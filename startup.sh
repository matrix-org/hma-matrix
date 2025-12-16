#!/bin/bash

set -ex
cd /app

if [ "$USE_DOCKER_SECRETS" == "true" ]; then
  # Hide commands from being printed to console for a moment
  set +x
  echo "Overwriting environment variables with Docker secrets"
  export SYNAPSE_ADMIN_ACCESS_TOKEN=$(cat /var/run/secrets/synapse_admin_access_token)
  set -x
fi

# We run migrations first to ensure things are set up properly.
./scripts/db-migrate.sh

# Now we can run the actual app (copied from upstream CMD)
gunicorn --bind 0.0.0.0:5100 "OpenMediaMatch.app:create_app()"
