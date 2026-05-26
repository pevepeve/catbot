import re
from typing import Optional

from config import get_settings


class LinkService:
    def __init__(self, nitter_instance: Optional[str] = None):
        settings = get_settings()
        self.nitter_instance = nitter_instance or settings.nitter_instance

    def rewrite_twitter_link(self, text: str) -> Optional[str]:
        match = re.search(
            r"(https:\/\/twitter\.com\/.*\/status\/\d*)\b",
            text,
            re.MULTILINE,
        )
        if not match:
            match = re.search(
                r"(https:\/\/twitter\.com\/\w*)\b",
                text,
                re.MULTILINE,
            )
        if not match:
            return None

        return match[1].replace("https://twitter.com/", self.nitter_instance)
