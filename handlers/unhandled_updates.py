import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import Dispatcher
from aiogram.dispatcher.event.bases import UNHANDLED
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import TelegramObject, Update
from aiogram.types.update import UpdateTypeLookupError


logger = logging.getLogger(__name__)
MAX_UPDATE_LOG_LENGTH = 4000


def get_update_type(update: Update) -> str:
    try:
        return update.event_type
    except UpdateTypeLookupError:
        return "unknown"


def serialize_update(update: Update, *, max_length: int = MAX_UPDATE_LOG_LENGTH) -> str:
    payload = json.dumps(
        update.model_dump(mode="json", exclude_none=True),
        ensure_ascii=False,
        sort_keys=True,
    )
    if len(payload) <= max_length:
        return payload
    return payload[: max_length - 3] + "..."


class UnhandledUpdateLoggerMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        response = await handler(event, data)

        if response is UNHANDLED and isinstance(event, Update):
            logger.info(
                "Unhandled update received: id=%s type=%s payload=%s",
                event.update_id,
                get_update_type(event),
                serialize_update(event),
            )

        return response


def register_unhandled_update_logger(dispatcher: Dispatcher) -> None:
    dispatcher.update.outer_middleware(UnhandledUpdateLoggerMiddleware())
