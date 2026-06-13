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
LOCAL_PYTHON_PREFIX="$PROJECT_ROOT/.python311"
LOCAL_PYTHON_BUILD_DIR="$PROJECT_ROOT/.python-build"
PYTHON_VERSION="3.11.9"
PYTHON_TARBALL="Python-$PYTHON_VERSION.tgz"
PYTHON_SOURCE_DIR="$LOCAL_PYTHON_BUILD_DIR/Python-$PYTHON_VERSION"
PYTHON_BIN=""

step() {
    printf '[deploy] %s\n' "$1"
}

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Required command not found: $1" >&2
        exit 1
    fi
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

run_checked() {
    step "Running: $*"
    "$@"
}

apt_package_exists() {
    apt-cache show "$1" >/dev/null 2>&1
}

python_supported() {
    local python_cmd="$1"
    "$python_cmd" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'
}

select_existing_python() {
    local candidate
    for candidate in python3.12 /usr/bin/python3.12 python3.11 /usr/bin/python3.11; do
        if command_exists "$candidate" && python_supported "$candidate"; then
            PYTHON_BIN="$(command -v "$candidate")"
            step "Using existing Python interpreter: $PYTHON_BIN"
            return 0
        fi
    done
    return 1
}

install_python_from_source() {
    step "APT packages for Python 3.11 are unavailable on this Ubuntu 18.04 host."
    step "Falling back to building Python $PYTHON_VERSION locally under $LOCAL_PYTHON_PREFIX"

    if [[ -x "$LOCAL_PYTHON_PREFIX/bin/python3.11" ]]; then
        step "Reusing existing local Python 3.11 build"
        PYTHON_BIN="$LOCAL_PYTHON_PREFIX/bin/python3.11"
        return
    fi

    run_checked sudo apt-get install -y \
        build-essential \
        curl \
        libbz2-dev \
        libffi-dev \
        libgdbm-dev \
        libjpeg-dev \
        liblzma-dev \
        libncurses5-dev \
        libreadline-dev \
        libsqlite3-dev \
        libssl-dev \
        libxml2-dev \
        libxmlsec1-dev \
        libxslt1-dev \
        tk-dev \
        uuid-dev \
        xz-utils \
        zlib1g-dev

    mkdir -p "$LOCAL_PYTHON_BUILD_DIR"

    if [[ ! -f "$LOCAL_PYTHON_BUILD_DIR/$PYTHON_TARBALL" ]]; then
        run_checked curl -fL "https://www.python.org/ftp/python/$PYTHON_VERSION/$PYTHON_TARBALL" -o "$LOCAL_PYTHON_BUILD_DIR/$PYTHON_TARBALL"
    fi

    rm -rf "$PYTHON_SOURCE_DIR"
    run_checked tar -xzf "$LOCAL_PYTHON_BUILD_DIR/$PYTHON_TARBALL" -C "$LOCAL_PYTHON_BUILD_DIR"

    cd "$PYTHON_SOURCE_DIR"
    run_checked ./configure --prefix="$LOCAL_PYTHON_PREFIX" --with-ensurepip=install
    run_checked make -j"$(nproc)"
    run_checked make install

    PYTHON_BIN="$LOCAL_PYTHON_PREFIX/bin/python3.11"
    cd "$PROJECT_ROOT"
}

require_command sudo
require_command apt-get

step "Project root: $PROJECT_ROOT"
step "Ubuntu 18.04 ships with Python 3.6, which is too old for this bot."

export DEBIAN_FRONTEND=noninteractive

if ! select_existing_python; then
    step "No suitable local Python found. Trying to install Python 3.11."

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
        zlib1g-dev

    if apt_package_exists python3.11 && apt_package_exists python3.11-venv; then
        run_checked sudo apt-get install -y python3.11 python3.11-dev python3.11-venv
        PYTHON_BIN="/usr/bin/python3.11"
    else
        install_python_from_source
    fi
fi

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
