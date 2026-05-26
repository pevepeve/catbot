import io

from aiogram import Bot


class TelegramMediaStore:
    def __init__(self, bot: Bot, target_chat_id: int):
        self.bot = bot
        self.target_chat_id = target_chat_id

    async def upload_photo(self, file_io: io.BytesIO) -> str:
        file_io.seek(0)
        message = await self.bot.send_photo(
            self.target_chat_id,
            file_io,
            disable_notification=True,
        )
        return message.photo[-1].file_id

