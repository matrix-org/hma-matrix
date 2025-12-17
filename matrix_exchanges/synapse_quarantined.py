import typing as t
from dataclasses import dataclass, field

import PIL
import requests
from threatexchange.exchanges import auth, fetch_state as state
from threatexchange.exchanges import signal_exchange_api
from threatexchange.exchanges.collab_config import (
    CollaborationConfigWithDefaults,
)
from threatexchange.signal_type.signal_base import SignalType, BytesHasher


_API_NAME: str = "synapse_quarantined"


@dataclass
class _SynapseQuarantinedCollabConfigRequiredFields:
    """Required config fields for the exchange. Used by SynapseQuarantinedCollabConfig."""

    admin_api_url: str = field(
        metadata={"help": "The admin API URL for Synapse"}
    )


@dataclass
class SynapseQuarantinedCollabConfig(
    CollaborationConfigWithDefaults,
    _SynapseQuarantinedCollabConfigRequiredFields
):
    """Container class for exchange API configuration."""

    pass


@dataclass
class SynapseQuarantinedCheckpoint(
    state.FetchCheckpointBase,
):
    """Tracks where HMA left off in the exchange fetching. Created by HMA as-needed, populated by us."""

    local_from_token: str
    remote_from_token: str

    def is_stale(self) -> bool:
        # When an exchange becomes stale it loses its checkpoint, so we don't really want to do that.
        return False


@dataclass
class SynapseQuarantinedCredentials(auth.CredentialHelper):
    """Credentials for accessing Synapse's admin API. Created by HMA as-needed."""

    ENV_VARIABLE: t.ClassVar[str] = "SYNAPSE_ADMIN_ACCESS_TOKEN"
    FILE_NAME: t.ClassVar[str] = "~/.synapse_admin_access_token"

    access_token: str

    @classmethod
    def _from_str(cls, s: str) -> "SynapseQuarantinedCredentials":
        return cls(s.strip())

    def _are_valid(self) -> bool:
        return bool(self.access_token)


@dataclass
class SynapseQuarantinedSignalMetadata(
    state.FetchedSignalMetadata,
):
    """Tracks per-signal (media item) metadata for the HMA database."""

    mxc_uri: str


class SynapseQuarantinedExchangeAPI(
    auth.SignalExchangeWithAuth[SynapseQuarantinedCollabConfig, SynapseQuarantinedCredentials],
    signal_exchange_api.SignalExchangeAPIWithSimpleUpdates[
        SynapseQuarantinedCollabConfig,
        SynapseQuarantinedCheckpoint,
        SynapseQuarantinedSignalMetadata,
    ],
):
    """
    This exchange pulls media from Synapse's quarantined media list so it can be downloaded and hashed
    locally before being used by HMA for inclusion in a content bank somewhere.
    """

    def __init__(self, collab: SynapseQuarantinedCollabConfig, access_token: str):
        super().__init__()
        self.collab = collab
        self._access_token = access_token

    @classmethod
    def for_collab(
        cls,
        collab: SynapseQuarantinedCollabConfig,
        credentials: t.Optional["SynapseQuarantinedCredentials"] = None,
    ) -> "SynapseQuarantinedExchangeAPI":
        credentials = credentials or SynapseQuarantinedCredentials.get(cls)
        return cls(collab, credentials.access_token)

    @staticmethod
    def get_credential_cls() -> t.Type[SynapseQuarantinedCredentials]:
        return SynapseQuarantinedCredentials

    @staticmethod
    def get_checkpoint_cls() -> t.Type[SynapseQuarantinedCheckpoint]:
        return SynapseQuarantinedCheckpoint

    @staticmethod
    def get_record_cls() -> t.Type[SynapseQuarantinedSignalMetadata]:
        return SynapseQuarantinedSignalMetadata

    @staticmethod
    def get_config_cls() -> t.Type[SynapseQuarantinedCollabConfig]:
        return SynapseQuarantinedCollabConfig

    def fetch_iter(
        self,
        supported_signal_types: t.Sequence[t.Type[SignalType]],
        checkpoint: t.Optional[SynapseQuarantinedCheckpoint],
    ) -> t.Iterator[state.FetchDelta[t.Tuple[str, str], SynapseQuarantinedSignalMetadata, SynapseQuarantinedCheckpoint]]:
        # Process local media first
        local_token = checkpoint.local_from_token if checkpoint else "0"
        local_media_mxcs, next_batch = self._fetch(True, local_token)
        if next_batch != "":
            local_token = next_batch.split("-", maxsplit=1)[0] + "-0"

        # Now process remote media
        remote_token = checkpoint.remote_from_token if checkpoint else 0
        remote_media_mxcs, next_batch = self._fetch(False, remote_token)
        if next_batch != "":
            remote_token = next_batch.split("-", maxsplit=1)[0] + "-0"

        # Hash the media, if we can
        ret = list()
        for media_mxc in local_media_mxcs + remote_media_mxcs:
            for signal_type in supported_signal_types:
                signal_hash = self._hash(media_mxc, signal_type)
                if signal_hash:
                    ret.append(((signal_type.get_name(), signal_hash), SynapseQuarantinedSignalMetadata(media_mxc)))

        # Return the delta
        yield state.FetchDelta(dict(ret), SynapseQuarantinedCheckpoint(local_token, remote_token))

    def _fetch(self, local: bool, from_token: str) -> tuple[list[str], str]:
        res = requests.get(
            f"{self.collab.admin_api_url}/_synapse/admin/v1/media/quarantined?kind={"local" if local else "remote"}&from={from_token}&limit={1000 if local else 250}",
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        if res.status_code != 200:
            raise RuntimeError(f"Failed to fetch media: {res.text}")
        json = res.json()
        return json.get("media", []), json.get("next_batch", "")

    def _hash(self, mxc_uri: str, signal_type: t.Type[SignalType]) -> str | None:
        if not issubclass(signal_type, BytesHasher):
            return None
        try:
            # We can ignore the cast warning because we're only really expecting to take a PDQSignal anyway, which inherits both classes.
            # noinspection PyInvalidCast
            hasher = t.cast(BytesHasher, signal_type)
            res = requests.get(
                f"{self.collab.admin_api_url}/_matrix/client/v1/media/download/{mxc_uri[len("mxc://"):]}?admin_unsafely_bypass_quarantine=true",
                headers={"Authorization": f"Bearer {self._access_token}"},
            )
            if res.status_code != 200:
                raise RuntimeError(f"Failed to download media: {res.text}")
            b = res.content
            return hasher.hash_from_bytes(b)
        except PIL.UnidentifiedImageError:
            # ignore non-image files (they're probably encrypted)
            return None
