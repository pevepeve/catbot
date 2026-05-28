from dataclasses import dataclass
from sqlalchemy import asc, func, select
from typing import Optional

from config import get_settings
from infrastructure.db import SessionLocal
from models.orm import SavedMessage


@dataclass(frozen=True)
class ChatMessageRecord:
    chat_id: int
    chat_name: str
    chat_username: str
    chat_type: str
    message_id: int | None
    user_id: int | None
    user_name: str
    reply_to_message_id: int | None
    text: str
    created_at: str
    content_type: str


class MessageRepository:
    def __init__(self, session_factory=SessionLocal, max_saved_messages: Optional[int] = None):
        self.session_factory = session_factory
        settings = get_settings()
        self.max_saved_messages = max_saved_messages or settings.last_saved_messages

    def save_message(
        self,
        text: str,
        message_date,
        chat_id: int,
        chat_name: str = "",
        chat_username: str = "",
        chat_type: str = "",
        message_id: int | None = None,
        user_id: int | None = None,
        user_name: str = "",
        reply_to_message_id: int | None = None,
        content_type: str = "text",
    ) -> None:
        session = self.session_factory()
        try:
            count_saved = session.execute(
                select(func.count()).select_from(SavedMessage).where(SavedMessage.chatid == chat_id)
            ).scalar_one()

            if int(count_saved) >= self.max_saved_messages:
                statement = (
                    select(SavedMessage)
                    .where(SavedMessage.chatid == chat_id)
                    .order_by(asc(SavedMessage.id))
                    .limit(1)
                )
                first_message = session.execute(statement).scalar_one()
                session.delete(first_message)

            session.add(
                SavedMessage(
                    chatid=chat_id,
                    chat_name=chat_name,
                    chat_username=chat_username,
                    chat_type=chat_type,
                    message_id=message_id,
                    user_id=user_id,
                    user_name=user_name,
                    reply_to_message_id=reply_to_message_id,
                    text=text,
                    date=str(message_date),
                    content_type=content_type,
                )
            )
            session.commit()
        finally:
            session.close()

    def get_messages(self, chat_id: int) -> list[ChatMessageRecord]:
        session = self.session_factory()
        try:
            statement = (
                select(SavedMessage)
                .where(SavedMessage.chatid == chat_id)
                .order_by(asc(SavedMessage.id))
            )
            return [
                ChatMessageRecord(
                    chat_id=row.chatid,
                    chat_name=row.chat_name or "",
                    chat_username=row.chat_username or "",
                    chat_type=row.chat_type or "",
                    message_id=row.message_id,
                    user_id=row.user_id,
                    user_name=row.user_name or "Unknown",
                    reply_to_message_id=row.reply_to_message_id,
                    text=row.text or "",
                    created_at=row.date or "",
                    content_type=row.content_type or "text",
                )
                for row in session.execute(statement).scalars()
            ]
        finally:
            session.close()
