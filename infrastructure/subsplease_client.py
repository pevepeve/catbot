import json
from io import BytesIO
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from PIL import Image


class SubspleaseClient:
    scraped_site = "https://subsplease.org"
    shows_folder = "/shows/"
    json_url = "https://subsplease.org/api/?f=schedule&tz=Europe/Moscow"
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

    def fetch_schedule(self) -> dict:
        response = requests.get(self.json_url)
        response.raise_for_status()
        animes = json.loads(response.text)

        anime_dictionary = {}
        for day in self.days_list:
            anime_day = animes["schedule"][day]
            anime_dictionary[day] = []
            for show in anime_day:
                anime_dictionary[day].append(
                    {
                        "title": show["title"],
                        "time": show["time"],
                        "synopsis": self.get_synopsis(show["page"]),
                        "image": self.save_image(show["image_url"], show["page"]),
                        "url": self.get_full_url(show["page"]),
                    }
                )
        return anime_dictionary

    def get_full_url(self, page: str) -> str:
        return self.scraped_site + self.shows_folder + page

    def get_synopsis(self, page: str) -> str:
        response = requests.get(self.get_full_url(page))
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        syn_list = soup.body.find_all("div", class_="series-syn")[0].find_all("p")
        return "\n".join(paragraph.get_text() for paragraph in syn_list).strip()

    def save_image(self, url: str, save_filename: str) -> str:
        response = requests.get(self.scraped_site + url)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content))
        self.media_folder.mkdir(parents=True, exist_ok=True)
        filename = f"{save_filename}.jpg"
        image.save(self.media_folder / filename)
        return filename

