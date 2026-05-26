from repositories.message_repository import MessageRepository


class ChatHistoryService:
    def __init__(self, repository: MessageRepository):
        self.repository = repository

    async def save_message(self, message: str, message_date, chat_id: int) -> None:
        self.repository.save_message(message, message_date, chat_id)

    async def get_messages(self, chat_id: int) -> list[str]:
        return self.repository.get_messages(chat_id)

