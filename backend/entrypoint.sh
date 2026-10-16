#!/bin/sh
set -eu

cd /app

# Allow explicit maintenance commands, e.g. docker compose run api python ...
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

# Do not start an API against an outdated schema if migration fails.
python -m alembic upgrade head

# One process owns the local Chroma directory and shared embedding model.
# exec forwards container shutdown signals directly to the API process.
exec python -m uvicorn main:app \
    --host 0.0.0.0 \
    --port "${PORT:-7860}" \
    --workers 1 \
    --no-proxy-headers
