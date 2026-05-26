from services.anime_service import AnimeService


class FakeAnimeRepository:
    def __init__(self):
        self.schedule = {
            "Monday": [{"title": "Show A", "time": "18:00", "image": "a.jpg"}],
            "Tuesday": [{"title": "Show B", "time": "19:00", "image": "b.jpg"}],
            "Wednesday": [],
            "Thursday": [],
            "Friday": [],
            "Saturday": [],
            "Sunday": [],
        }
        self.saved_schedule = None

    def load_schedule(self):
        return self.schedule

    def save_schedule(self, schedule):
        self.saved_schedule = schedule

    def get_thumbnail_id(self, filename):
        return {"a.jpg": "thumb-a", "b.jpg": "thumb-b"}[filename]


class FakeSubspleaseClient:
    def __init__(self, schedule):
        self.schedule = schedule

    def fetch_schedule(self):
        return self.schedule


def test_get_schedule_for_weekday():
    service = AnimeService(FakeAnimeRepository(), FakeSubspleaseClient({}))

    schedule = service.get_schedule_for_weekday("Monday")

    assert schedule == [{"title": "Show A", "time": "18:00", "image": "a.jpg"}]


def test_get_anime_details_and_thumbnail():
    service = AnimeService(FakeAnimeRepository(), FakeSubspleaseClient({}))

    details = service.get_anime_details("Tuesday", 0)
    thumbnail_id = service.get_thumbnail_id("b.jpg")

    assert details["title"] == "Show B"
    assert service.get_day_label("Tuesday") == "вторник"
    assert thumbnail_id == "thumb-b"


def test_refresh_schedule_saves_client_payload():
    repository = FakeAnimeRepository()
    new_schedule = {"Monday": [], "Tuesday": [], "Wednesday": [], "Thursday": [], "Friday": [], "Saturday": [], "Sunday": []}
    service = AnimeService(repository, FakeSubspleaseClient(new_schedule))

    service.refresh_schedule()

    assert repository.saved_schedule == new_schedule
