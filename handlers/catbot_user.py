import io
from html import escape
import logging

from aiogram import Dispatcher, F, Router
from aiogram.enums import ChatMemberStatus, ChatType, ParseMode
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)
from emoji import emojize
from sqlalchemy.exc import NoResultFound

import texts
from repositories import (
    AnimeRepository,
    MessageImageOCRRepository,
    MessageRepository,
    NekoRepository,
)
from services import (
    AnimeService,
    ChatHistoryService,
    MessageImageOCRService,
    NekoService,
    OCRService,
    SummaryService,
)
from ui import get_keyboard_animes, get_keyboard_close_detail, get_keyboard_days


MAX_LEN_MESSAGE = 4096
MAX_LEN_CAPTION = 1024
CALLBACK_EXPIRED_TEXT = "This menu has expired. Run the command again."
CALLBACK_FOREIGN_TEXT = "Only the user who opened this menu can use these buttons."
CALLBACK_MUTED_TEXT = "Muted users cannot use this menu in the chat."
anime_detail_messages: dict[tuple[int, int], int] = {}

router = Router()
anime_service = AnimeService(AnimeRepository())
chat_history_service = ChatHistoryService(MessageRepository())
summary_service = SummaryService(chat_history_service)
neko_service = NekoService(NekoRepository())
ocr_service = OCRService()
message_image_ocr_service = MessageImageOCRService(
    MessageImageOCRRepository(),
    ocr_service,
)
logger = logging.getLogger(__name__)


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
        available_synopsis_len = MAX_LEN_CAPTION - len(header) - len(link_line)
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


async def safe_delete_message(bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id, message_id)
    except TelegramBadRequest:
        return


async def close_detail_message(chat_id: int, menu_message_id: int, bot) -> None:
    detail_message_id = anime_detail_messages.pop((chat_id, menu_message_id), None)
    if detail_message_id is not None:
        await safe_delete_message(bot, chat_id, detail_message_id)


def split_photo_back_payload(callback_data: str) -> tuple[int, int] | None:
    payload, owner_id = split_callback_owner(callback_data)
    if owner_id is None or not payload.startswith("photoback_"):
        return None
    menu_message_id = payload.split("_")[1]
    if not menu_message_id.isdigit():
        return None
    return int(menu_message_id), owner_id


def build_thumbnail_input(anime_title: dict):
    image_filename = anime_title["image"]
    try:
        return anime_service.get_thumbnail_id(image_filename)
    except NoResultFound:
        image_path = anime_service.client.media_folder / image_filename
        return FSInputFile(image_path, filename=image_filename)


async def persist_uploaded_thumbnail(anime_title: dict, message: Message) -> None:
    if not message.photo:
        return
    anime_service.repository.save_thumbnail_id(
        message.photo[-1].file_id,
        anime_title["image"],
    )


def get_chat_type_value(chat_type) -> str:
    return getattr(chat_type, "value", str(chat_type))


def get_media_source(message: Message):
    if message.photo:
        return message.photo[-1]
    if message.document and (message.document.mime_type or "").startswith("image/"):
        return message.document
    return None


def extract_command_arguments(text: str | None) -> str:
    if not text:
        return ""
    _, _, arguments = text.partition(" ")
    return arguments.strip()


def get_factcheck_claim_text(message: Message) -> str:
    if message.reply_to_message:
        replied_content = message.reply_to_message.text or message.reply_to_message.caption or ""
        if replied_content.strip():
            return replied_content.strip()
    return extract_command_arguments(message.text)


