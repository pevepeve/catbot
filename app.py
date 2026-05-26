import logging
from logging import StreamHandler
import sys

from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode

from config import get_settings
from handlers import catbot_admin, catbot_user
from infrastructure import init_db


def main():
    settings = get_settings()
    init_db()

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        filename="logs/bot.log",
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting bot")

    bot = Bot(token=settings.api_token, parse_mode=ParseMode.HTML)
    storage = MemoryStorage()
    dispatcher = Dispatcher(bot, storage=storage)
    dispatcher.middleware.setup(LoggingMiddleware())

    catbot_user.register_handlers_user(dispatcher)
    catbot_admin.register_handlers_admin(dispatcher, admin_id=settings.admin_id)

    logger.setLevel(logging.DEBUG)
    handler = StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s, [%(levelname)s] %(message)s"))
    logger.addHandler(handler)

    executor.start_polling(dispatcher, skip_updates=True)


if __name__ == "__main__":
    main()
