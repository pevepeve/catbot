from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Optional

from PIL import Image

try:
    import pytesseract
    from pytesseract import TesseractNotFoundError
except ImportError:  # pragma: no cover - optional dependency in local dev
    pytesseract = None

    class TesseractNotFoundError(Exception):
        pass


OCR_LANGUAGE = "rus+eng"
OCR_TEXT_MIN_LEN = 2


@dataclass(frozen=True)
class OCRResult:
    raw_text: str
    normalized_text: str


class OCRService:
    def __init__(self):
        self.is_available = False
        self.startup_warning: str | None = None
        self._detect_engine()

    def _detect_engine(self) -> None:
        if pytesseract is None:
            self.startup_warning = (
                "OCR indexing disabled: pytesseract is not installed. "
                "Incoming image messages will not be OCR-indexed."
            )
            return

        try:
            pytesseract.get_tesseract_version()
        except (TesseractNotFoundError, OSError) as error:
            self.startup_warning = (
                "OCR indexing disabled: Tesseract engine is unavailable. "
                f"Incoming image messages will not be OCR-indexed. Details: {error}"
            )
            return

        self.is_available = True

    @staticmethod
    def normalize_text(text: str) -> str:
        text = text.replace("ё", "е").replace("Ё", "Е")
        text = re.sub(r"\s+", " ", text)
        return text.strip().lower()

    @staticmethod
    def has_meaningful_text(text: str) -> bool:
        if len(text.strip()) < OCR_TEXT_MIN_LEN:
            return False
        return bool(re.search(r"[A-Za-zА-Яа-яЁё0-9]", text))

    @staticmethod
    def preprocess_image(file_io: io.BytesIO) -> Image.Image:
        file_io.seek(0)
        image = Image.open(file_io)
        image = image.convert("L")
        width, height = image.size
        if max(width, height) < 1200:
            image = image.resize((width * 2, height * 2))
        return image

    def extract_text(self, file_io: io.BytesIO) -> OCRResult | None:
        if not self.is_available or pytesseract is None:
            return None

        image = self.preprocess_image(file_io)
        raw_text = pytesseract.image_to_string(image, lang=OCR_LANGUAGE).strip()
        normalized_text = self.normalize_text(raw_text)
        if not self.has_meaningful_text(normalized_text):
            return None
        return OCRResult(raw_text=raw_text, normalized_text=normalized_text)
