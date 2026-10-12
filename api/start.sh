#!/bin/sh
# Container start: apply pending Alembic migrations, then replace this shell with the server
# so that uvicorn runs as PID 1 and receives the stop signal.
set -eu

alembic upgrade head
exec uvicorn app.infrastructure.fastapi.main:app --host 0.0.0.0 --port 8000 "$@"
