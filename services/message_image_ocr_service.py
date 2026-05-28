from __future__ import annotations

import io
import logging

from repositories.message_image_ocr_repository import (
    MessageImageOCRRecord,
    MessageImageOCRRepository,
    NO_OCR_TEXT,
    PENDING_OCR_TEXT,
)
from services.ocr_service import OCRResult, OCRService

logger = logging.getLogger(__name__)


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

    @staticmethod
    def get_ocr_raw_text(ocr_result: OCRResult | None, ocr_attempted: bool) -> str:
        if ocr_result is not None:
            return ocr_result.raw_text
        if ocr_attempted:
            return NO_OCR_TEXT
        return PENDING_OCR_TEXT

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
        ocr_attempted: bool,
    ) -> bool:
        search_text = self.build_search_text(caption_text, ocr_result)
        ocr_raw_text = self.get_ocr_raw_text(ocr_result, ocr_attempted)

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
                ocr_raw_text=ocr_raw_text,
                search_text=search_text,
                file_id=file_id,
                file_unique_id=file_unique_id,
            )
        )
        return bool(search_text) or ocr_raw_text == PENDING_OCR_TEXT

    async def backfill_pending_images(self, bot, limit: int | None = None) -> int:
        if not self.ocr_service.is_available:
            return 0

        pending_records = self.repository.get_pending_records(limit=limit)
        processed_count = 0
        for record in pending_records:
            try:
                telegram_file = await bot.get_file(record.file_id)
                file_io = io.BytesIO()
                await bot.download_file(telegram_file.file_path, destination=file_io)
                ocr_result = self.ocr_service.extract_text(file_io)
                self.save_message_image(
                    chat_id=record.chat_id,
                    chat_name=record.chat_name,
                    chat_username=record.chat_username,
                    chat_type=record.chat_type,
                    message_id=record.message_id,
                    message_date=record.message_date,
                    user_id=record.user_id,
                    user_name=record.user_name,
                    caption_text=record.caption_text,
                    file_id=record.file_id,
                    file_unique_id=record.file_unique_id,
                    ocr_result=ocr_result,
                    ocr_attempted=True,
                )
                processed_count += 1
            except Exception:
                logger.exception(
                    "Failed OCR backfill for chat_id=%s message_id=%s",
                    record.chat_id,
                    record.message_id,
                )
        return processed_count
