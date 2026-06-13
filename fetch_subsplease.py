import asyncio

from aiogram import Bot

from config import get_settings
from infrastructure import TelegramMediaStore, init_db
from infrastructure.subsplease_client import SubspleaseClient
from repositories.anime_repository import AnimeRepository
from services.anime_service import AnimeService


async def get_schedule():
    settings = get_settings()
    init_db()

    bot = Bot(token=settings.api_token)
    try:
        media_store = TelegramMediaStore(bot, settings.admin_id)
        await AnimeService(AnimeRepository(), SubspleaseClient()).refresh_schedule(
            media_store,
            force=True,
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(get_schedule())

