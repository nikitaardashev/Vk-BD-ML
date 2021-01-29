from sqlalchemy import Column, Integer, String


def groups(base):
    class Groups(base):
        __tablename__ = 'Groups'

        group_id = Column(Integer, primary_key=True, index=True, unique=True)
        name = Column(String)
        subject = Column(String)
        link = Column(String)
    return Groups
