import os
import asyncio
import logging
from aiogram import Bot
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from data.config.config import API_TOKEN, ADMIN_ID, ANIMETHUMBDB_FILENAME


from db_neko import Base, AnimeThumbsIds

logformat = u'%(filename)s [ LINE:%(lineno)+3s ]#%(levelname)+8s [%(asctime)s]  %(message)s'
logging.basicConfig(format=logformat,
                    level=logging.DEBUG)

engine = create_engine(f'sqlite:///{ANIMETHUMBDB_FILENAME}')

if not os.path.isfile(f'./{ANIMETHUMBDB_FILENAME}'):
    Base.metadata.create_all(engine)

session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

bot = Bot(token=API_TOKEN)


MEDIA_FOLDER = './media'


async def uploadMediaFiles(method):
    folder_path = os.path.join(MEDIA_FOLDER)
    for filename in os.listdir(folder_path):
        if filename.startswith('.'):
            continue
        if filename.startswith('nekochan'):
            continue
        exists = Session.query(AnimeThumbsIds.filename).filter_by(
            filename=filename).first() is not None
        if exists:
            logging.info(
                f'File {filename} is already in the database')
            continue
        logging.info(f'Started processing {filename}')
        try:
            with open(os.path.join(folder_path, filename), 'rb') as file:
                msg = await method(ADMIN_ID, file, disable_notification=True)
                file_id = msg.photo[-1].file_id
                session = Session()
                newItem = AnimeThumbsIds(file_id=file_id, filename=filename)
                try:
                    session.add(newItem)
                    session.commit()
                except Exception as e:
                    logging.error(
                        'Couldn\'t upload {}. Error is {}'.format(filename, e))
                else:
                    logging.info(
                        f'Successfully uploaded and saved to DB'
                        f' file {filename} with id {file_id}')
                finally:
                    session.close()
        except Exception as e:
            logging.error(
                'Couldn\'t upload {}. Error is {}'.format(filename, e))


loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

tasks = [
    loop.create_task(uploadMediaFiles(bot.send_photo)),
]

wait_tasks = asyncio.wait(tasks)

loop.run_until_complete(wait_tasks)
loop.close()
Session.remove()
