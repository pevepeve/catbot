from aiogram.types import ParseMode
from aiogram import Dispatcher, types
from  .. import fetch_subsplease
import logging


logger = logging.getLogger(__name__)

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


def register_handlers_cardholder(dp: Dispatcher):
    dp.register_message_handler(cmd_anime_update, commands=['update_anime'], state="*")
    dp.register_message_handler(cmd_debug, commands=['debug'], state="*")