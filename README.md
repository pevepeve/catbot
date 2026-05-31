# CatBot

A Telegram bot with anime schedule, catgirl image, and chat summary features.

## User Commands

- `/start` - show the bot greeting
- `/help` - show the built-in help text
- `/neko` - send a random catgirl image
- `/animetoday` - show today's anime schedule with inline details
- `/animes` - browse the current anime schedule by weekday
- `/tldr` - generate a short summary of recent chat messages
- `/factcheck` - ask DeepSeek whether a post's claims could be called a lie and why
  Use it by replying to a post or by passing the claim text after the command.

## Text Triggers

- `кек` - replies with `КЕК!`

## Admin Commands

These commands are only available to the configured admin user.

- `/update_anime` - force refresh the cached anime schedule and thumbnails
- `/debug` - print the current chat ID and user ID
- `/addneko` - add a new neko image

`/addneko` can be used in two ways:

- send `/addneko` while replying to a photo message
- send a photo with caption `/addneko`

## `.env` Configuration

CatBot loads configuration from a `.env` file via `python-dotenv`.

Required variables:

- `API_TOKEN` - Telegram bot token from BotFather
- `ADMIN_ID` - Telegram user ID allowed to use admin commands
- `DB_FILENAME` - SQLite database filename, for example `catbot.db`

Optional variables:

- `TELEGRAM_PROXY` - proxy URL for Telegram, leave empty if unused
- `LAST_SAVED_MESSAGES` - how many chat messages to keep per chat for `/tldr`, default `1000`
- `LAST_SAVED_IMAGE_MESSAGES` - how many OCR-indexed image messages to keep per chat, default `1000`
- `SUMMARY_LOOKBACK_DAYS` - how many recent days `/tldr` should consider, default `3`
- `SUMMARY_BACKEND` - summarizer backend, `local` or `deepseek`, default `local`
- `DEEPSEEK_API_KEY` - DeepSeek API key, only needed when `SUMMARY_BACKEND=deepseek`
- `DEEPSEEK_BASE_URL` - DeepSeek API base URL, default `https://api.deepseek.com`
- `DEEPSEEK_MODEL` - DeepSeek chat model name, default `deepseek-chat`
- `DEEPSEEK_TIMEOUT_SECONDS` - timeout for DeepSeek summary requests, default `30`
- `LOG_UNHANDLED_UPDATES` - when `true`, poll all Telegram update types and log full payloads for updates that no handler consumed, default `false`

Example `.env`:

```dotenv
API_TOKEN=123456:telegram-bot-token
ADMIN_ID=123456789
DB_FILENAME=catbot.db

TELEGRAM_PROXY=
LAST_SAVED_MESSAGES=1000
LAST_SAVED_IMAGE_MESSAGES=1000
SUMMARY_LOOKBACK_DAYS=3

SUMMARY_BACKEND=local
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT_SECONDS=30
LOG_UNHANDLED_UPDATES=false
```

If `SUMMARY_BACKEND=deepseek`, CatBot stores per-chat summary usage and allows a new DeepSeek `/tldr` only after both 30 minutes and 100 new chat messages since the last successful DeepSeek summary. Until then, `/tldr` automatically falls back to the local summarizer for that chat.

If `SUMMARY_BACKEND=deepseek` but DeepSeek is not configured or the API request fails, CatBot automatically falls back to the local summarizer.

## Deploy On Another Windows Machine

1. Copy the `catbot` folder to the target machine.
2. Open PowerShell in that folder.
3. Run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\deploy_windows.ps1
```

The script will:

- create `.venv`
- install dependencies from `requirements.txt`
- create the `media` folder
- copy `.env.example` to `.env` if `.env` does not exist

Then:

1. Edit `.env` and fill in `API_TOKEN`, `ADMIN_ID`, and `DB_FILENAME`.
2. Start the bot with:

```powershell
.\run_bot.ps1
```

You can also start immediately after setup with:

```powershell
.\deploy_windows.ps1 -StartBot
```

## Deploy On Ubuntu 18.04.5 LTS

Ubuntu 18.04 ships with Python 3.6, which is too old for this project. The deploy script installs Python 3.11 from `ppa:deadsnakes/ppa`, creates `.venv`, installs dependencies, creates `media`, and copies `.env.example` to `.env` if needed.

1. Copy the `catbot` folder to the target machine.
2. Open a terminal in that folder.
3. Make the scripts executable:

```bash
chmod +x deploy_ubuntu_1804.sh run_bot.sh
```

4. Run:

```bash
./deploy_ubuntu_1804.sh
```

Then:

1. Edit `.env` and fill in `API_TOKEN`, `ADMIN_ID`, and `DB_FILENAME`.
2. Start the bot with:

```bash
./run_bot.sh
```

You can also start immediately after setup with:

```bash
./deploy_ubuntu_1804.sh --start-bot
```

Optional `systemd` setup:

1. Copy `catbot.service.example` to `/etc/systemd/system/catbot.service`.
2. Adjust `WorkingDirectory`, `ExecStart`, and `User`.
3. Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now catbot
```
