from repositories.message_repository import ChatMessageRecord, MessageRepository


class ChatHistoryService:
    def __init__(self, repository: MessageRepository):
        self.repository = repository

    async def save_message(
        self,
        text: str,
        message_date,
        chat_id: int,
        chat_name: str = "",
        chat_username: str = "",
        chat_type: str = "",
        message_id: int | None = None,
        user_id: int | None = None,
        user_name: str = "",
        reply_to_message_id: int | None = None,
        content_type: str = "text",
    ) -> None:
        self.repository.save_message(
            text=text,
            message_date=message_date,
            chat_id=chat_id,
            chat_name=chat_name,
            chat_username=chat_username,
            chat_type=chat_type,
            message_id=message_id,
            user_id=user_id,
            user_name=user_name,
            reply_to_message_id=reply_to_message_id,
            content_type=content_type,
        )

    async def get_messages(self, chat_id: int) -> list[ChatMessageRecord]:
        return self.repository.get_messages(chat_id)

