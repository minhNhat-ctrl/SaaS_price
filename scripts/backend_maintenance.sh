#!/usr/bin/env bash
# Maintenance helper: clear pyc, clear Django cache, restart backend service
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="gunicorn-saas.service"
PYTHON_BIN="python3.9"

cd "$ROOT_DIR"

echo "[1/3] Removing cached bytecode (*.pyc)..."
find "$ROOT_DIR" -name "*.pyc" -delete

echo "[2/3] Clearing Django cache..."
$PYTHON_BIN manage.py clear_cache || {
  echo "Cache clear failed" >&2
  exit 1
}

echo "[3/3] Restarting backend service ($SERVICE_NAME)..."
sudo systemctl restart "$SERVICE_NAME"

echo "Done. Backend restarted and caches cleared."
