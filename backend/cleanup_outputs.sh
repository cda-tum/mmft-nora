#!/bin/bash
set -euo pipefail

# Example server cron entry:
# 0 3 * * * bash /var/www/cda/app/mmft-nora/backend/cleanup_outputs.sh >> /var/www/cda/app/mmft-nora/backend/output/mmft-nora-cleanup.log 2>&1

APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
MAX_AGE_DAYS="${MAX_AGE_DAYS:-2}"

BACKEND_OUTPUT_DIR="$APP_DIR/backend/output"
CLI_RESULTS_DIR="$APP_DIR/results"

mkdir -p "$BACKEND_OUTPUT_DIR" "$CLI_RESULTS_DIR"

find "$BACKEND_OUTPUT_DIR" -mindepth 1 -maxdepth 1 -type f \
  \( -name 'design_*.dxf' -o -name 'preview_*.png' -o -name 'job_*.pkl' -o -name 'job_*.json' \) \
  -mtime +"$MAX_AGE_DAYS" -exec rm -f {} +

find "$CLI_RESULTS_DIR" -mindepth 1 -maxdepth 1 -type f \
  \( -name 'output*.dxf' -o -name 'output*.png' -o -name 'output*.svg' \) \
  -mtime +"$MAX_AGE_DAYS" -exec rm -f {} +
