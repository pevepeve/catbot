from random import choice
from datetime import date
import aiofiles
import logging
import json
import os
from attr import s

from sqlitedict import SqliteDict
from aiogram import Bot, Dispatcher, executor, types

from data.config.config import API_TOKEN


SCRAPED_SITE = 'https://subsplease.org'
MEDIA_FOLDER = 'media/'
SHOWS_FOLDER = '/shows/'
NEKODIR = 'media/nekochans/'
JSON_FILE = 'anime.json'
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
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    await message.reply('Hi!\nI\'m CatgirlBot, I send catgirls and anime schedules.')


@dp.message_handler(commands=['animetoday'])
async def animetoday(message: types.Message):
    today_anime = anime_dict[days_list[date.today().weekday()]]
    text = f'Сегодня {days_list_ru[date.today().weekday()]}, и выходят с субтитрами аниме:\n'
    for title_item in today_anime:
        formatted_str = f'*{title_item["title"]}* : {title_item["time"]} \n'
        text += formatted_str

    await message.answer(text, parse_mode='MarkdownV2')


@dp.message_handler(commands=['neko'])
async def neko(message: types.Message):
    random_file = choice(os.listdir(NEKODIR))
    async with aiofiles.open(NEKODIR+random_file, mode='rb') as photo:
        await message.reply_photo(photo, caption='Держи кошкодевочку!')


@dp.message_handler(regexp='(^кек$)')
async def kek(message: types.Message):

    await message.answer('КЕК!')

@dp.message_handler(commands=['save'])
async def save(message: types.Message):
    if message.reply_to_message:
        saveable = message.reply_to_message.text
        if len(message.text.split()) > 1:
            if message.text.split()[1]:
                mesg_tag = message.text.split()[1]
        else:
            mesg_tag = 'undefined'
        saved_messages_table[len(saved_messages_table)] = {
            'tag': mesg_tag,
            'message': saveable,
            'by': message.reply_to_message.from_user.first_name}
        await message.answer('Saved')
    else:
        await message.answer('Nothing to save')


@dp.message_handler(commands=['unpack'])
async def unpack(message: types.Message):
    if len(message.text.split()) > 1 and len(saved_messages_table) > int(message.text.split()[1]):
        reply_dic = saved_messages_table[message.text.split()[1]]
        reply = 'By: <b>' + reply_dic['by'] + '</b>, tag: <b>' + reply_dic['tag']+'</b>\n'
        reply += reply_dic['message']
        await message.answer(reply, parse_mode='HTML')
    else:
        await message.answer('Nothing to unpack')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
