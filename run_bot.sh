#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "Virtual environment is missing. Run ./deploy_ubuntu_1804.sh first." >&2
    exit 1
fi

cd "$PROJECT_ROOT"
exec "$VENV_PYTHON" bot.py
