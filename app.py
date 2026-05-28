import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import get_settings
from handlers import catbot_admin, catbot_user
from infrastructure import TelegramMediaStore, init_db
from repositories import AnimeRepository
from services import AnimeService


ANIME_REFRESH_CHECK_INTERVAL_SECONDS = 6 * 60 * 60


async def anime_schedule_refresh_loop(bot: Bot, admin_id: int) -> None:
    anime_service = AnimeService(AnimeRepository())
    media_store = TelegramMediaStore(bot, admin_id)

    while True:
        try:
            result = await anime_service.refresh_schedule(media_store)
            if result.refreshed or result.uploaded_thumbnails:
                logging.info(
                    "Anime schedule sync completed: refreshed=%s uploaded_thumbnails=%s",
                    result.refreshed,
                    result.uploaded_thumbnails,
                )
        except Exception:
            logging.exception("Anime schedule sync failed")

        await asyncio.sleep(ANIME_REFRESH_CHECK_INTERVAL_SECONDS)


async def ocr_backfill_once(bot: Bot) -> None:
    if not catbot_user.ocr_service.is_available:
        return

    processed = await catbot_user.message_image_ocr_service.backfill_pending_images(bot)
    if processed:
        logging.info("OCR backfill completed: processed=%s", processed)


async def main():
    settings = get_settings()
    init_db()

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        stream=sys.stdout,
    )
    if catbot_user.ocr_service.startup_warning:
        logging.warning(catbot_user.ocr_service.startup_warning)

    bot = Bot(
        token=settings.api_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()

    catbot_user.register_handlers_user(dispatcher)
    catbot_admin.register_handlers_admin(dispatcher, admin_id=settings.admin_id)
    refresh_task = asyncio.create_task(
        anime_schedule_refresh_loop(bot, settings.admin_id),
        name="anime-schedule-refresh",
    )
    ocr_backfill_task = asyncio.create_task(
        ocr_backfill_once(bot),
        name="ocr-backfill",
    )
    try:
        await dispatcher.start_polling(bot)
    finally:
        refresh_task.cancel()
        if not ocr_backfill_task.done():
            ocr_backfill_task.cancel()
        await asyncio.gather(refresh_task, ocr_backfill_task, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
