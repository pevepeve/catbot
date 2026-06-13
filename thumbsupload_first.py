import asyncio
import logging
import os

from aiogram import Bot
from aiogram.types import FSInputFile

from config import get_settings
from infrastructure.db import SessionLocal, init_db
from models.orm import AnimeThumbnail


settings = get_settings()
init_db()

logformat = (
    u"%(filename)s [ LINE:%(lineno)+3s ]#%(levelname)+8s [%(asctime)s]  %(message)s"
)
logging.basicConfig(format=logformat, level=logging.DEBUG)

bot = Bot(token=settings.api_token)
MEDIA_FOLDER = "./media"


async def upload_media_files(method):
    folder_path = os.path.join(MEDIA_FOLDER)
    for filename in os.listdir(folder_path):
        if filename.startswith(".") or filename.startswith("nekochan"):
            continue

        session = SessionLocal()
        try:
            exists = (
                session.query(AnimeThumbnail.filename).filter_by(filename=filename).first()
                is not None
            )
        finally:
            session.close()

        if exists:
            logging.info(f"File {filename} is already in the database")
            continue

        logging.info(f"Started processing {filename}")
        try:
            upload = FSInputFile(os.path.join(folder_path, filename), filename=filename)
            message = await method(settings.admin_id, upload, disable_notification=True)
            file_id = message.photo[-1].file_id

            session = SessionLocal()
            try:
                session.add(AnimeThumbnail(file_id=file_id, filename=filename))
                session.commit()
            finally:
                session.close()

            logging.info(
                "Successfully uploaded and saved to DB file %s with id %s",
                filename,
                file_id,
            )
        except Exception as error:
            logging.error("Couldn't upload %s. Error is %s", filename, error)


loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
wait_tasks = asyncio.wait([loop.create_task(upload_media_files(bot.send_photo))])
loop.run_until_complete(wait_tasks)
loop.close()
