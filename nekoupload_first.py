import os
import asyncio
import logging
from aiogram import Bot
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from dotenv import load_dotenv

load_dotenv()


NEKODB_FILENAME = os.getenv('DB_FILENAME')
API_TOKEN = os.getenv('API_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')

from db_neko import Base, NekoIds

logformat = u'%(filename)s [ LINE:%(lineno)+3s ]#%(levelname)+8s [%(asctime)s]  %(message)s'
logging.basicConfig(format=logformat,
                    level=logging.DEBUG)

engine = create_engine(f'sqlite:///{NEKODB_FILENAME}')

if not os.path.isfile(f'./{NEKODB_FILENAME}'):
    Base.metadata.create_all(engine)

session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

bot = Bot(token=API_TOKEN)


MEDIA_FOLDER = './media'


async def uploadMediaFiles(folder, method):
    folder_path = os.path.join(MEDIA_FOLDER, folder)
    for filename in os.listdir(folder_path):
        if filename.startswith('.'):
            continue
        exists = Session.query(NekoIds.filename).filter_by(
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
                newItem = NekoIds(file_id=file_id, filename=filename)
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
    loop.create_task(uploadMediaFiles('nekochans', bot.send_photo)),
]

wait_tasks = asyncio.wait(tasks)

loop.run_until_complete(wait_tasks)
loop.close()
Session.remove()
