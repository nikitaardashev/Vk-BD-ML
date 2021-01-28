from sqlalchemy import Column, Integer, String

from database.db_session import sqlalchemy_base


class Groups(sqlalchemy_base):
    __tablename__ = 'Groups'

    group_id = Column(Integer, primary_key=True, index=True, unique=True)
    name = Column(String)
    subject = Column(String)
    link = Column(String)
