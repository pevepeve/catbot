import re

from common.summary import summarize_sumy
from repositories.message_repository import ChatMessageRecord
from services.chat_history_service import ChatHistoryService


NOISE_MESSAGE_MIN_LEN = 2


class SummaryService:
    def __init__(self, chat_history_service: ChatHistoryService):
        self.chat_history_service = chat_history_service

    async def summarize_recent(self, chat_id: int) -> str:
        messages = await self.chat_history_service.get_messages(chat_id)
        prepared_messages = self.prepare_messages(messages)
        if not prepared_messages:
            return "Недостаточно данных для суммаризации."
        return summarize_sumy("\n".join(prepared_messages))

    @staticmethod
    def normalize_text(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

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
    def format_message(cls, message: ChatMessageRecord) -> str:
        normalized_text = cls.normalize_text(message.text)
        timestamp = message.created_at[11:16] if len(message.created_at) >= 16 else "??:??"
        speaker = message.user_name or "Unknown"
        return f"[{timestamp}] {speaker}: {normalized_text}"

    @classmethod
    def prepare_messages(cls, messages: list[ChatMessageRecord]) -> list[str]:
        prepared_messages = []
        for message in messages:
            if cls.should_skip_message(message):
                continue
            prepared_messages.append(cls.format_message(message))
        return prepared_messages

