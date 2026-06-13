import io

from aiogram import Bot
from aiogram.types import BufferedInputFile


class TelegramMediaStore:
    def __init__(self, bot: Bot, target_chat_id: int):
        self.bot = bot
        self.target_chat_id = target_chat_id

    async def upload_photo(self, file_io: io.BytesIO, filename: str = "upload.jpg") -> str:
        file_io.seek(0)
        upload = BufferedInputFile(file_io.getvalue(), filename=filename)
        message = await self.bot.send_photo(
            self.target_chat_id,
            upload,
            disable_notification=True,
        )
        return message.photo[-1].file_id
