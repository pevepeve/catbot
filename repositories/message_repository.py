from sqlalchemy import asc, func, select
from typing import Optional

from config import get_settings
from infrastructure.db import SessionLocal
from models.orm import SavedMessage


class MessageRepository:
    def __init__(self, session_factory=SessionLocal, max_saved_messages: Optional[int] = None):
        self.session_factory = session_factory
        settings = get_settings()
        self.max_saved_messages = max_saved_messages or settings.last_saved_messages

    def save_message(self, message: str, message_date, chat_id: int) -> None:
        session = self.session_factory()
        try:
            count_saved = session.execute(
                select(func.count()).select_from(SavedMessage).where(SavedMessage.chatid == chat_id)
            ).scalar_one()

            if int(count_saved) > self.max_saved_messages:
                statement = (
                    select(SavedMessage)
                    .where(SavedMessage.chatid == chat_id)
                    .order_by(asc(SavedMessage.id))
                    .limit(1)
                )
                first_message = session.execute(statement).scalar_one()
                session.delete(first_message)

            session.add(SavedMessage(text=message, date=message_date, chatid=chat_id))
            session.commit()
        finally:
            session.close()

    def get_messages(self, chat_id: int) -> list[str]:
        session = self.session_factory()
        try:
            statement = select(SavedMessage.text).where(SavedMessage.chatid == chat_id)
            return [row[0] for row in session.execute(statement)]
        finally:
            session.close()
