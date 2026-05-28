from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class NekoImage(Base):
    __tablename__ = "NekoIDs"

    id = Column(Integer, primary_key=True)
    file_id = Column(String(255))
    filename = Column(String(255))


class AnimeThumbnail(Base):
    __tablename__ = "AnimeThumbsIDs"

    id = Column(Integer, primary_key=True)
    file_id = Column(String(255))
    filename = Column(String(255))


class SavedMessage(Base):
    __tablename__ = "SavedMessages"

    id = Column(Integer, primary_key=True)
    chatid = Column(Integer)
    chat_name = Column(String(255))
    chat_username = Column(String(255))
    chat_type = Column(String(32))
    message_id = Column(Integer)
    user_id = Column(Integer)
    user_name = Column(String(255))
    reply_to_message_id = Column(Integer)
    text = Column(Text)
    date = Column(String(255))
    content_type = Column(String(32))


# Backward-compatible aliases for existing imports.
NekoIds = NekoImage
AnimeThumbsIds = AnimeThumbnail
SavedMessages = SavedMessage

