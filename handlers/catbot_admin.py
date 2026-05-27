import io
import logging

from aiogram import F, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message

import texts
from config import get_settings
from infrastructure import TelegramMediaStore
from repositories import AnimeRepository, NekoRepository
from services import AnimeService, NekoService


logger = logging.getLogger(__name__)
settings = get_settings()


def build_admin_router(admin_id: int) -> Router:
    router = Router()
    router.message.filter(F.from_user.id == admin_id)

    anime_service = AnimeService(AnimeRepository())
    neko_service = NekoService(NekoRepository())

    @router.message(Command("update_anime"))
    async def cmd_anime_update(message: Message):
        try:
            anime_service.refresh_schedule()
        except Exception as error:
            logger.error(error)
        else:
            await message.answer(texts.ADMIN_UPDATED)

    @router.message(Command("debug"))
    async def cmd_debug(message: Message):
        debug_text = texts.ADMIN_DEBUG.format(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
        )
        await message.answer(debug_text)

    @router.message(Command("addneko"))
    @router.message(F.photo & F.caption.regexp(r"^/addneko(?:@\w+)?$"))
    async def cmd_addneko(message: Message):
        try:
            if message.reply_to_message and message.reply_to_message.photo:
                saveable = message.reply_to_message.photo[-1]
            elif message.photo:
                saveable = message.photo[-1]
            else:
                raise ValueError(texts.ADMIN_NOTHING_TO_SAVE)

            file_io = io.BytesIO()
            await message.bot.download(saveable, destination=file_io)
            await message.answer(texts.ADMIN_DOWNLOADED_ID.format(file_info=saveable.file_id))

            media_store = TelegramMediaStore(message.bot, settings.admin_id)
            file_md5 = await neko_service.add_neko(file_io, media_store)
            await message.answer(texts.ADMIN_DOWNLOADED_MD5.format(file_md5=file_md5))
        except ValueError as error:
            error_text = str(error)
            if error_text == texts.ADMIN_NOTHING_TO_SAVE:
                await message.answer(error_text)
            else:
                await message.answer(texts.ADMIN_ALREADY_EXISTS.format(error=error))
        except Exception:
            await message.answer(texts.ADMIN_NOTHING_TO_SAVE)

    return router


def register_handlers_admin(dispatcher: Dispatcher, admin_id: int):
    dispatcher.include_router(build_admin_router(admin_id))
