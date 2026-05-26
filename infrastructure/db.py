from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import get_settings
from models.orm import Base


settings = get_settings()

engine = create_engine(f"sqlite:///{settings.db_filename}")
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(engine)

