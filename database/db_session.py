import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Session
import sqlalchemy.ext.declarative as dec

sqlalchemy_base = dec.declarative_base()

_factory: orm.session.Session = None


def global_init(db_file: str):
    global _factory

    if _factory:
        return

    if not db_file or not db_file.strip():
        raise Exception('Database file must be specified')

    connection_str = f'sqlite:///{db_file.strip()}?check_same_thread=false'
    print(f'Connecting to the database with address {connection_str}')

    from .models import __all_db_models

    engine = sa.create_engine(connection_str)
    _factory = orm.sessionmaker(bind=engine)

    sqlalchemy_base.metadata.create_all(engine)


def create_session() -> Session:
    global _factory
    return _factory()
