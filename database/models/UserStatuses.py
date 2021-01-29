from sqlalchemy import Column, Integer, String


def user_statuses(base):
    class UserStatuses(base):
        __tablename__ = 'UserStatuses'

        user_id = Column(Integer, primary_key=True, index=True, unique=True)
        status = Column(String)
        page = Column(Integer, nullable=True)
        subjects = Column(String, nullable=True)
    return UserStatuses
