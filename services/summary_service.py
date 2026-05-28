from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from config import get_settings
from repositories.message_repository import ChatMessageRecord
from services.chat_history_service import ChatHistoryService

try:
    from pymorphy3 import MorphAnalyzer
except ImportError:  # pragma: no cover - optional dependency in local dev
    MorphAnalyzer = None

try:
    from razdel import tokenize as razdel_tokenize
except ImportError:  # pragma: no cover - optional dependency in local dev
    razdel_tokenize = None


NOISE_MESSAGE_MIN_LEN = 2
MAX_TOPICS = 5
MAX_NOTABLE_POINTS = 4
MAX_QUESTIONS = 4
MAX_REPLY_THREADS = 4
MAX_OPEN_QUESTIONS = 3
QUESTION_WORDS = {
    "как",
    "когда",
    "кто",
    "куда",
    "где",
    "зачем",
    "почему",
    "что",
    "чего",
    "какой",
    "какая",
    "какие",
    "какого",
    "нужно",
    "надо",
}
STOPWORDS = {
    "это",
    "как",
    "так",
    "для",
    "что",
    "или",
    "если",
    "она",
    "они",
    "оно",
    "его",
    "ее",
    "её",
    "мне",
    "тебе",
    "вам",
    "нас",
    "все",
    "всё",
    "тут",
    "там",
    "потом",
    "сейчас",
    "сегодня",
    "завтра",
    "вчера",
    "после",
    "надо",
    "нужно",
    "будет",
    "будут",
    "просто",
    "типа",
    "блин",
    "лол",
    "ага",
    "угу",
    "щас",
    "ещё",
    "еще",
    "очень",
    "вроде",
    "короче",
    "кстати",
    "только",
    "чтобы",
    "пока",
    "потому",
}
LINK_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9_-]+")
CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")


def build_morph_analyzer():
    if MorphAnalyzer is None:
        return None
    return MorphAnalyzer()


MORPH = build_morph_analyzer()


@dataclass(frozen=True)
class PreparedSummaryMessage:
    message_id: int | None
    speaker: str
    timestamp: str
    text: str
    normalized_text: str
    reply_to_message_id: int | None
    lemmas: tuple[str, ...]
    is_question: bool
    is_reply: bool
    has_link: bool
    score: int


