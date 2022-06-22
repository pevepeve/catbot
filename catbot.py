from random import choice
from datetime import date
import aiofiles
import logging
import json
import os

from emoji import emojize

from sqlitedict import SqliteDict
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ParseMode
from aiogram.utils.markdown import text, bold, italic, code, pre
from data.config.config import API_TOKEN


SCRAPED_SITE = 'https://subsplease.org'
MEDIA_FOLDER = 'media/'
SHOWS_FOLDER = '/shows/'
NEKODIR = 'media/nekochans/'
JSON_FILE = 'anime.json'
ROW_LEN_WEEK_BUTTONS = 4

saved_messages_table = SqliteDict(
    'saved.sqlite', tablename='saved', autocommit=True)

days_list = ['Monday', 'Tuesday', 'Wednesday',
             'Thursday', 'Friday', 'Saturday', 'Sunday']
days_list_ru = ['понедельник', 'вторник', 'среда',
                'четверг', 'пятница', 'суббота', 'воскресенье']

with open(JSON_FILE, mode='rb') as json_anime:
    anime_dict = json.load(json_anime)
# Configure logging
logging.basicConfig(level=logging.INFO, filename='logs/bot.log')

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)


def get_keyboard_days():
    buttons = [types.InlineKeyboardButton(
        text=days_list_ru[day_num], callback_data='weekday_'+day_name) for day_num, day_name in enumerate(days_list)]
    keyboard = types.InlineKeyboardMarkup(row_width=ROW_LEN_WEEK_BUTTONS)
    keyboard.add(*buttons)
    return keyboard

###############################
#     CALLBACK HANDLERS
###############################


@dp.callback_query_handler(text_startswith='weekday_')
async def callbacks_num(callback_query: types.CallbackQuery):
    weekday_q = callback_query.data.split("_")[1]
    today_anime = anime_dict[weekday_q]
    day_pretty = days_list_ru[days_list.index(weekday_q)].capitalize()
    text = f'<b>{day_pretty}</b> - с субтитрами выходят аниме:\n'
    for title_item in today_anime:
        formatted_str = f'<b>{title_item["title"]}</b> : {title_item["time"]} \n'
        text += formatted_str
    await bot.answer_callback_query(callback_query.id, emojize(':check_mark_button:'))
    await callback_query.message.answer(text, reply_markup=get_keyboard_days())

###############################
#     COMMAND HANDLERS
###############################


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    await message.reply('Hi!\nI send catgirls and anime schedules.')


@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    await message.reply(text(bold('Я могу ответить на следующие команды:'),
                             '/start',
                             '/help',
                             '/neko',
                             '/animetoday',
                             sep='\n'),
                        parse_mode=ParseMode.MARKDOWN_V2)


@dp.message_handler(commands=['animetoday'])
async def cmd_animetoday(message: types.Message):
    today_num = date.today().weekday()
    today_anime = anime_dict[days_list[today_num]]
    text = f'Сегодня {days_list_ru[today_num]}, и выходят с субтитрами аниме:\n'
    for title_item in today_anime:
        formatted_str = f'<b>{title_item["title"]}</b> : {title_item["time"]} \n'
        text += formatted_str

    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message_handler(commands=['neko'])
async def cmd_neko(message: types.Message):
    random_file = choice(os.listdir(NEKODIR))
    async with aiofiles.open(NEKODIR + random_file, mode='rb') as photo:
        await message.reply_photo(photo, caption='Держи кошкодевочку!')


@dp.message_handler(commands=['save'])
async def cmd_save(message: types.Message):
    if message.reply_to_message:
        saveable = message.reply_to_message.text
        message_tag = 'undefined'
        if len(message.text.split()) > 1:
            if message.text.split()[1]:
                message_tag = message.text.split()[1]
        saved_messages_table[len(saved_messages_table)] = {
            'tag': message_tag,
            'message': saveable,
            'by': message.reply_to_message.from_user.first_name}
        await message.answer(f'Saved id: {len(saved_messages_table)}')
    else:
        await message.answer('Nothing to save')


@dp.message_handler(commands=['unpack'])
async def cmd_unpack(message: types.Message):
    if len(message.text.split()) > 1:
        if len(saved_messages_table) > int(message.text.split()[1]):
            reply_dic = saved_messages_table[message.text.split()[1]]
            reply = 'By: <b>' + reply_dic['by'] + \
                '</b>, tag: <b>' + reply_dic['tag']+'</b>\n'
            reply += reply_dic['message']
            await message.answer(reply, parse_mode=ParseMode.HTML)
    else:
        await message.answer('Nothing to unpack')


@dp.message_handler(commands=['animes'])
async def cmd_animeschedules(message: types.Message):
    text = f'*Выберите день*:\n'
    await message.answer(text, reply_markup=get_keyboard_days(), parse_mode=ParseMode.MARKDOWN_V2)


###############################
#     MESSAGE HANDLERS
###############################


@dp.message_handler(regexp='(^кек$)')
async def kek(message: types.Message):

    await message.answer('КЕК!')

###############################
#     MAIN CYCLE
###############################


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
