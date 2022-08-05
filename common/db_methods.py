import io
import logging
import os
from random import randrange

from aiogram import Bot
from sqlalchemy import create_engine, func, select, asc
from sqlalchemy.orm import scoped_session, sessionmaker


from db_neko import AnimeThumbsIds, Base, NekoIds, SavedMessages

from dotenv import load_dotenv

load_dotenv()

DB_FILENAME = os.getenv('DB_FILENAME')
API_TOKEN = os.getenv('API_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')
LAST_SAVED_MESSAGES = 20

bot = Bot(token=API_TOKEN)

engine = create_engine(f'sqlite:///{DB_FILENAME}')
session_factory = sessionmaker(
    bind=engine, expire_on_commit=False)
Session = scoped_session(session_factory)

if not os.path.isfile(f'./{DB_FILENAME}'):
    Base.metadata.create_all(engine)

########################################
#             Functions
########################################


async def photo_upload(file_io: io.BytesIO, md5: str):
    exists = Session.execute(select(NekoIds.filename).where(
        NekoIds.filename == md5+'.jpg')).scalars().first() is not None
    if exists:
        logging.info(
            f'File {md5} is already in the database')
        raise ValueError('Already exists')
    logging.info(f'Started processing {md5}')
    try:
        with file_io as file:
            msg = await bot.send_photo(ADMIN_ID, file, disable_notification=True)
            file_id = msg.photo[-1].file_id
            session = Session()
            newItem = NekoIds(file_id=file_id, filename=md5+'.jpg')
            try:
                session.add(newItem)
                session.commit()
            except Exception as e:
                logging.error(
                    'Couldn\'t upload {}. Error is {}'.format(md5, e))
            else:
                logging.info(
                    f'Successfully uploaded and saved to DB'
                    f' file {md5} with id {file_id}')
            finally:
                session.close()
    except Exception as e:
        logging.error(
            'Couldn\'t upload {}. Error is {}'.format(md5, e))


async def get_thumb_id(filename):
    thumb = Session.execute(select(AnimeThumbsIds.file_id).where(
        AnimeThumbsIds.filename == filename))
    return thumb.scalar_one()


async def get_random_nekochan():
    count_nekos = Session.execute(func.count(NekoIds.filename))
    random_neko = randrange(1, count_nekos.scalar_one())
    nekoid = Session.execute(select(NekoIds.file_id).where(
        NekoIds.id == random_neko))
    return nekoid.scalar_one()


async def save_to_db(message, date):
    try:
        count_saved = Session.execute(func.count(SavedMessages.id)).scalar_one()
        if int(count_saved) > LAST_SAVED_MESSAGES:
            statement = select(SavedMessages).order_by(asc(SavedMessages.id)).limit(1)
            first = Session.execute(statement).scalar_one()
            Session.delete(first)
        newItem = SavedMessages(text=message, date=date)
        Session.add(newItem)
        Session.commit()
    finally:
        Session.close()
