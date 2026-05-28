from typing import Optional

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import texts


ROW_LEN_WEEK_BUTTONS = 4
ROW_LEN_TITLES_BUTTONS = 2
LETTERS_IN_TITLE_BTN = 7


def chunk_buttons(buttons, row_width):
    return [buttons[index:index + row_width] for index in range(0, len(buttons), row_width)]


def with_owner(callback_data: str, owner_id: Optional[int] = None) -> str:
    if owner_id is None:
        return callback_data
    return f"{callback_data}_{owner_id}"


def get_keyboard_days(
    days_list: list[str],
    days_list_ru: list[str],
    day: Optional[str] = None,
    owner_id: Optional[int] = None,
):
    buttons = [
        InlineKeyboardButton(
            text=days_list_ru[day_num],
            callback_data=with_owner("weekday_" + day_name, owner_id),
        )
        for day_num, day_name in enumerate(days_list)
    ]
    if day is not None:
        buttons.append(
            InlineKeyboardButton(
                text=texts.MORE_DETAILS,
                callback_data=with_owner(f"animedayc_{day}", owner_id),
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=chunk_buttons(buttons, ROW_LEN_WEEK_BUTTONS))


def get_keyboard_animes(titles_day: list[dict], day: str, owner_id: Optional[int] = None):
    buttons = [
        InlineKeyboardButton(
            text=f'{title_num} {title["title"][:LETTERS_IN_TITLE_BTN]}..',
            callback_data=with_owner("anime_" + day + "_" + str(title_num), owner_id),
        )
        for title_num, title in enumerate(titles_day)
    ]
    buttons.append(
        InlineKeyboardButton(
            text=texts.BACK,
            callback_data=with_owner(f"back_{day}", owner_id),
        )
    )
    return InlineKeyboardMarkup(inline_keyboard=chunk_buttons(buttons, ROW_LEN_TITLES_BUTTONS))


def get_keyboard_back(weekday: str, owner_id: Optional[int] = None):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.BACK,
                    callback_data=with_owner("back_" + weekday, owner_id),
                )
            ]
        ]
    )


def get_keyboard_close_detail(menu_message_id: int, owner_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.BACK,
                    callback_data=f"photoback_{menu_message_id}_{owner_id}",
                )
            ]
        ]
    )
