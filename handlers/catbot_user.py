from html import escape

from aiogram import Dispatcher, F, Router
from aiogram.enums import ChatMemberStatus, ChatType, ParseMode
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from emoji import emojize

import texts
from repositories import AnimeRepository, MessageRepository, NekoRepository
from services import (
    AnimeService,
    ChatHistoryService,
    NekoService,
    SummaryService,
)
from ui import get_keyboard_animes, get_keyboard_back, get_keyboard_days


MAX_LEN_MESSAGE = 4096
CALLBACK_EXPIRED_TEXT = "This menu has expired. Run the command again."
CALLBACK_FOREIGN_TEXT = "Only the user who opened this menu can use these buttons."
CALLBACK_MUTED_TEXT = "Muted users cannot use this menu in the chat."

router = Router()
anime_service = AnimeService(AnimeRepository())
chat_history_service = ChatHistoryService(MessageRepository())
summary_service = SummaryService(chat_history_service)
neko_service = NekoService(NekoRepository())


def split_callback_owner(callback_data: str) -> tuple[str, int | None]:
    payload, separator, owner_id = callback_data.rpartition("_")
    if separator and owner_id.isdigit():
        return payload, int(owner_id)
    return callback_data, None


def build_weekday_message(weekday: str) -> str:
    today_anime = anime_service.get_schedule_for_weekday(weekday)
    day_pretty = escape(anime_service.get_day_label(weekday).capitalize())
    message_text = f"<b>{day_pretty}</b> - {escape(texts.ANIME_DAY_PREFIX)}\n"
    for num, title_item in enumerate(today_anime):
        title = escape(title_item["title"])
        time_value = escape(title_item["time"])
        message_text += f"<b>{num}. {title}</b> : {time_value} \n"
    return message_text


def build_anime_message(weekday: str, title_index: int) -> str:
    anime_title = anime_service.get_anime_details(weekday, title_index)
    title = escape(anime_title["title"])
    day_label = escape(anime_service.get_day_label(weekday))
    time_value = escape(anime_title["time"])
    synopsis = escape(anime_title.get("synopsis", ""))
    show_url = escape(anime_title["url"], quote=True)
    header = (
        f"<b>{title} : "
        f"{day_label}, {time_value}</b>\n"
    )
    link_line = f'<a href="{show_url}">SubsPlease</a>\n'

    if synopsis:
        synopsis_block = f"{synopsis}\n\n"
        available_synopsis_len = MAX_LEN_MESSAGE - len(header) - len(link_line)
        if available_synopsis_len < len(synopsis_block):
            synopsis_block = synopsis_block[: max(available_synopsis_len - 3, 0)] + "..."
        return header + synopsis_block + link_line

    return header + link_line


async def can_use_chat_menu(callback_query: CallbackQuery) -> bool:
    if not callback_query.message or callback_query.message.chat.type == ChatType.PRIVATE:
        return True

    member = await callback_query.bot.get_chat_member(
        callback_query.message.chat.id,
        callback_query.from_user.id,
    )
    if member.status in {
        ChatMemberStatus.CREATOR,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.MEMBER,
    }:
        return True
    if member.status == ChatMemberStatus.RESTRICTED:
        return bool(member.can_send_messages)
    return False


async def ensure_callback_access(callback_query: CallbackQuery) -> tuple[str, int | None] | None:
    if not callback_query.data:
        await callback_query.answer(CALLBACK_EXPIRED_TEXT, show_alert=True)
        return None

    payload, owner_id = split_callback_owner(callback_query.data)
    if owner_id is None:
        await callback_query.answer(CALLBACK_EXPIRED_TEXT, show_alert=True)
        return None
    if owner_id != callback_query.from_user.id:
        await callback_query.answer(CALLBACK_FOREIGN_TEXT, show_alert=True)
        return None
    if not await can_use_chat_menu(callback_query):
        await callback_query.answer(CALLBACK_MUTED_TEXT, show_alert=True)
        return None
    return payload, owner_id


async def safe_edit_text(message: Message, text: str, **kwargs) -> None:
    try:
        await message.edit_text(text, **kwargs)
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise


@router.callback_query(F.data.startswith("weekday_") | F.data.startswith("back_"))
async def callbacks_weekday(callback_query: CallbackQuery):
    access = await ensure_callback_access(callback_query)
    if access is None or not callback_query.message:
        return

    payload, owner_id = access
    weekday_q = payload.split("_")[1]
    message_text = build_weekday_message(weekday_q)

    if callback_query.message:
        await safe_edit_text(
            callback_query.message,
            message_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_keyboard_days(
                anime_service.days_list,
                anime_service.days_list_ru,
                weekday_q,
                owner_id=owner_id,
            ),
        )
    await callback_query.answer(emojize(":check_mark_button:"))


@router.callback_query(F.data.startswith("anime_"))
async def callbacks_anime(callback_query: CallbackQuery):
    access = await ensure_callback_access(callback_query)
    if access is None or not callback_query.message:
        return

    payload, owner_id = access
    _, weekday_q, title_q = payload.split("_")
    message_text = build_anime_message(weekday_q, int(title_q))

    await safe_edit_text(
        callback_query.message,
        message_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_keyboard_back(weekday_q, owner_id=owner_id),
    )
    await callback_query.answer(emojize(":check_mark_button:"))


@router.callback_query(F.data.startswith("animedayc_"))
async def callbacks_animechoice(callback_query: CallbackQuery):
    access = await ensure_callback_access(callback_query)
    if access is None or not callback_query.message:
        return

    payload, owner_id = access
    weekday_q = payload.split("_")[1]
    today_anime = anime_service.get_schedule_for_weekday(weekday_q)
    await safe_edit_text(
        callback_query.message,
        texts.ANIME_PICK_TITLE,
        reply_markup=get_keyboard_animes(today_anime, weekday_q, owner_id=owner_id),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    await callback_query.answer(emojize(":check_mark_button:"))


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
    day_label = escape(anime_service.get_day_label(weekday))
    message_text = escape(texts.ANIME_TODAY_PREFIX).format(day_label=day_label)
    for num, title_item in enumerate(today_anime):
        title = escape(title_item["title"])
        time_value = escape(title_item["time"])
        message_text += f"<b>{num}. {title}</b> : {time_value} \n"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.MORE_DETAILS,
                    callback_data=f"animedayc_{weekday}_{message.from_user.id}",
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
            owner_id=message.from_user.id,
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


@router.message(F.text)
async def textsave(message: Message):
    await chat_history_service.save_message(message.text, message.date, message.chat.id)


def register_handlers_user(dispatcher: Dispatcher):
    dispatcher.include_router(router)
