from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class NekoIds(Base):
    __tablename__ = 'NekoIDs'
    id = Column(Integer, primary_key=True)
    file_id = Column(String(255))
    filename = Column(String(255))

class AnimeThumbsIds(Base):
    __tablename__ = 'AnimeThumbsIDs'
    id = Column(Integer, primary_key=True)
    file_id = Column(String(255))
    filename = Column(String(255))