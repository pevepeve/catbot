from aiogram import Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils.markdown import bold, text
from emoji import emojize

import texts
from repositories import AnimeRepository, MessageRepository, NekoRepository
from services import (
    AnimeService,
    ChatHistoryService,
    LinkService,
    NekoService,
    SummaryService,
)
from ui import get_keyboard_animes, get_keyboard_back, get_keyboard_days


MAX_LEN_CAPTION = 1023

anime_service = AnimeService(AnimeRepository())
chat_history_service = ChatHistoryService(MessageRepository())
summary_service = SummaryService(chat_history_service)
link_service = LinkService()
neko_service = NekoService(NekoRepository())


async def callbacks_weekday(callback_query: types.CallbackQuery):
    weekday_q = callback_query.data.split("_")[1]
    today_anime = anime_service.get_schedule_for_weekday(weekday_q)
    day_pretty = anime_service.get_day_label(weekday_q).capitalize()
    message_text = f"<b>{day_pretty}</b> - {texts.ANIME_DAY_PREFIX}\n"
    for num, title_item in enumerate(today_anime):
        formatted_str = f'<b>{num}. {title_item["title"]}</b> : {title_item["time"]} \n'
        message_text += formatted_str

    await callback_query.answer(emojize(":check_mark_button:"))
    await callback_query.message.answer(
        message_text,
        reply_markup=get_keyboard_days(
            anime_service.days_list,
            anime_service.days_list_ru,
            weekday_q,
        ),
    )


async def callbacks_anime(callback_query: types.CallbackQuery):
    weekday_q = callback_query.data.split("_")[1]
    title_q = int(callback_query.data.split("_")[2])
    anime_title = anime_service.get_anime_details(weekday_q, title_q)
    message_text = (
        f'<b>{anime_title["title"]} : '
        f'{anime_service.get_day_label(weekday_q)}, {anime_title["time"]}</b>\n'
    )
    message_text += f' {anime_title["synopsis"]} \n'

    await callback_query.answer(emojize(":check_mark_button:"))
    thumb_id = anime_service.get_thumbnail_id(anime_title["image"])
    if len(message_text) > MAX_LEN_CAPTION:
        message_text = message_text[: MAX_LEN_CAPTION - 4] + "..."

    await callback_query.message.reply_photo(
        thumb_id,
        caption=message_text,
        reply_markup=get_keyboard_back(weekday_q),
    )


async def callbacks_animechoice(callback_query: types.CallbackQuery):
    weekday_q = callback_query.data.split("_")[1]
    today_anime = anime_service.get_schedule_for_weekday(weekday_q)
    await callback_query.message.answer(
        texts.ANIME_PICK_TITLE,
        reply_markup=get_keyboard_animes(today_anime, weekday_q),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def cmd_start(message: types.Message):
    await message.reply(texts.START_TEXT)


async def cmd_help(message: types.Message):
    await message.reply(
        text(
            bold(texts.HELP_TITLE),
            *texts.HELP_LINES,
            sep="\n",
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def cmd_animetoday(message: types.Message):
    weekday, today_anime = anime_service.get_today_schedule()
    day_label = anime_service.get_day_label(weekday)
    message_text = texts.ANIME_TODAY_PREFIX.format(day_label=day_label)
    for num, title_item in enumerate(today_anime):
        formatted_str = f'<b>{num}. {title_item["title"]}</b> : {title_item["time"]} \n'
        message_text += formatted_str

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton(
            text=texts.MORE_DETAILS,
            callback_data="animedayc_" + weekday,
        )
    )
    await message.answer(
        message_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )


async def cmd_neko(message: types.Message):
    try:
        random_neko_id = await neko_service.get_random_neko_id()
        await message.reply_photo(random_neko_id, caption=texts.NEKO_CAPTION)
    except Exception as error:
        await message.answer(str(error))


async def cmd_animeschedules(message: types.Message):
    await message.answer(
        texts.ANIME_PICK_DAY,
        reply_markup=get_keyboard_days(
            anime_service.days_list,
            anime_service.days_list_ru,
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def cmd_tldr(message: types.Message):
    summary = await summary_service.summarize_recent(message.chat.id)
    await message.answer(
        texts.TLDR_PREFIX + summary,
        parse_mode=ParseMode.HTML,
    )


async def kek(message: types.Message):
    await message.answer(texts.KEK)


async def twitter_nitter(message: types.Message):
    await chat_history_service.save_message(message.text, message.date, message.chat.id)
    nittered = link_service.rewrite_twitter_link(message.text)
    if nittered:
        await message.answer(nittered)


async def textsave(message: types.Message):
    await chat_history_service.save_message(message.text, message.date, message.chat.id)


def register_handlers_user(dp: Dispatcher):
    dp.register_callback_query_handler(
        callbacks_weekday,
        text_startswith=["weekday_", "back_"],
        state="*",
    )
    dp.register_callback_query_handler(
        callbacks_anime,
        text_startswith="anime_",
        state="*",
    )
    dp.register_callback_query_handler(
        callbacks_animechoice,
        text_startswith=["animedayc_"],
        state="*",
    )

    dp.register_message_handler(cmd_start, commands=["start"], state="*")
    dp.register_message_handler(cmd_help, commands=["help"], state="*")
    dp.register_message_handler(cmd_animetoday, commands=["animetoday"], state="*")
    dp.register_message_handler(cmd_neko, commands=["neko"], state="*")
    dp.register_message_handler(cmd_animeschedules, commands=["animes"], state="*")
    dp.register_message_handler(cmd_tldr, commands=["tldr"], state="*")

    dp.register_message_handler(kek, regexp="(^кек$)", state="*")
    dp.register_message_handler(
        twitter_nitter,
        regexp=r"https:\/\/twitter\.com\/\b",
        state="*",
    )
    dp.register_message_handler(textsave, state="*")

