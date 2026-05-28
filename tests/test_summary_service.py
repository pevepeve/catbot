from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.orm import Base
from repositories.message_repository import ChatMessageRecord, MessageRepository
from services.summary_service import SummaryService


def test_prepare_messages_filters_noise_and_formats_speakers():
    messages = [
        ChatMessageRecord(
            chat_id=1,
            chat_name="Test Chat",
            chat_username="testchat",
            chat_type="group",
            message_id=1,
            user_id=1,
            user_name="alice",
            reply_to_message_id=None,
            text="/animes",
            created_at="2026-05-28T10:00:00+03:00",
            content_type="text",
        ),
        ChatMessageRecord(
            chat_id=1,
            chat_name="Test Chat",
            chat_username="testchat",
            chat_type="group",
            message_id=2,
            user_id=2,
            user_name="bob",
            reply_to_message_id=None,
            text="   обсудим   релиз  сегодня   ",
            created_at="2026-05-28T10:05:00+03:00",
            content_type="text",
        ),
        ChatMessageRecord(
            chat_id=1,
            chat_name="Test Chat",
            chat_username="testchat",
            chat_type="group",
            message_id=3,
            user_id=3,
            user_name="carol",
            reply_to_message_id=None,
            text="...",
            created_at="2026-05-28T10:06:00+03:00",
            content_type="text",
        ),
    ]

    prepared = SummaryService.prepare_messages(messages)

    assert prepared == ["[10:05] bob: обсудим релиз сегодня"]


def test_message_repository_keeps_last_messages_per_chat():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    repository = MessageRepository(session_factory=session_factory, max_saved_messages=2)

    repository.save_message(
        "first",
        "2026-05-28T10:00:00+03:00",
        1,
        chat_name="Chat One",
        chat_username="chatone",
        chat_type="group",
        message_id=1,
        user_name="a",
    )
    repository.save_message(
        "second",
        "2026-05-28T10:01:00+03:00",
        1,
        chat_name="Chat One",
        chat_username="chatone",
        chat_type="group",
        message_id=2,
        user_name="b",
    )
    repository.save_message(
        "third",
        "2026-05-28T10:02:00+03:00",
        1,
        chat_name="Chat One",
        chat_username="chatone",
        chat_type="group",
        message_id=3,
        user_name="c",
    )

    messages = repository.get_messages(1)

    assert [message.message_id for message in messages] == [2, 3]
    assert [message.text for message in messages] == ["second", "third"]
    assert [message.chat_name for message in messages] == ["Chat One", "Chat One"]
    assert [message.chat_type for message in messages] == ["group", "group"]
