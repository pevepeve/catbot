from dataclasses import dataclass
from typing import Optional

from sqlalchemy import asc, func, select

from config import get_settings
from infrastructure.db import SessionLocal
from models.orm import MessageImageOCR


@dataclass(frozen=True)
class MessageImageOCRRecord:
    chat_id: int
    chat_name: str
    chat_username: str
    chat_type: str
    message_id: int
    message_link: str
    user_id: int | None
    user_name: str
    message_date: str
    caption_text: str
    ocr_raw_text: str
    search_text: str
    file_id: str
    file_unique_id: str


class MessageImageOCRRepository:
    def __init__(self, session_factory=SessionLocal, max_saved_messages: Optional[int] = None):
        self.session_factory = session_factory
        settings = get_settings()
        self.max_saved_messages = max_saved_messages or settings.last_saved_image_messages

    def save_record(self, record: MessageImageOCRRecord) -> None:
        session = self.session_factory()
        try:
            statement = select(MessageImageOCR).where(
                MessageImageOCR.chat_id == record.chat_id,
                MessageImageOCR.message_id == record.message_id,
            )
            existing = session.execute(statement).scalar_one_or_none()
            if existing is not None:
                existing.chat_name = record.chat_name
                existing.chat_username = record.chat_username
                existing.chat_type = record.chat_type
                existing.message_link = record.message_link
                existing.user_id = record.user_id
                existing.user_name = record.user_name
                existing.message_date = record.message_date
                existing.caption_text = record.caption_text
                existing.ocr_raw_text = record.ocr_raw_text
                existing.search_text = record.search_text
                existing.file_id = record.file_id
                existing.file_unique_id = record.file_unique_id
                session.commit()
                return

            count_saved = session.execute(
                select(func.count()).select_from(MessageImageOCR).where(
                    MessageImageOCR.chat_id == record.chat_id
                )
            ).scalar_one()

            if int(count_saved) >= self.max_saved_messages:
                oldest_statement = (
                    select(MessageImageOCR)
                    .where(MessageImageOCR.chat_id == record.chat_id)
                    .order_by(asc(MessageImageOCR.id))
                    .limit(1)
                )
                oldest = session.execute(oldest_statement).scalar_one()
                session.delete(oldest)

            session.add(
                MessageImageOCR(
                    chat_id=record.chat_id,
                    chat_name=record.chat_name,
                    chat_username=record.chat_username,
                    chat_type=record.chat_type,
                    message_id=record.message_id,
                    message_link=record.message_link,
                    user_id=record.user_id,
                    user_name=record.user_name,
                    message_date=record.message_date,
                    caption_text=record.caption_text,
                    ocr_raw_text=record.ocr_raw_text,
                    search_text=record.search_text,
                    file_id=record.file_id,
                    file_unique_id=record.file_unique_id,
                )
            )
            session.commit()
        finally:
            session.close()
