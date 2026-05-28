import os

os.environ.setdefault("DB_FILENAME", ":memory:")

from handlers.catbot_user import split_callback_owner, split_photo_back_payload
from ui.keyboards import (
    get_keyboard_animes,
    get_keyboard_back,
    get_keyboard_close_detail,
    get_keyboard_days,
)


def flatten_callback_data(markup):
    return [button.callback_data for row in markup.inline_keyboard for button in row]


def test_keyboards_include_owner_id():
    owner_id = 777

    day_callbacks = flatten_callback_data(
        get_keyboard_days(["Monday"], ["mon"], "Monday", owner_id=owner_id)
    )
    anime_callbacks = flatten_callback_data(
        get_keyboard_animes([{"title": "Show A"}], "Monday", owner_id=owner_id)
    )
    back_callbacks = flatten_callback_data(get_keyboard_back("Monday", owner_id=owner_id))
    close_callbacks = flatten_callback_data(get_keyboard_close_detail(123, owner_id=owner_id))

    assert day_callbacks == ["weekday_Monday_777", "animedayc_Monday_777"]
    assert anime_callbacks == ["anime_Monday_0_777", "back_Monday_777"]
    assert back_callbacks == ["back_Monday_777"]
    assert close_callbacks == ["photoback_123_777"]


def test_split_callback_owner_supports_owned_and_legacy_buttons():
    assert split_callback_owner("anime_Monday_0_777") == ("anime_Monday_0", 777)
    assert split_callback_owner("back_Monday") == ("back_Monday", None)


def test_split_photo_back_payload():
    assert split_photo_back_payload("photoback_123_777") == (123, 777)
    assert split_photo_back_payload("photoback_bad_777") is None
