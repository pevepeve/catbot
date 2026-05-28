from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class SubspleaseClient:
    scraped_site = "https://subsplease.org/"
    shows_folder = "/shows/"
    json_url = "https://subsplease.org/api/?f=schedule&tz=Europe/Moscow"
    request_timeout = 30
    days_list = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    def __init__(self, media_folder: str = "media"):
        self.media_folder = Path(media_folder)
        self.session = requests.Session()

    def fetch_schedule(self) -> dict:
        response = self.session.get(self.json_url, timeout=self.request_timeout)
        response.raise_for_status()
        animes = response.json()

        anime_dictionary = {}
        for day in self.days_list:
            anime_day = animes["schedule"].get(day, [])
            anime_dictionary[day] = []
            for show in anime_day:
                anime_dictionary[day].append(
                    {
                        "title": show["title"],
                        "page": show["page"],
                        "time": show["time"],
                        "image_url": show["image_url"],
                        "synopsis": self.get_synopsis(show["page"]),
                        "image": self.save_image(show["image_url"], show["page"]),
                        "url": self.get_full_url(show["page"]),
                    }
                )
        return anime_dictionary

    def get_full_url(self, page: str) -> str:
        return urljoin(self.scraped_site, self.shows_folder + page + "/")

    def get_synopsis(self, page: str) -> str:
        response = self.session.get(self.get_full_url(page), timeout=self.request_timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        synopsis_node = soup.select_one("div.series-syn")
        if synopsis_node is None:
            return ""
        syn_list = synopsis_node.find_all("p")
        return "\n".join(paragraph.get_text() for paragraph in syn_list).strip()

    def save_image(self, url: str, save_filename: str) -> str:
        parsed_path = urlparse(url).path
        suffix = Path(parsed_path).suffix.lower() or ".jpg"
        filename = f"{save_filename}{suffix}"

        self.media_folder.mkdir(parents=True, exist_ok=True)
        target_path = self.media_folder / filename
        if target_path.exists():
            return filename

        response = self.session.get(urljoin(self.scraped_site, url), timeout=self.request_timeout)
        response.raise_for_status()
        target_path.write_bytes(response.content)
        return filename

