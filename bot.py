import logging
from logging import StreamHandler
import os 
import sys

from dotenv import load_dotenv
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ParseMode

from handlers import catbot_user, catbot_admin

load_dotenv()

DB_FILENAME = os.getenv('DB_FILENAME')
API_TOKEN = os.getenv('API_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')

engine = create_async_engine(f'sqlite+aiosqlite:///{DB_FILENAME}')
session_factory = sessionmaker(
    bind=engine, expire_on_commit=False, class_=AsyncSession)
Session = scoped_session(session_factory)
logger = logging.getLogger(__name__)

if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG,
                        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
                        filename='logs/bot.log', encoding='utf-8')

    logger.info("Starting bot")

    bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
    storage = MemoryStorage()
    dp = Dispatcher(bot, storage=storage)
    dp.middleware.setup(LoggingMiddleware())

    catbot_user.register_handlers_user(dp, admin_id = int(ADMIN_ID))
    catbot_admin.register_handlers_admin(dp, admin_id = int(ADMIN_ID))
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = StreamHandler(sys.stdout)
    logger.addHandler(handler)
    formatter = logging.Formatter(
        '%(asctime)s, [%(levelname)s] %(message)s'
    )
    handler.setFormatter(formatter)

    executor.start_polling(dp, skip_updates=True)