@router.callback_query(F.data.startswith("weekday_") | F.data.startswith("back_"))
async def callbacks_weekday(callback_query: CallbackQuery):
    access = await ensure_callback_access(callback_query)
    if access is None or not callback_query.message:
        return

    payload, owner_id = access
    weekday_q = payload.split("_")[1]
    message_text = build_weekday_message(weekday_q)
    await close_detail_message(
        callback_query.message.chat.id,
        callback_query.message.message_id,
        callback_query.bot,
    )

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
    anime_title = anime_service.get_anime_details(weekday_q, int(title_q))
    caption = build_anime_message(weekday_q, int(title_q))
    media = InputMediaPhoto(
        media=build_thumbnail_input(anime_title),
        caption=caption,
        parse_mode=ParseMode.HTML,
    )
    detail_key = (callback_query.message.chat.id, callback_query.message.message_id)
    detail_message_id = anime_detail_messages.get(detail_key)
    reply_markup = get_keyboard_close_detail(
        callback_query.message.message_id,
        owner_id,
    )

    if detail_message_id is not None:
        try:
            updated_message = await callback_query.bot.edit_message_media(
                chat_id=callback_query.message.chat.id,
                message_id=detail_message_id,
                media=media,
                reply_markup=reply_markup,
            )
            if isinstance(updated_message, Message):
                await persist_uploaded_thumbnail(anime_title, updated_message)
        except TelegramBadRequest as error:
            if "message is not modified" in str(error):
                await callback_query.answer(emojize(":check_mark_button:"))
                return
            detail_message_id = None

    if detail_message_id is None:
        detail_message = await callback_query.message.reply_photo(
            photo=build_thumbnail_input(anime_title),
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
        anime_detail_messages[detail_key] = detail_message.message_id
        await persist_uploaded_thumbnail(anime_title, detail_message)

    await callback_query.answer(emojize(":check_mark_button:"))


@router.callback_query(F.data.startswith("animedayc_"))
async def callbacks_animechoice(callback_query: CallbackQuery):
    access = await ensure_callback_access(callback_query)
    if access is None or not callback_query.message:
        return

    payload, owner_id = access
    weekday_q = payload.split("_")[1]
    today_anime = anime_service.get_schedule_for_weekday(weekday_q)
    await close_detail_message(
        callback_query.message.chat.id,
        callback_query.message.message_id,
        callback_query.bot,
    )
    await safe_edit_text(
        callback_query.message,
        texts.ANIME_PICK_TITLE,
        reply_markup=get_keyboard_animes(today_anime, weekday_q, owner_id=owner_id),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    await callback_query.answer(emojize(":check_mark_button:"))


@router.callback_query(F.data.startswith("photoback_"))
async def callbacks_photo_back(callback_query: CallbackQuery):
    if not callback_query.data or not callback_query.message:
        await callback_query.answer(CALLBACK_EXPIRED_TEXT, show_alert=True)
        return

    parsed = split_photo_back_payload(callback_query.data)
    if parsed is None:
        await callback_query.answer(CALLBACK_EXPIRED_TEXT, show_alert=True)
        return

    menu_message_id, owner_id = parsed
    if owner_id != callback_query.from_user.id:
        await callback_query.answer(CALLBACK_FOREIGN_TEXT, show_alert=True)
        return
    if not await can_use_chat_menu(callback_query):
        await callback_query.answer(CALLBACK_MUTED_TEXT, show_alert=True)
        return

    anime_detail_messages.pop((callback_query.message.chat.id, menu_message_id), None)
    await safe_delete_message(
        callback_query.bot,
        callback_query.message.chat.id,
        callback_query.message.message_id,
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
    summary_response = await summary_service.summarize_recent_response(message.chat.id)
    await message.answer(
        texts.TLDR_PREFIX + escape(summary_response.text),
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("factcheck"))
async def cmd_factcheck(message: Message):
    claim_text = get_factcheck_claim_text(message)
    if not claim_text:
        await message.answer(texts.FACTCHECK_USAGE)
        return

    try:
        result = await summary_service.factcheck_claim(claim_text)
    except RuntimeError as error:
        error_message = str(error)
        if "not configured" in error_message:
            await message.answer(texts.FACTCHECK_UNAVAILABLE)
            return
        logger.exception("Fact check command failed for chat_id=%s", message.chat.id)
        await message.answer(texts.FACTCHECK_FAILED)
        return

    await message.answer(
        texts.FACTCHECK_PREFIX + escape(result),
        parse_mode=ParseMode.HTML,
    )


@router.message(F.photo | F.document)
async def index_image_message(message: Message):
    media_source = get_media_source(message)
    if media_source is None:
        return

    caption_text = message.caption or ""
    if message.from_user:
        speaker_name = message.from_user.username or message.from_user.full_name
        user_id = message.from_user.id
    else:
        speaker_name = "Unknown"
        user_id = None

    ocr_result = None
    ocr_attempted = False
    if ocr_service.is_available:
        file_io = io.BytesIO()
        try:
            await message.bot.download(media_source, destination=file_io)
            ocr_result = ocr_service.extract_text(file_io)
            ocr_attempted = True
        except Exception:
            logger.exception(
                "Failed OCR indexing for chat_id=%s message_id=%s",
                message.chat.id,
                message.message_id,
            )
            ocr_result = None

    try:
        message_image_ocr_service.save_message_image(
            chat_id=message.chat.id,
            chat_name=message.chat.title or message.chat.full_name or "",
            chat_username=message.chat.username or "",
            chat_type=get_chat_type_value(message.chat.type),
            message_id=message.message_id,
            message_date=message.date.isoformat(),
            user_id=user_id,
            user_name=speaker_name,
            caption_text=caption_text,
            file_id=media_source.file_id,
            file_unique_id=media_source.file_unique_id,
            ocr_result=ocr_result,
            ocr_attempted=ocr_attempted,
        )
    except Exception:
        logger.exception(
            "Failed saving image OCR index for chat_id=%s message_id=%s",
            message.chat.id,
            message.message_id,
        )


@router.message(F.text.regexp(r"(^кек$)"))
async def kek(message: Message):
    await message.answer(texts.KEK)


@router.message(F.text | F.caption)
async def textsave(message: Message):
    content = message.text or message.caption
    if not content:
        return

    if message.from_user:
        speaker_name = message.from_user.username or message.from_user.full_name
        user_id = message.from_user.id
    else:
        speaker_name = "Unknown"
        user_id = None

    await chat_history_service.save_message(
        text=content,
        message_date=message.date.isoformat(),
        chat_id=message.chat.id,
        chat_name=message.chat.title or message.chat.full_name or "",
        chat_username=message.chat.username or "",
        chat_type=get_chat_type_value(message.chat.type),
        message_id=message.message_id,
        user_id=user_id,
        user_name=speaker_name,
        reply_to_message_id=(
            message.reply_to_message.message_id if message.reply_to_message else None
        ),
        content_type="caption" if message.caption else "text",
    )


def register_handlers_user(dispatcher: Dispatcher):
    dispatcher.include_router(router)
