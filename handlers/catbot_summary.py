import logging

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import IDFilter
from aiogram.types import ParseMode

logger = logging.getLogger(__name__)


async def cmd_tldr(message: types.Message):
    text = 'Chat ID: ' + str(message.chat.id) + \
        ' UID :' + str(message.from_user.id)
    await message.answer(text, parse_mode=ParseMode.HTML)
    

def register_handlers_summary(dp: Dispatcher, admin_id : int):
    dp.register_message_handler(cmd_tldr, IDFilter(user_id=admin_id), commands=['tldr'], state="*")
