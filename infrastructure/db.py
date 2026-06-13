from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from config import get_settings
from models.orm import Base


settings = get_settings()

engine = create_engine(f"sqlite:///{settings.db_filename}")
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(engine)
    ensure_saved_messages_columns()


def ensure_saved_messages_columns() -> None:
    inspector = inspect(engine)
    if "SavedMessages" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("SavedMessages")}
    required_columns = {
        "chat_name": "VARCHAR(255)",
        "chat_username": "VARCHAR(255)",
        "chat_type": "VARCHAR(32)",
        "message_id": "INTEGER",
        "user_id": "INTEGER",
        "user_name": "VARCHAR(255)",
        "reply_to_message_id": "INTEGER",
        "content_type": "VARCHAR(32)",
    }

    missing_columns = {
        name: column_type
        for name, column_type in required_columns.items()
        if name not in existing_columns
    }
    if not missing_columns:
        return

    with engine.begin() as connection:
        for column_name, column_type in missing_columns.items():
            connection.execute(
                text(f'ALTER TABLE "SavedMessages" ADD COLUMN {column_name} {column_type}')
            )

