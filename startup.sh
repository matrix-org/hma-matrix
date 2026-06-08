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

# We run migrations on the CRON and CURATOR workers to ensure everything is set up. We
# don't run the migrations on matchers or hashers because they're meant to be readonly.
# Both CRON and CURATOR workers are targeted to ensure migrations *definitely* run. The
# UI worker is "readonly" by this script, but is a read+write worker.
should_run_migrations=false
# Split CSV list
IFS=',' read -ra worker_roles <<< "$HMA_WORKER_ROLE"
for role in "${worker_roles[@]}"; do
  if [ "$role" == "CRON" ] || [ "$role" == "CURATOR" ]; then
    should_run_migrations=true
    break
  fi
done
if [ "$should_run_migrations" == "true" ]; then
  ./scripts/db-migrate.sh
else
  echo "Skipping migrations - readonly or UI role"
fi

# Now we can run the actual app (copied from upstream CMD)
gunicorn --bind 0.0.0.0:5100 "OpenMediaMatch.app:create_app()"
