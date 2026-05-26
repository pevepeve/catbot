import random

from sqlalchemy import select

from infrastructure.db import SessionLocal
from models.orm import NekoImage


class NekoRepository:
    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    def exists_by_filename(self, filename: str) -> bool:
        session = self.session_factory()
        try:
            statement = select(NekoImage.filename).where(NekoImage.filename == filename)
            return session.execute(statement).scalars().first() is not None
        finally:
            session.close()

    def add_image(self, file_id: str, filename: str) -> None:
        session = self.session_factory()
        try:
            session.add(NekoImage(file_id=file_id, filename=filename))
            session.commit()
        finally:
            session.close()

    def get_random_file_id(self) -> str:
        session = self.session_factory()
        try:
            file_ids = session.execute(select(NekoImage.file_id)).scalars().all()
        finally:
            session.close()

        if not file_ids:
            raise ValueError("No neko images configured")

        return random.choice(file_ids)

