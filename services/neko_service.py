import hashlib
import io

from infrastructure.telegram_media_store import TelegramMediaStore
from repositories.neko_repository import NekoRepository


class NekoService:
    def __init__(self, repository: NekoRepository):
        self.repository = repository

    async def get_random_neko_id(self) -> str:
        return self.repository.get_random_file_id()

    async def add_neko(self, file_io: io.BytesIO, media_store: TelegramMediaStore) -> str:
        file_md5 = hashlib.md5(file_io.getbuffer()).hexdigest()
        filename = f"{file_md5}.jpg"

        if self.repository.exists_by_filename(filename):
            raise ValueError("Already exists")

        file_id = await media_store.upload_photo(file_io)
        self.repository.add_image(file_id=file_id, filename=filename)
        return file_md5

