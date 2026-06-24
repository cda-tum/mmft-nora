#!/bin/bash
set -euo pipefail

APP_DIR="${APP_DIR:-/var/www/cda/app/mmft-nora}"
VENV_DIR="${VENV_DIR:-$APP_DIR/nora-venv}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-5003}"

echo "[INFO $(date +'%Y-%m-%dT%H:%M:%S')] starting MMFT NORA backend on ${HOST}:${PORT}" >> /tmp/mmft-nora-deploy.log

cd "$APP_DIR"
mkdir -p "$APP_DIR/backend/output" "$APP_DIR/results"

export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/mmft-nora-matplotlib}"
mkdir -p "$MPLCONFIGDIR"

source "$VENV_DIR/bin/activate"
exec python -m uvicorn backend.app:app --host "$HOST" --port "$PORT" --proxy-headers
