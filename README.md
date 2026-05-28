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
