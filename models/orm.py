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
    text = Column(Text)
    date = Column(String(255))


# Backward-compatible aliases for existing imports.
NekoIds = NekoImage
AnimeThumbsIds = AnimeThumbnail
SavedMessages = SavedMessage

