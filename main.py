import os
from web import Bot
from database.db_session import DataBase


if __name__ == '__main__':
    db = DataBase(os.environ.get('DATABASE_URL'))

    bot = Bot(db)
    bot.listen()
