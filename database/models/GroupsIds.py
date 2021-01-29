from sqlalchemy import Column, Integer, String


def groups_ids(base):
    class GroupsIds(base):
        __tablename__ = 'GroupsIds'

        group_id = Column(Integer, primary_key=True, index=True, unique=True)
        name = Column(String)
        subject = Column(String)
        link = Column(String)
    return GroupsIds