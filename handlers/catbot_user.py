import json
from datetime import date
import re

from aiogram import Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils.markdown import bold, text
from emoji import emojize

from common.db_methods import (
    get_random_nekochan, get_thumb_id, save_to_db, get_last_messages)
from common.summary import summarize_sumy

ROW_LEN_WEEK_BUTTONS = 4
ROW_LEN_TITLES_BUTTONS = 2
LETTERS_IN_TITLE_BTN = 7
ANIME_SCHEDULE_JSON_FILE = 'anime.json'
MAX_LEN_CAPTION = 1023
NITTER_INSTANCE = 'https://nitter.hu/'

days_list = ['Monday', 'Tuesday', 'Wednesday',
             'Thursday', 'Friday', 'Saturday', 'Sunday']
days_list_ru = ['понедельник', 'вторник', 'среда',
                'четверг', 'пятница', 'суббота', 'воскресенье']


with open(ANIME_SCHEDULE_JSON_FILE, mode='rb') as json_anime:
    anime_dict = json.load(json_anime)

# Keyboards


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


def get_keyboard_back(weekday):
    kb_back = types.InlineKeyboardMarkup()
    buttons = [types.InlineKeyboardButton(
        text='Назад', callback_data='back_' + weekday), ]
    kb_back.add(*buttons)
    return kb_back

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
    text = f'<b>{anime_title["title"]} : {days_list_ru[days_list.index(weekday_q)]}, {anime_title["time"]}</b>\n'
    text += f' {anime_title["synopsis"]} \n'
    await callback_query.answer(emojize(':check_mark_button:'))
    thumb_id = await get_thumb_id(anime_title['image'])
    if len(text) > MAX_LEN_CAPTION:
        text = text[:MAX_LEN_CAPTION-4]+'...'
    await callback_query.message.reply_photo(thumb_id,
                                             caption=text,
                                             reply_markup=get_keyboard_back(weekday_q))


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
                             '/help - этот текст',
                             '/neko - отправляет картинку с кошкодевочкой',
                             '/animetoday - какое аниме выходит сегодня',
                             '/animes - аниме этого сезона',
                             '/tldr - суммаризация последних сообщений беседы',
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
    await message.answer(text,
                         parse_mode=ParseMode.HTML,
                         reply_markup=kb_moreinfo)


async def cmd_neko(message: types.Message):
    try:
        random_neko_id = await get_random_nekochan()
        neko_caption = 'Держи кошкодевочку!'
        await message.reply_photo(random_neko_id, caption=neko_caption)
    except Exception as e:
        await message.answer(str(e) + random_neko_id)


async def cmd_animeschedules(message: types.Message):
    text = f'*Выберите день*:\n'
    await message.answer(text,
                         reply_markup=get_keyboard_days(),
                         parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_tldr(message: types.Message):
    msgstext = await get_last_messages(message.chat.id)
    summary = 'Вкратце в предыдущих сообщениях:\n' + \
        summarize_sumy('. \n'.join(msgstext))
    await message.answer(summary, parse_mode=ParseMode.HTML)

###############################
#     MESSAGE HANDLERS
###############################


async def kek(message: types.Message):
    await message.answer('КЕК!')


async def twitter_nitter(message: types.Message):
    match = re.match(r'(https:\/\/twitter\.com\/\S*\/status\/\d*)\b', message.text)
    nittered = match[1].replace('https://twitter.com/', NITTER_INSTANCE)
    await message.answer(nittered)
    await save_to_db(message.text, message.date, message.chat.id)


async def textsave(message: types.Message):
    await save_to_db(message.text, message.date, message.chat.id)


def register_handlers_user(dp: Dispatcher):
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
    dp.register_message_handler(cmd_tldr, commands=['tldr'], state="*")

    dp.register_message_handler(kek, regexp='(^кек$)', state="*")
    dp.register_message_handler(
        twitter_nitter, regexp=r'(https:\/\/twitter\.com\/\S*\/status\/\d*)\b',
        state="*")
    dp.register_message_handler(textsave, state="*")
