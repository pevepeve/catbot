import hashlib
import io
import logging

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import IDFilter
from aiogram.types import ParseMode

import fetch_subsplease

logger = logging.getLogger(__name__)

from common.db_methods import photo_upload


async def cmd_anime_update(message: types.Message):
    try:
        fetch_subsplease.get_schedule()
    except Exception as e:
        logger.error(e)
    else:
        text = 'Updated'
        await message.answer(text, parse_mode=ParseMode.HTML)


async def cmd_debug(message: types.Message):
    text = 'Chat ID: ' + str(message.chat.id) + \
        ' UID :' + str(message.from_user.id)
    await message.answer(text, parse_mode=ParseMode.HTML)
    
async def cmd_addneko(message: types.Message):
    if message.reply_to_message:
        saveable = message.reply_to_message.photo[-1]
        file_info = await saveable.get_file()
        file_io = io.BytesIO()
        await saveable.download(destination=file_io)
        await message.answer(f'Downloaded id: {file_info}')
        file_md5 = hashlib.md5(file_io.getbuffer()).hexdigest()
        await message.answer(f'Downloaded md5: {file_md5}')
        try:
            await photo_upload(file_io, md5=file_md5)
        except ValueError as error:
            await message.answer(f'Error: {error}')

    else:
        try:
            saveable = message.photo[-1]
            file_info = await saveable.get_file()
            file_io = io.BytesIO()
            await saveable.download(destination=file_io)
            await message.answer(f'Downloaded id: {file_info}')
            file_md5 = hashlib.md5(file_io.getbuffer()).hexdigest()
            await message.answer(f'Downloaded md5: {file_md5}')
            try:
                await photo_upload(file_io, md5=file_md5)
            except ValueError as error:
                await message.answer(f'Error: {error}')
        except Exception as error:
            await message.answer(f'Error: Nothing to save')

def register_handlers_admin(dp: Dispatcher, admin_id : int):
    dp.register_message_handler(cmd_anime_update, IDFilter(user_id=admin_id), commands=['update_anime'], state="*")
    dp.register_message_handler(cmd_debug, IDFilter(user_id=admin_id), commands=['debug'], state="*")
    dp.register_message_handler(cmd_addneko,
                                IDFilter(user_id=admin_id),
                                commands=['addneko'],  content_types=['photo'],
                                commands_ignore_caption=False, state="*")
    dp.register_message_handler(cmd_addneko,
                                IDFilter(user_id=admin_id),
                                commands=['addneko'],
                                commands_ignore_caption=False, state="*")