import asyncio
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.orm import Base
from repositories.message_repository import ChatMessageRecord, MessageRepository
from services.summary_service import SummaryService


class FakeChatHistoryService:
    def __init__(self, messages):
        self.messages = messages

    async def get_messages(self, chat_id: int):
        return self.messages


def build_message(
    message_id: int,
    user_name: str,
    text: str,
    created_at: str,
    reply_to_message_id: int | None = None,
):
    return ChatMessageRecord(
        chat_id=1,
        chat_name="Test Chat",
        chat_username="testchat",
        chat_type="group",
        message_id=message_id,
        user_id=message_id,
        user_name=user_name,
        reply_to_message_id=reply_to_message_id,
        text=text,
        created_at=created_at,
        content_type="text",
    )


def test_prepare_messages_filters_noise_and_extracts_metadata():
    messages = [
        build_message(1, "alice", "/animes", "2026-05-28T10:00:00+03:00"),
        build_message(2, "bob", "  release  tonight?  ", "2026-05-28T10:05:00+03:00"),
        build_message(3, "carol", "...", "2026-05-28T10:06:00+03:00"),
    ]

    prepared = SummaryService.prepare_messages(messages)

    assert len(prepared) == 1
    assert prepared[0].speaker == "bob"
    assert prepared[0].timestamp == "10:05"
    assert prepared[0].normalized_text == "release tonight?"
    assert prepared[0].is_question is True


def test_structured_summary_keeps_only_topics_and_notable():
    messages = [
        build_message(1, "alice", "Need release plan for deploy today?", "2026-05-28T10:00:00+03:00"),
        build_message(2, "bob", "Yes, deploy after config fix", "2026-05-28T10:02:00+03:00", reply_to_message_id=1),
        build_message(3, "carol", "DeepSeek later, local summary now", "2026-05-28T10:03:00+03:00"),
    ]
    service = SummaryService(FakeChatHistoryService(messages))

    summary = asyncio.run(service.summarize_recent(1))

    assert "Темы:" in summary
    assert "Важное:" in summary
    assert "Вопросы:" not in summary
    assert "Ответы / треды:" not in summary
    assert "Открыто:" not in summary
    assert "[10:02] bob: Yes, deploy after config fix" in summary


def test_topic_extraction_skips_generic_words():
    messages = [
        build_message(1, "alice", "Это такой криптодоллар, почти как стейблкоин", "2026-05-28T10:00:00+03:00"),
        build_message(2, "bob", "Криптодоллар и крипта снова обсуждаются", "2026-05-28T10:02:00+03:00"),
        build_message(3, "carol", "Такой подход к крипте спорный", "2026-05-28T10:03:00+03:00"),
    ]

    prepared = SummaryService.prepare_messages(messages)
    topics = SummaryService.extract_topics(prepared)

    assert "такой" not in topics
    assert "быть" not in topics
    assert "криптодоллар" in topics


def test_filter_recent_messages_excludes_stale_history():
    messages = [
        build_message(1, "alice", "old deploy note", "2026-05-20T10:00:00+00:00"),
        build_message(2, "bob", "fresh release plan?", "2026-05-27T12:00:00+00:00"),
    ]

    filtered = SummaryService.filter_recent_messages(
        messages,
        lookback_days=3,
        now=datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc),
    )

    assert [message.message_id for message in filtered] == [2]


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
