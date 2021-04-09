import os
from time import sleep
from traceback import format_exc
from requests.exceptions import ReadTimeout, ConnectionError
from web import Bot
from database.db_session import DataBase


def start_bot():
    users_db = DataBase(os.environ.get('DATABASE_URL'))
    groups_db = DataBase(
        'sqlite:///database/db.sqlite?check_same_thread=false')
    log_dir = "https://dashboard.heroku.com/apps/vk-recommend/logs"
    model_name = os.environ.get("MODEL_NAME", 'vk_not_filtered')

    bot = Bot(users_db, groups_db, model_name)
    if os.environ.get('IS_DEPLOY'):
        while True:
            try:
                bot.listen()
            except (ReadTimeout, ConnectionError):
                print('No connection to VK')
                sleep(3)
            except Exception as e:
                bot.send_message(159635403,
                                 f'Произошла ошибка:\n{repr(e)}\n\n{log_dir}')
                bot.send_message(399923740,
                                 f'Произошла ошибка:\n{repr(e)}\n\n{log_dir}')
                print('=== ERROR ===')
                print(format_exc())
                print('=============')
                exit(1)
    else:
        bot.listen()


if __name__ == '__main__':
    start_bot()
