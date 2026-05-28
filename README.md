# CatBot

A Telegram bot with anime schedule, catgirl image, and chat summary features.

## User Commands

- `/start` - show the bot greeting
- `/help` - show the built-in help text
- `/neko` - send a random catgirl image
- `/animetoday` - show today's anime schedule with inline details
- `/animes` - browse the current anime schedule by weekday
- `/tldr` - generate a short summary of recent chat messages

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
```

If `SUMMARY_BACKEND=deepseek` but DeepSeek is not configured or the API request fails, CatBot automatically falls back to the local summarizer.
