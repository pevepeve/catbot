from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
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
TOPIC_SCORE_MIN = 3
NOTABLE_SCORE_MIN = 3
SIMILARITY_THRESHOLD = 0.65
QUESTION_WORDS = {
    "\u043a\u0430\u043a",
    "\u043a\u043e\u0433\u0434\u0430",
    "\u043a\u0442\u043e",
    "\u043a\u0443\u0434\u0430",
    "\u0433\u0434\u0435",
    "\u0437\u0430\u0447\u0435\u043c",
    "\u043f\u043e\u0447\u0435\u043c\u0443",
    "\u0447\u0442\u043e",
    "\u0447\u0435\u0433\u043e",
    "\u043a\u0430\u043a\u043e\u0439",
    "\u043a\u0430\u043a\u0430\u044f",
    "\u043a\u0430\u043a\u0438\u0435",
    "\u043a\u0430\u043a\u043e\u0433\u043e",
    "\u043d\u0443\u0436\u043d\u043e",
    "\u043d\u0430\u0434\u043e",
}
LINK_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
TOKEN_RE = re.compile(r"[A-Za-z\u0400-\u04FF0-9_-]+")
CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
SUMMARY_EMPTY_MESSAGE = (
    "\u041d\u0435\u0434\u043e\u0441\u0442\u0430\u0442\u043e\u0447\u043d\u043e "
    "\u0434\u0430\u043d\u043d\u044b\u0445 \u0434\u043b\u044f "
    "\u0441\u0443\u043c\u043c\u0430\u0440\u0438\u0437\u0430\u0446\u0438\u0438."
)
TOPICS_TITLE = "\u0422\u0435\u043c\u044b"
NOTABLE_TITLE = "\u0412\u0430\u0436\u043d\u043e\u0435"


@lru_cache(maxsize=1)
def load_stopwords() -> frozenset[str]:
    stopwords_path = Path(__file__).with_name("summary_stopwords.txt")
    if not stopwords_path.exists():
        return frozenset()

    words = set()
    for raw_line in stopwords_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip().lower()
        if not line or line.startswith("#"):
            continue
        words.add(line)
    return frozenset(words)


