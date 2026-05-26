from aiogram import types
from typing import Optional


ROW_LEN_WEEK_BUTTONS = 4
ROW_LEN_TITLES_BUTTONS = 2
LETTERS_IN_TITLE_BTN = 7


def get_keyboard_days(days_list: list[str], days_list_ru: list[str], day: Optional[str] = None):
    buttons = [
        types.InlineKeyboardButton(
            text=days_list_ru[day_num],
            callback_data="weekday_" + day_name,
        )
        for day_num, day_name in enumerate(days_list)
    ]
    if day is not None:
        buttons.append(
            types.InlineKeyboardButton(
                text="Подробнее",
                callback_data=f"animedayc_{day}",
            )
        )
    keyboard = types.InlineKeyboardMarkup(row_width=ROW_LEN_WEEK_BUTTONS)
    keyboard.add(*buttons)
    return keyboard


def get_keyboard_animes(titles_day: list[dict], day: str):
    buttons = [
        types.InlineKeyboardButton(
            text=f'{title_num} {title["title"][:LETTERS_IN_TITLE_BTN]}..',
            callback_data="anime_" + day + "_" + str(title_num),
        )
        for title_num, title in enumerate(titles_day)
    ]
    buttons.append(
        types.InlineKeyboardButton(
            text="Назад",
            callback_data=f"back_{day}",
        )
    )
    keyboard = types.InlineKeyboardMarkup(row_width=ROW_LEN_TITLES_BUTTONS)
    keyboard.add(*buttons)
    return keyboard


def get_keyboard_back(weekday: str):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton(
            text="Назад",
            callback_data="back_" + weekday,
        )
    )
    return keyboard
