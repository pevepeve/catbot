from aiogram.types import ParseMode
from aiogram.dispatcher.filters import Text, IDFilter
from aiogram import Dispatcher, types
import fetch_subsplease
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
    
async def cmd_addneko(message: types.Message):
    pass

def register_handlers_admin(dp: Dispatcher, admin_id : int):
    dp.register_message_handler(cmd_anime_update, IDFilter(user_id=admin_id), commands=['update_anime'], state="*")
    dp.register_message_handler(cmd_debug, IDFilter(user_id=admin_id), commands=['debug'], state="*")
    dp.register_message_handler(cmd_addneko, IDFilter(user_id=admin_id), commands=['addneko'], state="*")