import json
from datetime import datetime, timedelta, timezone as dt_timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select

from config import get_settings
from infrastructure.db import SessionLocal
from models.orm import AnimeThumbnail


class AnimeRepository:
    try:
        timezone = ZoneInfo("Europe/Moscow")
    except ZoneInfoNotFoundError:
        timezone = dt_timezone(timedelta(hours=3), name="Europe/Moscow")
    days_list = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    def __init__(self, session_factory=SessionLocal, schedule_path: Optional[str] = None):
        self.session_factory = session_factory
        settings = get_settings()
        self.schedule_path = Path(schedule_path or settings.anime_schedule_json)

    def load_schedule(self) -> dict:
        if not self.schedule_path.exists():
            return {day: [] for day in self.days_list}
        with self.schedule_path.open("rb") as schedule_file:
            return json.load(schedule_file)

    def save_schedule(self, schedule: dict) -> None:
        self.schedule_path.parent.mkdir(parents=True, exist_ok=True)
        with self.schedule_path.open("w", encoding="utf-8") as schedule_file:
            json.dump(schedule, schedule_file, ensure_ascii=False, indent=4)

    def is_schedule_stale(self, now: Optional[datetime] = None) -> bool:
        if not self.schedule_path.exists():
            return True

        current_time = now.astimezone(self.timezone) if now else datetime.now(self.timezone)
        updated_at = datetime.fromtimestamp(
            self.schedule_path.stat().st_mtime,
            tz=self.timezone,
        )
        current_week = current_time.isocalendar()[:2]
        updated_week = updated_at.isocalendar()[:2]
        return current_week != updated_week

    def get_thumbnail_id(self, filename: str) -> str:
        session = self.session_factory()
        try:
            statement = select(AnimeThumbnail.file_id).where(AnimeThumbnail.filename == filename)
            return session.execute(statement).scalar_one()
        finally:
            session.close()

    def thumbnail_exists(self, filename: str) -> bool:
        session = self.session_factory()
        try:
            statement = select(AnimeThumbnail.id).where(AnimeThumbnail.filename == filename)
            return session.execute(statement).scalar_one_or_none() is not None
        finally:
            session.close()

    def save_thumbnail_id(self, file_id: str, filename: str) -> None:
        session = self.session_factory()
        try:
            statement = select(AnimeThumbnail).where(AnimeThumbnail.filename == filename)
            thumbnail = session.execute(statement).scalar_one_or_none()
            if thumbnail is None:
                session.add(AnimeThumbnail(file_id=file_id, filename=filename))
            else:
                thumbnail.file_id = file_id
            session.commit()
        finally:
            session.close()
