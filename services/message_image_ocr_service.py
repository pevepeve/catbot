from __future__ import annotations

from repositories.message_image_ocr_repository import (
    MessageImageOCRRecord,
    MessageImageOCRRepository,
)
from services.ocr_service import OCRResult, OCRService


class MessageImageOCRService:
    def __init__(
        self,
        repository: MessageImageOCRRepository,
        ocr_service: OCRService,
    ):
        self.repository = repository
        self.ocr_service = ocr_service

    @staticmethod
    def build_message_link(chat_id: int, chat_username: str, message_id: int) -> str:
        if chat_username:
            return f"https://t.me/{chat_username}/{message_id}"

        chat_id_str = str(chat_id)
        if chat_id_str.startswith("-100"):
            internal_chat_id = chat_id_str[4:]
            return f"https://t.me/c/{internal_chat_id}/{message_id}"
        return ""

    def build_search_text(self, caption_text: str, ocr_result: OCRResult | None) -> str:
        parts = []
        normalized_caption = self.ocr_service.normalize_text(caption_text) if caption_text else ""
        if normalized_caption.startswith("/"):
            normalized_caption = ""
        if normalized_caption:
            parts.append(normalized_caption)
        if ocr_result and ocr_result.normalized_text:
            parts.append(ocr_result.normalized_text)
        return " ".join(part for part in parts if part).strip()

    def save_message_image(
        self,
        *,
        chat_id: int,
        chat_name: str,
        chat_username: str,
        chat_type: str,
        message_id: int,
        message_date: str,
        user_id: int | None,
        user_name: str,
        caption_text: str,
        file_id: str,
        file_unique_id: str,
        ocr_result: OCRResult | None,
    ) -> bool:
        search_text = self.build_search_text(caption_text, ocr_result)
        if not search_text:
            return False

        self.repository.save_record(
            MessageImageOCRRecord(
                chat_id=chat_id,
                chat_name=chat_name,
                chat_username=chat_username,
                chat_type=chat_type,
                message_id=message_id,
                message_link=self.build_message_link(chat_id, chat_username, message_id),
                user_id=user_id,
                user_name=user_name,
                message_date=message_date,
                caption_text=caption_text,
                ocr_raw_text=ocr_result.raw_text if ocr_result else "",
                search_text=search_text,
                file_id=file_id,
                file_unique_id=file_unique_id,
            )
        )
        return True
