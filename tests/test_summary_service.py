import asyncio
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.orm import Base
from repositories.message_repository import ChatMessageRecord, MessageRepository
from services.summary_service import NOTABLE_TITLE, TOPICS_TITLE, SummaryService


class FakeChatHistoryService:
    def __init__(self, messages):
        self.messages = messages

    async def get_messages(self, chat_id: int):
        return self.messages


class FakeDeepSeekResponse:
    def __init__(self, content: str):
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": self.content}}]}


class FakeDeepSeekSession:
    def __init__(self, content: str):
        self.content = content
        self.last_request = None

    def post(self, url, headers=None, json=None, timeout=None):
        self.last_request = {
            "url": url,
            "headers": headers,
            "json": json,
            "timeout": timeout,
        }
        return FakeDeepSeekResponse(self.content)


class FailingDeepSeekSession:
    def post(self, url, headers=None, json=None, timeout=None):
        raise RuntimeError("deepseek unavailable")


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

    assert f"{TOPICS_TITLE}:" in summary
    assert f"{NOTABLE_TITLE}:" in summary
    assert "\u0412\u043e\u043f\u0440\u043e\u0441\u044b:" not in summary
    assert "\u041e\u0442\u0432\u0435\u0442\u044b / \u0442\u0440\u0435\u0434\u044b:" not in summary
    assert "\u041e\u0442\u043a\u0440\u044b\u0442\u043e:" not in summary
    assert "[10:02] bob: Yes, deploy after config fix" in summary


def test_deepseek_summary_is_used_when_configured():
    messages = [
        build_message(1, "alice", "Need release plan for deploy today?", "2026-05-28T10:00:00+03:00"),
        build_message(2, "bob", "Yes, deploy after config fix", "2026-05-28T10:02:00+03:00"),
    ]
    session = FakeDeepSeekSession("Темы:\n- релиз\n\nВажное:\n- обсудили выкладку")
    service = SummaryService(
        FakeChatHistoryService(messages),
        backend="deepseek",
        deepseek_api_key="secret",
        deepseek_model="deepseek-chat",
        deepseek_base_url="https://api.deepseek.com",
        requests_session=session,
    )

    summary = asyncio.run(service.summarize_recent(1))

    assert summary == "Темы:\n- релиз\n\nВажное:\n- обсудили выкладку"
    assert session.last_request["url"] == "https://api.deepseek.com/chat/completions"
    assert session.last_request["json"]["model"] == "deepseek-chat"


def test_deepseek_missing_key_falls_back_to_local():
    messages = [
        build_message(1, "alice", "Need release plan for deploy today?", "2026-05-28T10:00:00+03:00"),
        build_message(2, "bob", "Yes, deploy after config fix", "2026-05-28T10:02:00+03:00"),
    ]
    service = SummaryService(
        FakeChatHistoryService(messages),
        backend="deepseek",
        deepseek_api_key=None,
        requests_session=FakeDeepSeekSession("should not be used"),
    )

    summary = asyncio.run(service.summarize_recent(1))

    assert f"{TOPICS_TITLE}:" in summary
    assert f"{NOTABLE_TITLE}:" in summary


def test_deepseek_failure_falls_back_to_local():
    messages = [
        build_message(1, "alice", "Need release plan for deploy today?", "2026-05-28T10:00:00+03:00"),
        build_message(2, "bob", "Yes, deploy after config fix", "2026-05-28T10:02:00+03:00"),
    ]
    service = SummaryService(
        FakeChatHistoryService(messages),
        backend="deepseek",
        deepseek_api_key="secret",
        deepseek_model="deepseek-chat",
        deepseek_base_url="https://api.deepseek.com",
        requests_session=FailingDeepSeekSession(),
    )

    summary = asyncio.run(service.summarize_recent(1))

    assert f"{TOPICS_TITLE}:" in summary
    assert f"{NOTABLE_TITLE}:" in summary


