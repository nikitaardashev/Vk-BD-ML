import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Session
import sqlalchemy.ext.declarative as dec
from database.models.Groups import groups
from database.models.GroupsIds import groups_ids
from database.models.UserStatuses import user_statuses


class DataBase:
    def __init__(self, db_url: str):
        self.base = dec.declarative_base()

        if not db_url or not db_url.strip():
            raise Exception('Database file must be specified')

        print(f'Connecting to the database with address {db_url}')

        engine = sa.create_engine(db_url)
        self.factory = orm.sessionmaker(bind=engine)

        self.base.metadata.create_all(engine)

        self.Groups = groups(self.base)
        self.GroupsIds = groups_ids(self.base)
        self.UserStatuses = user_statuses(self.base)

    def create_session(self) -> Session:
        return self.factory()
