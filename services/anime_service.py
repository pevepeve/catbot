from datetime import date
from typing import Optional

from infrastructure.subsplease_client import SubspleaseClient
from repositories.anime_repository import AnimeRepository


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
        return self.days_list[date.today().weekday()]

    def get_today_schedule(self) -> tuple[str, list[dict]]:
        weekday = self.get_today_weekday()
        return weekday, self.get_schedule_for_weekday(weekday)

    def get_anime_details(self, weekday: str, title_index: int) -> dict:
        return self.get_schedule_for_weekday(weekday)[title_index]

    def get_thumbnail_id(self, filename: str) -> str:
        return self.repository.get_thumbnail_id(filename)

    def refresh_schedule(self) -> None:
        schedule = self.client.fetch_schedule()
        self.repository.save_schedule(schedule)

