import json
import io
import hashlib
from bot import ADMIN_ID, API_TOKEN, DB_FILENAME
import logging
from aiogram import Bot
import os

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from datetime import date
from random import randrange

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text, IDFilter
from aiogram.types import ParseMode
from aiogram.utils.markdown import bold, text
from emoji import emojize
from sqlalchemy import func, select

from db_neko import Base, AnimeThumbsIds, NekoIds

bot = Bot(token=API_TOKEN)

engine = create_engine(f'sqlite:///{DB_FILENAME}')
session_factory = sessionmaker(
    bind=engine, expire_on_commit=False)
Session = scoped_session(session_factory)

if not os.path.isfile(f'./{DB_FILENAME}'):
    Base.metadata.create_all(engine)

ROW_LEN_WEEK_BUTTONS = 4
ROW_LEN_TITLES_BUTTONS = 2
LETTERS_IN_TITLE_BTN = 7
ANIME_SCHEDULE_JSON_FILE = 'anime.json'
MAX_LEN_CAPTION = 1023

days_list = ['Monday', 'Tuesday', 'Wednesday',
             'Thursday', 'Friday', 'Saturday', 'Sunday']
days_list_ru = ['понедельник', 'вторник', 'среда',
                'четверг', 'пятница', 'суббота', 'воскресенье']


with open(ANIME_SCHEDULE_JSON_FILE, mode='rb') as json_anime:
    anime_dict = json.load(json_anime)


async def get_anime_thumbs_from_db():
    pass


async def get_random_nekochan():
    count_nekos = await Session.execute(func.count(NekoIds.filename))
    random_neko = randrange(1, count_nekos.scalar_one())
    nekoid = await Session.execute(select(NekoIds.file_id).where(
        NekoIds.id == random_neko))
    return nekoid.scalar_one()


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


async def callbacks_weekday(callback_query: types.CallbackQuery):
    weekday_q = callback_query.data.split("_")[1]
    today_anime = anime_dict[weekday_q]
    day_pretty = days_list_ru[days_list.index(weekday_q)].capitalize()
    text = f'<b>{day_pretty}</b> - с субтитрами выходят аниме:\n'
    for num, title_item in enumerate(today_anime):
        formatted_str = f'<b>{num}. {title_item["title"]}</b> : {title_item["time"]} \n'
        text += formatted_str
    await callback_query.answer(emojize(':check_mark_button:'))
    await callback_query.message.answer(text, reply_markup=get_keyboard_days(weekday_q))


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
    await callback_query.answer(emojize(':check_mark_button:'))
    thumb_id = await Session.execute(select(AnimeThumbsIds.file_id).where(
        AnimeThumbsIds.filename == anime_title['image']))
    if len(text) > MAX_LEN_CAPTION:
        text = text[:MAX_LEN_CAPTION-4]+'...'
    await callback_query.message.reply_photo(thumb_id.scalar_one(), caption=text, reply_markup=kb_back)


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


async def cmd_start(message: types.Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    await message.reply('Hi!\nI send catgirls and anime schedules.')


async def cmd_help(message: types.Message):
    await message.reply(text(bold('Я могу ответить на следующие команды:'),
                             '/start',
                             '/help',
                             '/neko',
                             '/animetoday',
                             sep='\n'),
                        parse_mode=ParseMode.MARKDOWN_V2)


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


async def cmd_neko(message: types.Message):
    random_neko_id = await get_random_nekochan()
    neko_caption = 'Держи кошкодевочку!'
    await message.reply_photo(random_neko_id, caption=neko_caption)

'''
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
'''


async def cmd_animeschedules(message: types.Message):
    text = f'*Выберите день*:\n'
    await message.answer(text, reply_markup=get_keyboard_days(), parse_mode=ParseMode.MARKDOWN_V2)


async def photo_upload(file_io: io.BytesIO, md5: str):
    exists = Session.execute(select(NekoIds.filename).where(
        NekoIds.filename == md5+'.jpg')).scalars().first() is not None
    if exists:
        logging.info(
            f'File {md5} is already in the database')
        raise ValueError('Already exists')
    logging.info(f'Started processing {md5}')
    try:
        with file_io as file:
            msg = await bot.send_photo(ADMIN_ID, file, disable_notification=True)
            file_id = msg.photo[-1].file_id
            session = Session()
            newItem = NekoIds(file_id=file_id, filename=md5+'.jpg')
            try:
                session.add(newItem)
                session.commit()
            except Exception as e:
                logging.error(
                    'Couldn\'t upload {}. Error is {}'.format(md5, e))
            else:
                logging.info(
                    f'Successfully uploaded and saved to DB'
                    f' file {md5} with id {file_id}')
            finally:
                session.close()
    except Exception as e:
        logging.error(
            'Couldn\'t upload {}. Error is {}'.format(md5, e))


async def cmd_addneko(message: types.Message):
    if message.reply_to_message:
        saveable_id = message.reply_to_message.photo[-1].file_id
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

###############################
#     MESSAGE HANDLERS
###############################


async def kek(message: types.Message):

    await message.answer('КЕК!')


def register_handlers_user(dp: Dispatcher, admin_id: int):
    dp.register_callback_query_handler(callbacks_weekday, text_startswith=[
                                       'weekday_', 'back_'], state="*")
    dp.register_callback_query_handler(
        callbacks_anime, text_startswith='anime_', state="*")
    dp.register_callback_query_handler(
        callbacks_animechoice, text_startswith=['animedayc_'], state="*")
    dp.register_message_handler(cmd_start, commands=['start'], state="*")
    dp.register_message_handler(cmd_help, commands=['help'], state="*")
    dp.register_message_handler(cmd_animetoday, commands=[
                                'animetoday'], state="*")
    dp.register_message_handler(cmd_neko, commands=['neko'], state="*")
    dp.register_message_handler(
        cmd_animeschedules, commands=['animes'], state="*")
    dp.register_message_handler(cmd_addneko, IDFilter(user_id=admin_id), commands=['addneko'],  content_types=[
                                'photo'], commands_ignore_caption=False, state="*")
    dp.register_message_handler(cmd_addneko, IDFilter(user_id=admin_id), commands=[
                                'addneko'], commands_ignore_caption=False, state="*")
    dp.register_message_handler(kek, regexp='(^кек$)', state="*")
