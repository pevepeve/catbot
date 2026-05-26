import json
from pathlib import Path
from typing import Optional

from sqlalchemy import select

from config import get_settings
from infrastructure.db import SessionLocal
from models.orm import AnimeThumbnail


class AnimeRepository:
    def __init__(self, session_factory=SessionLocal, schedule_path: Optional[str] = None):
        self.session_factory = session_factory
        settings = get_settings()
        self.schedule_path = Path(schedule_path or settings.anime_schedule_json)

    def load_schedule(self) -> dict:
        with self.schedule_path.open("rb") as schedule_file:
            return json.load(schedule_file)

    def get_thumbnail_id(self, filename: str) -> str:
        session = self.session_factory()
        try:
            statement = select(AnimeThumbnail.file_id).where(AnimeThumbnail.filename == filename)
            return session.execute(statement).scalar_one()
        finally:
            session.close()
