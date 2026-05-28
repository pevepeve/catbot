import asyncio
import tempfile
from pathlib import Path

from services.anime_service import AnimeService


class FakeAnimeRepository:
    def __init__(self):
        self.schedule = {
            "Monday": [{
                "title": "Show A",
                "time": "18:00",
                "page": "show-a",
                "image": "a.jpg",
                "image_url": "/images/a.jpg",
                "url": "https://example.com/a",
            }],
            "Tuesday": [{
                "title": "Show B",
                "time": "19:00",
                "page": "show-b",
                "image": "b.jpg",
                "image_url": "/images/b.jpg",
                "url": "https://example.com/b",
            }],
            "Wednesday": [],
            "Thursday": [],
            "Friday": [],
            "Saturday": [],
            "Sunday": [],
        }
        self.saved_schedule = None
        self.saved_thumbnails = {}
        self.stale = True

    def load_schedule(self):
        return self.schedule

    def save_schedule(self, schedule):
        self.saved_schedule = schedule
        self.schedule = schedule

    def is_schedule_stale(self):
        return self.stale

    def get_thumbnail_id(self, filename):
        return {"a.jpg": "thumb-a", "b.jpg": "thumb-b"}[filename]

    def thumbnail_exists(self, filename):
        return filename in self.saved_thumbnails

    def save_thumbnail_id(self, file_id, filename):
        self.saved_thumbnails[filename] = file_id


class FakeSubspleaseClient:
    def __init__(self, schedule, media_folder=None):
        self.schedule = schedule
        self.fetch_calls = 0
        self.media_folder = Path(media_folder or ".")

    def fetch_schedule(self):
        self.fetch_calls += 1
        return self.schedule


class FakeMediaStore:
    def __init__(self):
        self.uploads = []

    async def upload_photo(self, file_io, filename="upload.jpg"):
        self.uploads.append((filename, file_io.getvalue()))
        return f"uploaded-{filename}"


def test_get_schedule_for_weekday():
    service = AnimeService(FakeAnimeRepository(), FakeSubspleaseClient({}))

    schedule = service.get_schedule_for_weekday("Monday")

    assert schedule == [{
        "title": "Show A",
        "time": "18:00",
        "page": "show-a",
        "image": "a.jpg",
        "image_url": "/images/a.jpg",
        "url": "https://example.com/a",
    }]


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

    result = asyncio.run(service.refresh_schedule())

    assert repository.saved_schedule == new_schedule
    assert result.refreshed is True


def test_refresh_schedule_uploads_missing_thumbnails_from_cached_media():
    repository = FakeAnimeRepository()
    schedule = {
        "Monday": [{
            "title": "Show A",
            "time": "18:00",
            "page": "show-a",
            "image": "a.jpg",
            "image_url": "/images/a.jpg",
            "url": "https://example.com/a",
        }],
        "Tuesday": [{
            "title": "Show B",
            "time": "19:00",
            "page": "show-b",
            "image": "b.jpg",
            "image_url": "/images/b.jpg",
            "url": "https://example.com/b",
        }],
        "Wednesday": [],
        "Thursday": [],
        "Friday": [],
        "Saturday": [],
        "Sunday": [],
    }
    with tempfile.TemporaryDirectory() as temp_dir:
        media_folder = Path(temp_dir)
        (media_folder / "a.jpg").write_bytes(b"a-bytes")
        (media_folder / "b.jpg").write_bytes(b"b-bytes")
        service = AnimeService(repository, FakeSubspleaseClient(schedule, media_folder=media_folder))
        media_store = FakeMediaStore()

        result = asyncio.run(service.refresh_schedule(media_store))

    assert result.refreshed is True
    assert result.uploaded_thumbnails == 2
    assert repository.saved_thumbnails == {
        "a.jpg": "uploaded-a.jpg",
        "b.jpg": "uploaded-b.jpg",
    }
    assert media_store.uploads == [
        ("a.jpg", b"a-bytes"),
        ("b.jpg", b"b-bytes"),
    ]


def test_refresh_schedule_uses_cached_schedule_when_week_is_fresh():
    repository = FakeAnimeRepository()
    repository.stale = False
    repository.schedule = {
        "Monday": [{
            "title": "Show A",
            "time": "18:00",
            "page": "show-a",
            "image": "a.jpg",
            "image_url": "/images/a.jpg",
            "url": "https://example.com/a",
        }],
        "Tuesday": [],
        "Wednesday": [],
        "Thursday": [],
        "Friday": [],
        "Saturday": [],
        "Sunday": [],
    }
    with tempfile.TemporaryDirectory() as temp_dir:
        media_folder = Path(temp_dir)
        (media_folder / "a.jpg").write_bytes(b"a-bytes")
        service = AnimeService(
            repository,
            FakeSubspleaseClient(repository.schedule, media_folder=media_folder),
        )
        media_store = FakeMediaStore()

        result = asyncio.run(service.refresh_schedule(media_store))

    assert result.refreshed is False
    assert result.uploaded_thumbnails == 1
    assert service.client.fetch_calls == 0
