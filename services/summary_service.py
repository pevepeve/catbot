from common.summary import summarize_sumy
from services.chat_history_service import ChatHistoryService


class SummaryService:
    def __init__(self, chat_history_service: ChatHistoryService):
        self.chat_history_service = chat_history_service

    async def summarize_recent(self, chat_id: int) -> str:
        messages = await self.chat_history_service.get_messages(chat_id)
        return summarize_sumy(". \n".join(messages))