class SummaryService:
    def __init__(self, chat_history_service: ChatHistoryService, lookback_days: int | None = None):
        self.chat_history_service = chat_history_service
        settings = get_settings()
        self.lookback_days = (
            settings.summary_lookback_days if lookback_days is None else lookback_days
        )

    async def summarize_recent(self, chat_id: int) -> str:
        messages = await self.chat_history_service.get_messages(chat_id)
        recent_messages = self.filter_recent_messages(messages, self.lookback_days)
        prepared_messages = self.prepare_messages(recent_messages)
        if not prepared_messages:
            return "Недостаточно данных для суммаризации."
        return self.render_structured_summary(prepared_messages)

    @staticmethod
    def normalize_text(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def extract_timestamp(created_at: str) -> str:
        return created_at[11:16] if len(created_at) >= 16 else "??:??"

    @staticmethod
    def parse_created_at(created_at: str) -> datetime | None:
        if not created_at:
            return None
        try:
            parsed = datetime.fromisoformat(created_at)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed

    @classmethod
    def filter_recent_messages(
        cls,
        messages: list[ChatMessageRecord],
        lookback_days: int,
        now: datetime | None = None,
    ) -> list[ChatMessageRecord]:
        current_time = now or datetime.now(timezone.utc)
        threshold = current_time - timedelta(days=lookback_days)
        recent_messages = []
        for message in messages:
            created_at = cls.parse_created_at(message.created_at)
            if created_at is None:
                continue
            if created_at >= threshold:
                recent_messages.append(message)
        return recent_messages

    @staticmethod
    def tokenize_text(text: str) -> list[str]:
        if razdel_tokenize is not None:
            return [token.text for token in razdel_tokenize(text)]
        return TOKEN_RE.findall(text)

    @staticmethod
    def normalize_token(token: str) -> str:
        cleaned_token = token.strip("._-").lower()
        if not cleaned_token:
            return ""
        if MORPH is None or not CYRILLIC_RE.search(cleaned_token):
            return cleaned_token
        return MORPH.parse(cleaned_token)[0].normal_form

    @classmethod
    def is_meaningful_token(cls, token: str) -> bool:
        if len(token) < 3 and not token.isdigit():
            return False
        if token in STOPWORDS:
            return False
        if token.startswith(("http", "www", "@", "#", "/")):
            return False
        return bool(re.search(r"[A-Za-zА-Яа-яЁё0-9]", token))

    @classmethod
    def extract_lemmas(cls, text: str) -> tuple[str, ...]:
        lemmas = []
        for token in cls.tokenize_text(text):
            normalized = cls.normalize_token(token)
            if normalized and cls.is_meaningful_token(normalized):
                lemmas.append(normalized)
        return tuple(lemmas)

    @classmethod
    def should_skip_message(cls, message: ChatMessageRecord) -> bool:
        normalized_text = cls.normalize_text(message.text)
        if not normalized_text:
            return True
        if normalized_text.startswith("/"):
            return True
        if len(normalized_text) < NOISE_MESSAGE_MIN_LEN:
            return True
        if not re.search(r"[\w\u0400-\u04FF]", normalized_text):
            return True
        return False

    @classmethod
    def detect_question(cls, normalized_text: str, lemmas: Iterable[str]) -> bool:
        if "?" in normalized_text:
            return True
        lemma_set = set(lemmas)
        return any(question_word in lemma_set for question_word in QUESTION_WORDS)

    @classmethod
    def score_message(
        cls,
        normalized_text: str,
        lemmas: tuple[str, ...],
        is_question: bool,
        is_reply: bool,
        has_link: bool,
    ) -> int:
        score = min(len(set(lemmas)), 6)
        if 25 <= len(normalized_text) <= 300:
            score += 2
        if is_question:
            score += 2
        if is_reply:
            score += 1
        else:
            score += 2
        if has_link:
            score += 1
        return score

    @classmethod
    def prepare_messages(cls, messages: list[ChatMessageRecord]) -> list[PreparedSummaryMessage]:
        prepared_messages = []
        for message in messages:
            if cls.should_skip_message(message):
                continue

            normalized_text = cls.normalize_text(message.text)
            lemmas = cls.extract_lemmas(normalized_text)
            if not lemmas and not LINK_RE.search(normalized_text) and "?" not in normalized_text:
                continue

            is_question = cls.detect_question(normalized_text, lemmas)
            is_reply = message.reply_to_message_id is not None
            has_link = LINK_RE.search(normalized_text) is not None
            score = cls.score_message(
                normalized_text,
                lemmas,
                is_question,
                is_reply,
                has_link,
            )
            prepared_messages.append(
                PreparedSummaryMessage(
                    message_id=message.message_id,
                    speaker=message.user_name or "Unknown",
                    timestamp=cls.extract_timestamp(message.created_at),
                    text=message.text,
                    normalized_text=normalized_text,
                    reply_to_message_id=message.reply_to_message_id,
                    lemmas=lemmas,
                    is_question=is_question,
                    is_reply=is_reply,
                    has_link=has_link,
                    score=score,
                )
            )
        return prepared_messages

    @staticmethod
    def format_transcript_line(message: PreparedSummaryMessage) -> str:
        return f"[{message.timestamp}] {message.speaker}: {message.normalized_text}"

    @classmethod
    def extract_topics(cls, messages: list[PreparedSummaryMessage]) -> list[str]:
        topic_scores: dict[str, int] = {}
        for message in messages:
            if message.score < 3:
                continue
            for lemma in set(message.lemmas):
                topic_scores[lemma] = topic_scores.get(lemma, 0) + 1

        ranked_topics = sorted(
            topic_scores.items(),
            key=lambda item: (-item[1], -len(item[0]), item[0]),
        )
        return [topic for topic, _ in ranked_topics[:MAX_TOPICS]]

    @classmethod
    def extract_notable_points(cls, messages: list[PreparedSummaryMessage]) -> list[str]:
        ranked_messages = sorted(
            messages,
            key=lambda message: (-message.score, message.timestamp, message.speaker),
        )
        notable_points = []
        seen_texts = set()
        for message in ranked_messages:
            if message.normalized_text in seen_texts:
                continue
            seen_texts.add(message.normalized_text)
            notable_points.append(cls.format_transcript_line(message))
            if len(notable_points) >= MAX_NOTABLE_POINTS:
                break
        return notable_points

    @classmethod
    def extract_questions(cls, messages: list[PreparedSummaryMessage]) -> list[str]:
        questions = [
            cls.format_transcript_line(message)
            for message in messages
            if message.is_question
        ]
        return questions[:MAX_QUESTIONS]

    @classmethod
    def extract_reply_threads(cls, messages: list[PreparedSummaryMessage]) -> list[str]:
        message_by_id = {
            message.message_id: message
            for message in messages
            if message.message_id is not None
        }
        reply_threads = []
        for message in messages:
            if message.reply_to_message_id is None:
                continue
            parent_message = message_by_id.get(message.reply_to_message_id)
            if parent_message is None:
                continue
            reply_threads.append(
                f"[{message.timestamp}] {message.speaker} -> "
                f"{parent_message.speaker}: {message.normalized_text}"
            )
            if len(reply_threads) >= MAX_REPLY_THREADS:
                break
        return reply_threads

    @classmethod
    def extract_open_questions(cls, messages: list[PreparedSummaryMessage]) -> list[str]:
        replied_question_ids = {
            message.reply_to_message_id
            for message in messages
            if message.reply_to_message_id is not None
        }
        open_questions = []
        for message in messages:
            if not message.is_question or message.message_id is None:
                continue
            if message.message_id in replied_question_ids:
                continue
            open_questions.append(message.normalized_text)
            if len(open_questions) >= MAX_OPEN_QUESTIONS:
                break
        return open_questions

    @staticmethod
    def render_section(title: str, items: list[str]) -> str:
        return title + ":\n" + "\n".join(f"- {item}" for item in items)

    @classmethod
    def render_structured_summary(cls, messages: list[PreparedSummaryMessage]) -> str:
        topics = cls.extract_topics(messages)
        notable_points = cls.extract_notable_points(messages)
        questions = cls.extract_questions(messages)
        reply_threads = cls.extract_reply_threads(messages)
        open_questions = cls.extract_open_questions(messages)

        sections = []
        if topics:
            sections.append(cls.render_section("Темы", topics))
        if notable_points:
            sections.append(cls.render_section("Важное", notable_points))
        if questions:
            sections.append(cls.render_section("Вопросы", questions))
        if reply_threads:
            sections.append(cls.render_section("Ответы / треды", reply_threads))
        if open_questions:
            sections.append(cls.render_section("Открыто", open_questions))

        if not sections:
            return "Недостаточно данных для суммаризации."
        return "\n\n".join(sections)
