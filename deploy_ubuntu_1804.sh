#!/usr/bin/env bash
set -Eeuo pipefail

START_BOT=0
FORCE_RECREATE_VENV=0

for arg in "$@"; do
    case "$arg" in
        --start-bot)
            START_BOT=1
            ;;
        --force-recreate-venv)
            FORCE_RECREATE_VENV=1
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            echo "Usage: ./deploy_ubuntu_1804.sh [--start-bot] [--force-recreate-venv]" >&2
            exit 1
            ;;
    esac
done

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$PROJECT_ROOT/.venv"
ENV_EXAMPLE_PATH="$PROJECT_ROOT/.env.example"
ENV_PATH="$PROJECT_ROOT/.env"
MEDIA_PATH="$PROJECT_ROOT/media"
PYTHON_BIN="/usr/bin/python3.11"

step() {
    printf '[deploy] %s\n' "$1"
}

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Required command not found: $1" >&2
        exit 1
    fi
}

run_checked() {
    step "Running: $*"
    "$@"
}

require_command sudo
require_command apt-get

step "Project root: $PROJECT_ROOT"
step "Ubuntu 18.04 ships with Python 3.6, which is too old for this bot. Installing Python 3.11."

export DEBIAN_FRONTEND=noninteractive

run_checked sudo apt-get update
run_checked sudo apt-get install -y software-properties-common curl

if ! grep -Rqs "^deb .*\bdeadsnakes/ppa\b" /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null; then
    run_checked sudo add-apt-repository -y ppa:deadsnakes/ppa
fi

run_checked sudo apt-get update
run_checked sudo apt-get install -y \
    build-essential \
    libffi-dev \
    libjpeg-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    zlib1g-dev

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Python 3.11 was not installed successfully." >&2
    exit 1
fi

if [[ "$FORCE_RECREATE_VENV" -eq 1 && -d "$VENV_PATH" ]]; then
    step "Removing existing virtual environment"
    rm -rf "$VENV_PATH"
fi

if [[ ! -x "$VENV_PATH/bin/python" ]]; then
    step "Creating virtual environment"
    run_checked "$PYTHON_BIN" -m venv "$VENV_PATH"
else
    step "Using existing virtual environment"
fi

step "Upgrading pip"
run_checked "$VENV_PATH/bin/python" -m pip install --upgrade pip setuptools wheel

step "Installing dependencies"
run_checked "$VENV_PATH/bin/python" -m pip install -r "$PROJECT_ROOT/requirements.txt"

if [[ ! -d "$MEDIA_PATH" ]]; then
    step "Creating media directory"
    mkdir -p "$MEDIA_PATH"
else
    step "Media directory already exists"
fi

if [[ -f "$ENV_EXAMPLE_PATH" && ! -f "$ENV_PATH" ]]; then
    step "Creating .env from .env.example"
    cp "$ENV_EXAMPLE_PATH" "$ENV_PATH"
elif [[ -f "$ENV_PATH" ]]; then
    step ".env already exists"
else
    step "No .env.example found; skipping .env creation"
fi

printf '\n'
printf 'Deployment bootstrap finished.\n'
printf 'Next steps:\n'
printf '1. Edit %s and fill in API_TOKEN, ADMIN_ID, and DB_FILENAME.\n' "$ENV_PATH"
printf '2. Start the bot with ./run_bot.sh\n'

if [[ "$START_BOT" -eq 1 ]]; then
    step "Starting bot"
    cd "$PROJECT_ROOT"
    exec "$VENV_PATH/bin/python" bot.py
fi
