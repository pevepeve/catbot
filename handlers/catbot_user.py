from aiogram import Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
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

router = Router()
anime_service = AnimeService(AnimeRepository())
chat_history_service = ChatHistoryService(MessageRepository())
summary_service = SummaryService(chat_history_service)
link_service = LinkService()
neko_service = NekoService(NekoRepository())


@router.callback_query(F.data.startswith("weekday_") | F.data.startswith("back_"))
async def callbacks_weekday(callback_query: CallbackQuery):
    weekday_q = callback_query.data.split("_")[1]
    today_anime = anime_service.get_schedule_for_weekday(weekday_q)
    day_pretty = anime_service.get_day_label(weekday_q).capitalize()
    message_text = f"<b>{day_pretty}</b> - {texts.ANIME_DAY_PREFIX}\n"
    for num, title_item in enumerate(today_anime):
        message_text += f'<b>{num}. {title_item["title"]}</b> : {title_item["time"]} \n'

    await callback_query.answer(emojize(":check_mark_button:"))
    if callback_query.message:
        await callback_query.message.answer(
            message_text,
            reply_markup=get_keyboard_days(
                anime_service.days_list,
                anime_service.days_list_ru,
                weekday_q,
            ),
        )


@router.callback_query(F.data.startswith("anime_"))
async def callbacks_anime(callback_query: CallbackQuery):
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

    if callback_query.message:
        await callback_query.message.reply_photo(
            thumb_id,
            caption=message_text,
            reply_markup=get_keyboard_back(weekday_q),
        )


@router.callback_query(F.data.startswith("animedayc_"))
async def callbacks_animechoice(callback_query: CallbackQuery):
    weekday_q = callback_query.data.split("_")[1]
    today_anime = anime_service.get_schedule_for_weekday(weekday_q)
    if callback_query.message:
        await callback_query.message.answer(
            texts.ANIME_PICK_TITLE,
            reply_markup=get_keyboard_animes(today_anime, weekday_q),
            parse_mode=ParseMode.MARKDOWN_V2,
        )


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply(texts.START_TEXT)


@router.message(Command("help"))
async def cmd_help(message: Message):
    help_lines = "\n".join(texts.HELP_LINES)
    await message.reply(
        f"<b>{texts.HELP_TITLE}</b>\n{help_lines}",
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("animetoday"))
async def cmd_animetoday(message: Message):
    weekday, today_anime = anime_service.get_today_schedule()
    day_label = anime_service.get_day_label(weekday)
    message_text = texts.ANIME_TODAY_PREFIX.format(day_label=day_label)
    for num, title_item in enumerate(today_anime):
        message_text += f'<b>{num}. {title_item["title"]}</b> : {title_item["time"]} \n'

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.MORE_DETAILS,
                    callback_data="animedayc_" + weekday,
                )
            ]
        ]
    )
    await message.answer(
        message_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )


@router.message(Command("neko"))
async def cmd_neko(message: Message):
    try:
        random_neko_id = await neko_service.get_random_neko_id()
        await message.reply_photo(random_neko_id, caption=texts.NEKO_CAPTION)
    except Exception as error:
        await message.answer(str(error))


@router.message(Command("animes"))
async def cmd_animeschedules(message: Message):
    await message.answer(
        texts.ANIME_PICK_DAY,
        reply_markup=get_keyboard_days(
            anime_service.days_list,
            anime_service.days_list_ru,
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


@router.message(Command("tldr"))
async def cmd_tldr(message: Message):
    summary = await summary_service.summarize_recent(message.chat.id)
    await message.answer(
        texts.TLDR_PREFIX + summary,
        parse_mode=ParseMode.HTML,
    )


@router.message(F.text.regexp(r"(^кек$)"))
async def kek(message: Message):
    await message.answer(texts.KEK)


@router.message(F.text.regexp(r"https:\/\/twitter\.com\/\b"))
async def twitter_nitter(message: Message):
    await chat_history_service.save_message(message.text, message.date, message.chat.id)
    nittered = link_service.rewrite_twitter_link(message.text)
    if nittered:
        await message.answer(nittered)


@router.message(F.text)
async def textsave(message: Message):
    await chat_history_service.save_message(message.text, message.date, message.chat.id)


def register_handlers_user(dispatcher: Dispatcher):
    dispatcher.include_router(router)
