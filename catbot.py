from aiogram.dispatcher.filters.state import State, StatesGroup
#from aiogram.dispatcher.filters import Text
#from aiogram.dispatcher import FSMContext
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from random import randrange
from datetime import date
import logging
import json
from logging import StreamHandler
import os 
import sys

from emoji import emojize
from sqlalchemy.orm import scoped_session, sessionmaker

from sqlitedict import SqliteDict
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ParseMode
from aiogram.utils.markdown import text, bold, italic, code, pre

from data.config.config import API_TOKEN, NEKODB_FILENAME
from db_neko import NekoIds, AnimeThumbsIds
import fetch_subsplease

SCRAPED_SITE = 'https://subsplease.org'
MEDIA_FOLDER = 'media/'
SHOWS_FOLDER = '/shows/'
NEKODIR = 'media/nekochans/'
JSON_FILE = 'anime.json'
ROW_LEN_WEEK_BUTTONS = 4
ROW_LEN_TITLES_BUTTONS = 2
LETTERS_IN_TITLE_BTN = 7
MAX_LEN_CAPTION = 1023
saved_messages_table = SqliteDict(
    'saved.sqlite', tablename='saved', autocommit=True)

days_list = ['Monday', 'Tuesday', 'Wednesday',
             'Thursday', 'Friday', 'Saturday', 'Sunday']
days_list_ru = ['понедельник', 'вторник', 'среда',
                'четверг', 'пятница', 'суббота', 'воскресенье']

with open(JSON_FILE, mode='rb') as json_anime:
    anime_dict = json.load(json_anime)


logging.basicConfig(level=logging.INFO, filename='logs/bot.log')
engine = create_async_engine(f'sqlite+aiosqlite:///{NEKODB_FILENAME}')
session_factory = sessionmaker(
    bind=engine, expire_on_commit=False, class_=AsyncSession)
Session = scoped_session(session_factory)
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())


async def get_random_nekochan():
    count_nekos = await Session.execute(func.count(NekoIds.filename))
    random_neko = randrange(1, count_nekos.scalar_one())
    nekoid = await Session.execute(select(NekoIds.file_id).where(
        NekoIds.id == random_neko))
    return nekoid.scalar_one()


###############################
#     KEYBOARDS
###############################

def get_keyboard_days(day=None):
    buttons = [types.InlineKeyboardButton(
        text=days_list_ru[day_num],
        callback_data='weekday_' + day_name) for day_num, day_name in enumerate(days_list)]
    if day is not None:
        buttons.append(types.InlineKeyboardButton(
            text='Подробнее',
            callback_data=f'animedayc_{day}'))
    keyboard = types.InlineKeyboardMarkup(row_width=ROW_LEN_WEEK_BUTTONS)
    keyboard.add(*buttons)
    return keyboard


def get_keyboard_animes(titles_day, day):
    buttons = [types.InlineKeyboardButton(
        text=f'{title_num} {title["title"][:LETTERS_IN_TITLE_BTN]}..',
        callback_data='anime_' + day + '_' + str(title_num)) for title_num, title in enumerate(titles_day)]
    buttons.append(types.InlineKeyboardButton(
        text='Назад',
        callback_data=f'back_{day}'))
    keyboard = types.InlineKeyboardMarkup(row_width=ROW_LEN_TITLES_BUTTONS)
    keyboard.add(*buttons)
    return keyboard

###############################
#     CALLBACK HANDLERS
###############################


@dp.callback_query_handler(text_startswith=['weekday_', 'back_'])
async def callbacks_weekday(callback_query: types.CallbackQuery):
    weekday_q = callback_query.data.split("_")[1]
    today_anime = anime_dict[weekday_q]
    day_pretty = days_list_ru[days_list.index(weekday_q)].capitalize()
    text = f'<b>{day_pretty}</b> - с субтитрами выходят аниме:\n'
    for num, title_item in enumerate(today_anime):
        formatted_str = f'<b>{num}. {title_item["title"]}</b> : {title_item["time"]} \n'
        text += formatted_str
    await bot.answer_callback_query(callback_query.id, emojize(':check_mark_button:'))
    await callback_query.message.answer(text, reply_markup=get_keyboard_days(weekday_q))


@dp.callback_query_handler(text_startswith='anime_')
async def callbacks_anime(callback_query: types.CallbackQuery):
    weekday_q, title_q = callback_query.data.split(
        "_")[1], callback_query.data.split("_")[2]
    anime_title = anime_dict[weekday_q][int(title_q)]
    kb_back = types.InlineKeyboardMarkup()
    buttons = [types.InlineKeyboardButton(
        text='Назад', callback_data='back_' + weekday_q), ]
    kb_back.add(*buttons)
    text = f'<b>{anime_title["title"]} : {days_list_ru[days_list.index(weekday_q)]}, {anime_title["time"]}</b>\n'
    text += f'{anime_title["synopsis"]} \n'
    await bot.answer_callback_query(callback_query.id, emojize(':check_mark_button:'))
    thumb_id = await Session.execute(select(AnimeThumbsIds.file_id).where(
        AnimeThumbsIds.filename == anime_title['image']))
    if len(text) > MAX_LEN_CAPTION:
        text = text[:MAX_LEN_CAPTION-4]+'...'
    await callback_query.message.reply_photo(thumb_id.scalar_one(), caption=text, reply_markup=kb_back)


@dp.callback_query_handler(text_startswith=['animedayc_'])
async def callbacks_animechoice(callback_query: types.CallbackQuery):
    weekday_q = callback_query.data.split("_")[1]
    text = f'*Выберите aниме*:\n'
    today_anime = anime_dict[weekday_q]
    await callback_query.message.answer(text,
                                        reply_markup=get_keyboard_animes(
                                            today_anime, weekday_q),
                                        parse_mode=ParseMode.MARKDOWN_V2)

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
    for num, title_item in enumerate(today_anime):
        formatted_str = f'<b>{num}. {title_item["title"]}</b> : {title_item["time"]} \n'
        text += formatted_str
    kb_moreinfo = types.InlineKeyboardMarkup()
    buttons = [types.InlineKeyboardButton(
        text='Подробнее', callback_data='animedayc_' + days_list[today_num]), ]
    kb_moreinfo.add(*buttons)
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb_moreinfo)


@dp.message_handler(commands=['neko'])
async def cmd_neko(message: types.Message):
    random_neko_id = await get_random_nekochan()
    neko_caption = 'Держи кошкодевочку!'
    await message.reply_photo(random_neko_id, caption=neko_caption)

@dp.message_handler(commands=['update_anime'])
async def cmd_neko(message: types.Message):
    try:
        fetch_subsplease.get_schedule()
    except Exception as e:
        logger.error(e)
    else:
        text = 'Updated'
        await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message_handler(commands=['debug'])
async def cmd_debug(message: types.Message):
    text = 'Chat ID: ' + str(message.chat.id) + \
        ' UID :' + str(message.from_user.id)
    await message.answer(text, parse_mode=ParseMode.HTML)


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
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = StreamHandler(sys.stdout)
    logger.addHandler(handler)
    formatter = logging.Formatter(
        '%(asctime)s, [%(levelname)s] %(message)s'
    )
    handler.setFormatter(formatter)

    executor.start_polling(dp, skip_updates=True)
