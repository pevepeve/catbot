from sqlalchemy import Column, Integer, String, Text, UniqueConstraint
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


class MessageImageOCR(Base):
    __tablename__ = "MessageImageOCR"
    __table_args__ = (
        UniqueConstraint("chat_id", "message_id", name="uq_MessageImageOCR_chat_message"),
    )

    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer)
    chat_name = Column(String(255))
    chat_username = Column(String(255))
    chat_type = Column(String(32))
    message_id = Column(Integer)
    message_link = Column(String(255))
    user_id = Column(Integer)
    user_name = Column(String(255))
    message_date = Column(String(255))
    caption_text = Column(Text)
    ocr_raw_text = Column(Text)
    search_text = Column(Text)
    file_id = Column(String(255))
    file_unique_id = Column(String(255))


# Backward-compatible aliases for existing imports.
NekoIds = NekoImage
AnimeThumbsIds = AnimeThumbnail
SavedMessages = SavedMessage