STOPWORDS = load_stopwords()


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
    topic_lemmas: tuple[str, ...]
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
            return SUMMARY_EMPTY_MESSAGE
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

    @staticmethod
    def get_token_pos(token: str) -> str | None:
        if MORPH is None or not CYRILLIC_RE.search(token):
            return None
        return MORPH.parse(token)[0].tag.POS

    @classmethod
    def is_meaningful_token(cls, token: str) -> bool:
        if len(token) < 3 and not token.isdigit():
            return False
        if token in STOPWORDS:
            return False
        if token.startswith(("http", "www", "@", "#", "/")):
            return False
        return bool(re.search(r"[A-Za-z\u0400-\u04FF0-9]", token))

    @classmethod
    def is_topic_token(cls, token: str) -> bool:
        if token.isdigit() or len(token) < 4:
            return False
        if token in STOPWORDS:
            return False

        pos = cls.get_token_pos(token)
        if pos is None:
            return True
        return pos in {"NOUN", "PROPN"}

    @classmethod
    def extract_lemmas(cls, text: str) -> tuple[str, ...]:
        lemmas = []
        for token in cls.tokenize_text(text):
            normalized = cls.normalize_token(token)
            if normalized and cls.is_meaningful_token(normalized):
                lemmas.append(normalized)
        return tuple(lemmas)

    @classmethod
    def extract_topic_lemmas(cls, lemmas: Iterable[str]) -> tuple[str, ...]:
        return tuple(lemma for lemma in lemmas if cls.is_topic_token(lemma))

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
        topic_lemmas: tuple[str, ...],
        is_question: bool,
        is_reply: bool,
        has_link: bool,
    ) -> int:
        score = min(len(set(lemmas)), 6)
        score += min(len(set(topic_lemmas)), 3)
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
            topic_lemmas = cls.extract_topic_lemmas(lemmas)
            if not lemmas and not LINK_RE.search(normalized_text) and "?" not in normalized_text:
                continue

            is_question = cls.detect_question(normalized_text, lemmas)
            is_reply = message.reply_to_message_id is not None
            has_link = LINK_RE.search(normalized_text) is not None
            score = cls.score_message(
                normalized_text,
                lemmas,
                topic_lemmas,
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
                    topic_lemmas=topic_lemmas,
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

    @staticmethod
    def similarity_ratio(first_tokens: tuple[str, ...], second_tokens: tuple[str, ...]) -> float:
        first_set = set(first_tokens)
        second_set = set(second_tokens)
        if not first_set or not second_set:
            return 0.0
        intersection = len(first_set & second_set)
        union = len(first_set | second_set)
        if union == 0:
            return 0.0
        return intersection / union

    @classmethod
    def messages_are_similar(
        cls,
        first_message: PreparedSummaryMessage,
        second_message: PreparedSummaryMessage,
    ) -> bool:
        if first_message.normalized_text == second_message.normalized_text:
            return True
        if (
            first_message.normalized_text in second_message.normalized_text
            or second_message.normalized_text in first_message.normalized_text
        ):
            return True

        first_tokens = first_message.topic_lemmas or first_message.lemmas
        second_tokens = second_message.topic_lemmas or second_message.lemmas
        return cls.similarity_ratio(first_tokens, second_tokens) >= SIMILARITY_THRESHOLD

    @classmethod
    def extract_topics(cls, messages: list[PreparedSummaryMessage]) -> list[str]:
        topic_weights: dict[str, int] = {}
        topic_message_counts: dict[str, int] = {}
        topic_speakers: dict[str, set[str]] = {}

        for message in messages:
            if message.score < TOPIC_SCORE_MIN:
                continue

            unique_topics = set(message.topic_lemmas)
            if not unique_topics:
                continue

            weight = max(message.score, 1)
            for lemma in unique_topics:
                topic_weights[lemma] = topic_weights.get(lemma, 0) + weight
                topic_message_counts[lemma] = topic_message_counts.get(lemma, 0) + 1
                topic_speakers.setdefault(lemma, set()).add(message.speaker)

        repeated_topics = {
            topic: weight
            for topic, weight in topic_weights.items()
            if topic_message_counts.get(topic, 0) >= 2
        }
        selected_topics = repeated_topics or topic_weights

        ranked_topics = sorted(
            selected_topics.items(),
            key=lambda item: (
                -len(topic_speakers.get(item[0], set())),
                -topic_message_counts.get(item[0], 0),
                -item[1],
                -len(item[0]),
                item[0],
            ),
        )
        return [topic for topic, _ in ranked_topics[:MAX_TOPICS]]

    @classmethod
    def extract_notable_points(cls, messages: list[PreparedSummaryMessage]) -> list[str]:
        ranked_messages = sorted(
            messages,
            key=lambda message: (
                -message.score,
                -len(set(message.topic_lemmas or message.lemmas)),
                -len(message.normalized_text),
                message.timestamp,
                message.speaker,
            ),
        )
        notable_messages: list[PreparedSummaryMessage] = []
        notable_points = []

        for message in ranked_messages:
            if message.score < NOTABLE_SCORE_MIN:
                continue
            if any(cls.messages_are_similar(existing, message) for existing in notable_messages):
                continue

            notable_messages.append(message)
            notable_points.append(cls.format_transcript_line(message))
            if len(notable_points) >= MAX_NOTABLE_POINTS:
                break

        if notable_points:
            return notable_points

        fallback_messages = sorted(messages, key=lambda message: (message.timestamp, message.speaker))
        for message in fallback_messages:
            if any(cls.messages_are_similar(existing, message) for existing in notable_messages):
                continue
            notable_messages.append(message)
            notable_points.append(cls.format_transcript_line(message))
            if len(notable_points) >= MAX_NOTABLE_POINTS:
                break
        return notable_points

    @staticmethod
    def render_section(title: str, items: list[str]) -> str:
        return title + ":\n" + "\n".join(f"- {item}" for item in items)

    @classmethod
    def render_structured_summary(cls, messages: list[PreparedSummaryMessage]) -> str:
        topics = cls.extract_topics(messages)
        notable_points = cls.extract_notable_points(messages)

        sections = []
        if topics:
            sections.append(cls.render_section(TOPICS_TITLE, topics))
        if notable_points:
            sections.append(cls.render_section(NOTABLE_TITLE, notable_points))

        if not sections:
            return SUMMARY_EMPTY_MESSAGE
        return "\n\n".join(sections)
