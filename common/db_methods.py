import io

from aiogram import Bot

from config import get_settings
from infrastructure import TelegramMediaStore, init_db
from repositories import AnimeRepository, MessageRepository, NekoRepository
from services import ChatHistoryService, NekoService


settings = get_settings()
init_db()

bot = Bot(token=settings.api_token)
anime_repository = AnimeRepository()
chat_history_service = ChatHistoryService(MessageRepository())
neko_service = NekoService(NekoRepository())


async def photo_upload(file_io: io.BytesIO, md5: str):
    filename = md5 + ".jpg"
    if neko_service.repository.exists_by_filename(filename):
        raise ValueError("Already exists")

    media_store = TelegramMediaStore(bot, settings.admin_id)
    file_id = await media_store.upload_photo(file_io, filename=filename)
    neko_service.repository.add_image(file_id=file_id, filename=filename)


async def get_thumb_id(filename):
    return anime_repository.get_thumbnail_id(filename)


async def get_random_nekochan():
    return await neko_service.get_random_neko_id()


async def save_to_db(message, date, chatid):
    await chat_history_service.save_message(message, date, chatid)


async def get_last_messages(chatid):
    return await chat_history_service.get_messages(chatid)
