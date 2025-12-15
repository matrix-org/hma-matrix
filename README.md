# hma-matrix

[HMA (Hasher Matcher Actioner)](https://github.com/facebook/ThreatExchange/tree/main/hasher-matcher-actioner) is a tool from Meta to detect content that's been copied (or slightly modified) from sources already identified.

This repository provides a Matrix-specific extensions to HMA for (primarily) the Matrix ecosystem to benefit from in a familiar "Matrix way" of deploying applications. Use of this repository is not required to set up an HMA instance - it just wraps up some of the functionality to be familiar to Matrix developers/server operators.

## Usage

This repo provides a Docker image which is layered on top of HMA's image. Configuration is done via environment variables rather than Python (if you'd like to use/override the Python config, HMA directly is probably a better choice).

The following environment variables can be specified:

* `HMA_DB_HOST` (default `localhost`) - The hostname (with port if required) for your PostgreSQL database running HMA.
* `HMA_DB_NAME` (default `hma`) - The name of the database on the PostgreSQL server to use.
* `HMA_DB_USER` (default `hma`) - The username to access the PostgreSQL database.
* `HMA_DB_PASS` (no default - **required**) - The password for the above user.
* `HMA_API_KEY` (no default - **required** if `HMA_API_KEY_REQUIRED` is not `false`) - The API key to require on requests. The UI may not function with an API key set - use HMA's Docker Compose/development setup for experimentation with the UI.
* `HMA_API_KEY_REQUIRED` (default `true`) - Set this to `false` to disable the API key requirement. This can allow you to use the UI properly when there's no API key. Ignored when an API key is specified.
* `HMA_WORKER_ROLE` (no default - **required**) - The type of functionality to enable on this particular instance. This allows for load balancing some/all aspects of HMA's operations. Reverse proxying and routing traffic to workers is left as an exercise for the reader 😇.

  The role **must** be one of the following:

  * `HASHER` - Services the `/h/*` API endpoints for hashing. Note that hashing can be resource intensive.
  * `MATCHER` - Services the `/m/*` API endpoints for matching. The matcher can additionally have the following environment variables:
    * `HMA_INDEX_CACHE_INTERVAL_SECONDS` (default `30`) - The interval to cache the internal index at.
  * `CURATOR` - Services the `/c/*` API endpoints for managing content, banks, exchanges, etc.
  * `CRON` - Runs scheduled tasks and builds the internal index for the matcher(s). There should be no more than one of these running at a time. The cron worker can additionally have the following environment variables:
    * `HMA_FETCHER_INTERVAL_SECONDS` (default `240` (4 minutes)) - The interval to fetch from exchanges at. This is set to `30` seconds in hma-matrix's `compose.yaml`.
    * `HMA_INDEXER_INTERVAL_SECONDS` (default `60` (1 minute)) - The interval to rebuild the internal index at.
  * `UI` - Services the `/ui/*` endpoints. Note that the UI might not function if an API key is set. The UI worker is the only worker that's not required to run a complete HMA instance.

The above can then be provided to the hma-matrix Docker image to run a worker:

```bash
docker run -d -e HMA_WORKER_ROLE=UI [...] -p 127.0.0.1:5100:5100 ghcr.io/matrix-org/hma-matrix:[version]
```

See [the GHCR repo](https://github.com/matrix-org/hma-matrix/pkgs/container/hma-matrix) for available tags/versions.

See [the HMA API docs](https://github.com/facebook/ThreatExchange/blob/main/hasher-matcher-actioner/docs/api.md) for more information on the API endpoints themselves.

> [!NOTE]
> It's possible with this setup to specify different API keys for different functions. All of the same type of worker will need to be using the same API key, but the hashers can use a different API key from the curators for an amount of role-based access control.

> [!NOTE]
> If there's a config option you'd like to set (or override) from HMA directly, you can do so by prefixing the option with `OMM_`. For example, `OMM_MAX_REMOTE_FILE_SIZE=1073741824` will set the max remote file size to 1gb.

## For developers

To quickly set up a local HMA stack for developing applications which use HMA, the Docker Compose file from this repo can be used.

1. `git clone https://github.com/matrix-org/hma-matrix.git && cd hma-matrix`
2. `docker compose up -d`
3. Visit `http://localhost:5100/ui`

> [!CAUTION]
> This stack is set up by default *without* an API key to allow use of the UI. It's recommended to set an API key in production deployments.

When API authentication is enabled, supply the API key as a Bearer token in the Authorization header:

```bash
curl -h "Authorization: Bearer ${HMA_API_KEY}" ...
```

## Matrix-specific exchanges

**TODO: Not yet written.**

Ideas:
* Synapse quarantined media exchange/import
* The same but for MMR
* Maybe policy list support if we can figure out how to make that work safely?
* "flagged as spam" from policyserv/mjolnir/draupnir/meowlnir/etc

## Versioning

This repository puts out new versions when HMA does *and* when there's functionality worth releasing, such as changes to the `config.py` file.

Structure: `[hma-version]-matrix.[increment]` where `[increment]` is on a per-`[hma-version]` basis.

Example: `1.0.21-matrix.2` is HMA v1.0.21, second release by this repo in the v1.0.21 series.
