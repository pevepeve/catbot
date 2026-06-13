import asyncio
import io
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from infrastructure.telegram_media_store import TelegramMediaStore
from infrastructure.subsplease_client import SubspleaseClient
from repositories.anime_repository import AnimeRepository


@dataclass(frozen=True)
class AnimeRefreshResult:
    refreshed: bool
    uploaded_thumbnails: int = 0


class AnimeService:
    days_list = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    days_list_ru = [
        "понедельник",
        "вторник",
        "среда",
        "четверг",
        "пятница",
        "суббота",
        "воскресенье",
    ]

    def __init__(self, repository: AnimeRepository, client: Optional[SubspleaseClient] = None):
        self.repository = repository
        self.client = client or SubspleaseClient()

    def get_day_label(self, weekday: str) -> str:
        return self.days_list_ru[self.days_list.index(weekday)]

    def get_schedule_for_weekday(self, weekday: str) -> list[dict]:
        schedule = self.repository.load_schedule()
        return schedule[weekday]

    def get_today_weekday(self) -> str:
        return self.days_list[datetime.now(self.repository.timezone).weekday()]

    def get_today_schedule(self) -> tuple[str, list[dict]]:
        weekday = self.get_today_weekday()
        return weekday, self.get_schedule_for_weekday(weekday)

    def get_anime_details(self, weekday: str, title_index: int) -> dict:
        return self.get_schedule_for_weekday(weekday)[title_index]

    def get_thumbnail_id(self, filename: str) -> str:
        return self.repository.get_thumbnail_id(filename)

    async def refresh_schedule(
        self,
        media_store: Optional[TelegramMediaStore] = None,
        force: bool = False,
    ) -> AnimeRefreshResult:
        refreshed = force or self.repository.is_schedule_stale()
        if refreshed:
            schedule = await asyncio.to_thread(self.client.fetch_schedule)
            await asyncio.to_thread(self.repository.save_schedule, schedule)
        else:
            schedule = await asyncio.to_thread(self.repository.load_schedule)

        uploaded_thumbnails = 0
        if media_store is not None:
            uploaded_thumbnails = await self.upload_missing_thumbnails(schedule, media_store)

        return AnimeRefreshResult(
            refreshed=refreshed,
            uploaded_thumbnails=uploaded_thumbnails,
        )

    async def upload_missing_thumbnails(
        self,
        schedule: dict,
        media_store: TelegramMediaStore,
    ) -> int:
        filenames = sorted(
            {
                anime["image"]: anime
                for titles in schedule.values()
                for anime in titles
                if anime.get("image")
            }.items()
        )

        uploaded_thumbnails = 0
        for filename, anime in filenames:
            exists = await asyncio.to_thread(self.repository.thumbnail_exists, filename)
            if exists:
                continue

            image_path = self.client.media_folder / filename
            if not image_path.exists():
                image_url = anime.get("image_url")
                page = anime.get("page")
                if not image_url or not page:
                    continue
                await asyncio.to_thread(
                    self.client.save_image,
                    image_url,
                    page,
                )

            file_bytes = await asyncio.to_thread(
                image_path.read_bytes
            )
            file_id = await media_store.upload_photo(
                io.BytesIO(file_bytes),
                filename=filename,
            )
            await asyncio.to_thread(self.repository.save_thumbnail_id, file_id, filename)
            uploaded_thumbnails += 1

        return uploaded_thumbnails