def test_topic_extraction_uses_external_stopwords():
    messages = [
        build_message(
            1,
            "alice",
            "\u042d\u0442\u043e \u0442\u0430\u043a\u043e\u0439 "
            "\u043a\u0440\u0438\u043f\u0442\u043e\u0434\u043e\u043b\u043b\u0430\u0440, "
            "\u043f\u043e\u0447\u0442\u0438 \u043a\u0430\u043a "
            "\u0441\u0442\u0435\u0439\u0431\u043b\u043a\u043e\u0438\u043d",
            "2026-05-28T10:00:00+03:00",
        ),
        build_message(
            2,
            "bob",
            "\u041a\u0440\u0438\u043f\u0442\u043e\u0434\u043e\u043b\u043b\u0430\u0440 "
            "\u0438 \u043a\u0440\u0438\u043f\u0442\u0430 \u0441\u043d\u043e\u0432\u0430 "
            "\u043e\u0431\u0441\u0443\u0436\u0434\u0430\u044e\u0442\u0441\u044f",
            "2026-05-28T10:02:00+03:00",
        ),
        build_message(
            3,
            "carol",
            "\u0422\u0430\u043a\u043e\u0439 \u043f\u043e\u0434\u0445\u043e\u0434 "
            "\u043a \u043a\u0440\u0438\u043f\u0442\u0435 \u0441\u043f\u043e\u0440\u043d\u044b\u0439",
            "2026-05-28T10:03:00+03:00",
        ),
    ]

    prepared = SummaryService.prepare_messages(messages)
    topics = SummaryService.extract_topics(prepared)

    assert "\u0442\u0430\u043a\u043e\u0439" not in topics
    assert "\u0431\u044b\u0442\u044c" not in topics
    assert "\u043a\u0440\u0438\u043f\u0442\u0430" in topics
    assert "\u043a\u0440\u0438\u043f\u0442\u043e\u0434\u043e\u043b\u043b\u0430\u0440" not in topics


def test_extract_notable_points_skips_near_duplicates():
    messages = [
        build_message(1, "alice", "Need release plan for deploy tonight", "2026-05-28T10:00:00+03:00"),
        build_message(2, "bob", "Need release plan for deploy tonight ASAP", "2026-05-28T10:01:00+03:00"),
        build_message(3, "carol", "Config fix is ready for production", "2026-05-28T10:02:00+03:00"),
    ]

    prepared = SummaryService.prepare_messages(messages)
    notable_points = SummaryService.extract_notable_points(prepared)

    assert len(notable_points) == 2
    assert any("Config fix is ready for production" in point for point in notable_points)


def test_extract_topics_clusters_related_terms():
    messages = [
        build_message(
            1,
            "alice",
            "\u041e\u043f\u0435\u043d\u0441\u043e\u0440\u0441 "
            "\u0441\u0435\u0442\u044c \u0434\u043b\u044f "
            "\u043a\u0440\u0438\u043f\u0442\u044b \u0438 "
            "\u043a\u0440\u0438\u043f\u0442\u043e\u0434\u043e\u043b\u043b\u0430\u0440\u0430",
            "2026-05-28T10:00:00+03:00",
        ),
        build_message(
            2,
            "bob",
            "\u041a\u0440\u0438\u043f\u0442\u0430 \u0438 "
            "\u043a\u0440\u0438\u043f\u0442\u043e\u0434\u043e\u043b\u043b\u0430\u0440 "
            "\u0432 \u044d\u0442\u043e\u0439 \u0441\u0435\u0442\u0438",
            "2026-05-28T10:01:00+03:00",
        ),
        build_message(
            3,
            "carol",
            "\u041c\u043e\u043d\u0435\u0442\u0430 "
            "\u043a\u0440\u0438\u043f\u0442\u0430 \u0438 "
            "\u0441\u0435\u0442\u044c \u0441\u043d\u043e\u0432\u0430 "
            "\u043e\u0431\u0441\u0443\u0436\u0434\u0430\u044e\u0442\u0441\u044f",
            "2026-05-28T10:02:00+03:00",
        ),
    ]

    prepared = SummaryService.prepare_messages(messages)
    topics = SummaryService.extract_topics(prepared)

    assert "\u043e\u043f\u0435\u043d\u0441\u043e\u0440\u0441" in topics
    assert "\u043a\u0440\u0438\u043f\u0442\u0430" in topics
    assert "\u0441\u0435\u0442\u044c" in topics
    assert "\u043a\u0440\u0438\u043f\u0442\u043e\u0434\u043e\u043b\u043b\u0430\u0440" not in topics
    assert "\u043c\u043e\u043d\u0435\u0442\u0430" not in topics


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
