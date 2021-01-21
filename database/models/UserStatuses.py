from sqlalchemy import Column, Integer, String

from database.db_session import sqlalchemy_base


class UserStatuses(sqlalchemy_base):
    __tablename__ = 'UserStatuses'

    user_id = Column(Integer, primary_key=True, index=True, unique=True)
    status = Column(String)
    page = Column(Integer, nullable=True)
    subjects = Column(String, nullable=True)
