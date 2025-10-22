#!/bin/sh

set -ex
cd /app

# We run migrations first to ensure things are set up properly.
./scripts/db-migrate.sh

# Now we can run the actual app (copied from upstream CMD)
gunicorn --bind 0.0.0.0:5100 "OpenMediaMatch.app:create_app()"
