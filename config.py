# This is the config file supplied to HMA
# See https://github.com/facebook/ThreatExchange/tree/main/hasher-matcher-actioner#configurability for details

import os
import sys
from flask import request, Response
from logging.config import dictConfig
from OpenMediaMatch.storage.postgres.impl import DefaultOMMStore
from threatexchange.signal_type.pdq.signal import PdqSignal
from threatexchange.signal_type.md5 import VideoMD5Signal
from threatexchange.content_type.photo import PhotoContent
from threatexchange.content_type.video import VideoContent
from threatexchange.exchanges.impl.static_sample import StaticSampleSignalExchangeAPI
from threatexchange.exchanges.impl.ncmec_api import NCMECSignalExchangeAPI
from threatexchange.exchanges.impl.stop_ncii_api import StopNCIISignalExchangeAPI
from threatexchange.exchanges.impl.fb_threatexchange_api import FBThreatExchangeSignalExchangeAPI
from threatexchange.exchanges.impl.techagainstterrorism_api import TATSignalExchangeAPI
from matrix_exchanges.synapse_quarantined import SynapseQuarantinedExchangeAPI

# ----------------------------------
# Database configuration
# ----------------------------------

db_user = os.environ.get("HMA_DB_USER", "hma")
db_pass = os.environ.get("HMA_DB_PASS", "")
db_host = os.environ.get("HMA_DB_HOST", "localhost")
db_name = os.environ.get("HMA_DB_NAME", "hma")

if db_pass == "":
  sys.exit("HMA_DB_PASS is required")

# Export to HMA
DATABASE_URI = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}/{db_name}"


# ----------------------------------
# Process configuration
# ----------------------------------

# Export some defaults to HMA
PRODUCTION = True
FLASK_LOGGING_CONFIG = dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            }
        },
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "default",
            }
        },
        "root": {"level": "INFO", "handlers": ["wsgi"]},
    }
)

# Export flags to HMA depending on our definition of a "role"
# role = os.environ.get("HMA_WORKER_ROLE", "")
# if role == "UI":
#   UI_ENABLED = True
# elif role == "CURATOR":
#   ROLE_CURATOR = True
# elif role == "CRON":  # There should only be ONE of these
#   TASK_FETCHER = True
#   TASK_INDEXER = True
#   TASK_FETCHER_INTERVAL_SECONDS = int(os.environ.get("HMA_FETCHER_INTERVAL_SECONDS", 60 * 4))
#   TASK_INDEXER_INTERVAL_SECONDS = int(os.environ.get("HMA_INDEXER_INTERVAL_SECONDS", 60))
# elif role == "HASHER":
#   ROLE_HASHER = True
# elif role == "MATCHER":
#   ROLE_MATCHER = True
#   ROLE_HASHER = False  # Can be combined, but not recommended for larger deployments
#   TASK_INDEX_CACHE = True
#   TASK_INDEX_CACHE_INTERVAL_SECONDS = int(os.environ.get("HMA_INDEX_CACHE_INTERVAL_SECONDS", 30))
# else:
#   sys.exit("Unknown role: " + role)

# Support multiple roles via CSV
# HMA_WORKER_ROLE can be a single role or a comma-separated list of roles
role_list = os.environ.get("HMA_WORKER_ROLE", "")
if not role_list:
  sys.exit("HMA_WORKER_ROLE is required")

# Parse comma-separated roles and make them uppercase
roles = [role.strip().upper() for role in role_list.split(",")]
invalid_roles = [role for role in roles if role not in ["UI", "CURATOR", "CRON", "HASHER", "MATCHER"]]
if invalid_roles:
  sys.exit("Unknown roles: " + ", ".join(invalid_roles))

# Enable features based on provided roles
if "UI" in roles:
  UI_ENABLED = True

if "CURATOR" in roles:
  ROLE_CURATOR = True

if "CRON" in roles:
  TASK_FETCHER = True
  TASK_INDEXER = True
  TASK_FETCHER_INTERVAL_SECONDS = int(os.environ.get("HMA_FETCHER_INTERVAL_SECONDS", 60 * 4))
  TASK_INDEXER_INTERVAL_SECONDS = int(os.environ.get("HMA_INDEXER_INTERVAL_SECONDS", 60))

if "HASHER" in roles:
  ROLE_HASHER = True

if "MATCHER" in roles:
  ROLE_MATCHER = True
  ROLE_HASHER = False
  TASK_INDEX_CACHE = True
  TASK_INDEX_CACHE_INTERVAL_SECONDS = int(os.environ.get("HMA_INDEX_CACHE_INTERVAL_SECONDS", 30))


# ----------------------------------
# Authentication config
# ----------------------------------

api_key = os.environ.get("HMA_API_KEY", "")
api_key_required = os.environ.get("HMA_API_KEY_REQUIRED", "true") != "false"

if api_key == "" and api_key_required:
  sys.exit("An HMA_API_KEY is required")

if api_key != "":
  def on_flask_ready(app):
    app.logger.info("Adding API authentication")

    @app.before_request
    def require_auth():
        app.logger.info("%s %s", request.method, request.path)
        if request.path == "/site-map" or request.path == "/status":
          return  # don't require auth on "status" endpoints
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or auth[7:] != api_key:
            return Response("Authentication required", 401)

  # Export the hook to HMA
  APP_HOOK = on_flask_ready
# else: API key not enabled


# ----------------------------------
# Core config
# ----------------------------------

# Export enable flags for all the things to HMA
# This doesn't configure the exchanges, just makes them possible to use.
# TODO: Later we'll need to (somehow) extend this to include private exchanges at startup
STORAGE_IFACE_INSTANCE = DefaultOMMStore(
  signal_types=[PdqSignal, VideoMD5Signal],
  content_types=[PhotoContent, VideoContent],
  exchange_types=[
    StaticSampleSignalExchangeAPI,
    FBThreatExchangeSignalExchangeAPI,
    NCMECSignalExchangeAPI,
    StopNCIISignalExchangeAPI,
    TATSignalExchangeAPI,
    SynapseQuarantinedExchangeAPI,
  ],
)
