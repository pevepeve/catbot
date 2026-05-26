import io
import logging

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import IDFilter
from aiogram.types import ParseMode

import texts
from config import get_settings
from infrastructure import TelegramMediaStore
from repositories import AnimeRepository, NekoRepository
from services import AnimeService, NekoService


logger = logging.getLogger(__name__)
settings = get_settings()
anime_service = AnimeService(AnimeRepository())
neko_service = NekoService(NekoRepository())


async def cmd_anime_update(message: types.Message):
    try:
        anime_service.refresh_schedule()
    except Exception as error:
        logger.error(error)
    else:
        await message.answer(texts.ADMIN_UPDATED, parse_mode=ParseMode.HTML)


async def cmd_debug(message: types.Message):
    debug_text = texts.ADMIN_DEBUG.format(
        chat_id=message.chat.id,
        user_id=message.from_user.id,
    )
    await message.answer(debug_text, parse_mode=ParseMode.HTML)


async def cmd_addneko(message: types.Message):
    try:
        if message.reply_to_message:
            saveable = message.reply_to_message.photo[-1]
        else:
            saveable = message.photo[-1]

        file_info = await saveable.get_file()
        file_io = io.BytesIO()
        await saveable.download(destination=file_io)
        await message.answer(texts.ADMIN_DOWNLOADED_ID.format(file_info=file_info))

        media_store = TelegramMediaStore(message.bot, settings.admin_id)
        file_md5 = await neko_service.add_neko(file_io, media_store)
        await message.answer(texts.ADMIN_DOWNLOADED_MD5.format(file_md5=file_md5))
    except ValueError as error:
        await message.answer(texts.ADMIN_ALREADY_EXISTS.format(error=error))
    except Exception:
        await message.answer(texts.ADMIN_NOTHING_TO_SAVE)


def register_handlers_admin(dp: Dispatcher, admin_id: int):
    dp.register_message_handler(
        cmd_anime_update,
        IDFilter(user_id=admin_id),
        commands=["update_anime"],
        state="*",
    )
    dp.register_message_handler(
        cmd_debug,
        IDFilter(user_id=admin_id),
        commands=["debug"],
        state="*",
    )
    dp.register_message_handler(
        cmd_addneko,
        IDFilter(user_id=admin_id),
        commands=["addneko"],
        content_types=["photo"],
        commands_ignore_caption=False,
        state="*",
    )
    dp.register_message_handler(
        cmd_addneko,
        IDFilter(user_id=admin_id),
        commands=["addneko"],
        commands_ignore_caption=False,
        state="*",
    )

