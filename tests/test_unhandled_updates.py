import asyncio
import logging

from aiogram.dispatcher.event.bases import UNHANDLED
from aiogram.types import Message, Update

from handlers.unhandled_updates import (
    UnhandledUpdateLoggerMiddleware,
    get_update_type,
    serialize_update,
)


def test_get_update_type_for_message_update():
    update = Update(
        update_id=123,
        message=Message.model_validate(
            {
                "message_id": 1,
                "date": 0,
                "chat": {"id": 10, "type": "private"},
            }
        ),
    )

    assert get_update_type(update) == "message"


def test_serialize_update_truncates_payload():
    update = Update(
        update_id=123,
        message=Message.model_validate(
            {
                "message_id": 1,
                "date": 0,
                "chat": {"id": 10, "type": "private"},
                "text": "x" * 200,
            }
        ),
    )

    payload = serialize_update(update, max_length=80)

    assert len(payload) == 80
    assert payload.endswith("...")


def test_unhandled_update_logger_middleware_logs_only_unhandled_updates(caplog):
    middleware = UnhandledUpdateLoggerMiddleware()
    update = Update(
        update_id=123,
        message=Message.model_validate(
            {
                "message_id": 1,
                "date": 0,
                "chat": {"id": 10, "type": "private"},
                "text": "hello",
            }
        ),
    )

    async def unhandled_handler(event, data):
        return UNHANDLED

    async def handled_handler(event, data):
        return "ok"

    with caplog.at_level(logging.INFO):
        asyncio.run(middleware(unhandled_handler, update, {}))
        asyncio.run(middleware(handled_handler, update, {}))

    assert "Unhandled update received: id=123 type=message" in caplog.text
    assert caplog.text.count("Unhandled update received") == 1
