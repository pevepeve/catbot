import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import get_settings
from handlers import catbot_admin, catbot_user
from infrastructure import init_db


async def main():
    settings = get_settings()
    init_db()

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        stream=sys.stdout,
    )

    bot = Bot(
        token=settings.api_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()

    catbot_user.register_handlers_user(dispatcher)
    catbot_admin.register_handlers_admin(dispatcher, admin_id=settings.admin_id)

    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
