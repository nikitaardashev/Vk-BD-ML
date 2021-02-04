import os
from web import Bot
from database.db_session import DataBase


if __name__ == '__main__':
    db = DataBase(os.environ.get('DATABASE_URL'))
    log_dir = "https://dashboard.heroku.com/apps/vk-recommend/logs"

    bot = Bot(db)
    if os.environ.get('IS_DEPLOY'):
        try:
            bot.listen()
        except Exception as e:
            bot.send_message(159635403, f'Произошла ошибка:\n{e}\n\n{log_dir}')
            bot.send_message(399923740, f'Произошла ошибка:\n{e}\n\n{log_dir}')
            exit(1)
    else:
        bot.listen()
