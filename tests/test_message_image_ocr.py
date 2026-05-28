from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.orm import Base, MessageImageOCR
from repositories.message_image_ocr_repository import (
    MessageImageOCRRecord,
    MessageImageOCRRepository,
)
from services.message_image_ocr_service import MessageImageOCRService
from services.ocr_service import OCRResult


class FakeOCRService:
    @staticmethod
    def normalize_text(text: str) -> str:
        return " ".join(text.lower().split())


def test_build_message_link_for_public_and_private_chats():
    service = MessageImageOCRService(MessageImageOCRRepository(session_factory=None), FakeOCRService())

    assert service.build_message_link(123, "publicchat", 45) == "https://t.me/publicchat/45"
    assert service.build_message_link(-1009876543210, "", 12) == "https://t.me/c/9876543210/12"
    assert service.build_message_link(-12345, "", 9) == ""


def test_build_search_text_ignores_command_caption_and_uses_ocr():
    service = MessageImageOCRService(MessageImageOCRRepository(session_factory=None), FakeOCRService())

    search_text = service.build_search_text(
        "/addneko",
        OCRResult(raw_text="MEME TEXT", normalized_text="meme text"),
    )

    assert search_text == "meme text"


def test_ocr_repository_keeps_last_records_per_chat():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    repository = MessageImageOCRRepository(session_factory=session_factory, max_saved_messages=2)

    repository.save_record(
        MessageImageOCRRecord(
            chat_id=1,
            chat_name="Chat",
            chat_username="chat",
            chat_type="group",
            message_id=1,
            message_link="",
            user_id=1,
            user_name="a",
            message_date="2026-05-28T10:00:00+03:00",
            caption_text="",
            ocr_raw_text="first",
            search_text="first",
            file_id="file-1",
            file_unique_id="uniq-1",
        )
    )
    repository.save_record(
        MessageImageOCRRecord(
            chat_id=1,
            chat_name="Chat",
            chat_username="chat",
            chat_type="group",
            message_id=2,
            message_link="",
            user_id=2,
            user_name="b",
            message_date="2026-05-28T10:01:00+03:00",
            caption_text="",
            ocr_raw_text="second",
            search_text="second",
            file_id="file-2",
            file_unique_id="uniq-2",
        )
    )
    repository.save_record(
        MessageImageOCRRecord(
            chat_id=1,
            chat_name="Chat",
            chat_username="chat",
            chat_type="group",
            message_id=3,
            message_link="",
            user_id=3,
            user_name="c",
            message_date="2026-05-28T10:02:00+03:00",
            caption_text="",
            ocr_raw_text="third",
            search_text="third",
            file_id="file-3",
            file_unique_id="uniq-3",
        )
    )

    session = session_factory()
    try:
        rows = session.query(MessageImageOCR).order_by(MessageImageOCR.id).all()
        assert [row.message_id for row in rows] == [2, 3]
        assert [row.search_text for row in rows] == ["second", "third"]
    finally:
        session.close()
