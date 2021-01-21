if __name__ == '__main__':
    # Search imports in parent directory (for model.predictor)
    import sys
    sys.path.insert(0, '..')

import json
from typing import List, Union, Dict
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id

from model.predictor import Predictor
from database import db_session
from database.models.UserStatuses import UserStatuses


class Bot:
    def __init__(self):
        self.group_token = ''  # ключ доступа группы
        self.group_id = 0  # ID группы
        self.service_token = ''  # сервисный ключ доступа (из приложения)
        self.app_id = 0  # ID приложения
        self.client_secret = ''  # защищённый ключ (из приложения)
        self.database_session = db_session.create_session()
        self.group_session = vk_api.VkApi(token=self.group_token,
                                          api_version='5.126')
        self.service_session = vk_api.VkApi(app_id=self.app_id,
                                            token=self.service_token,
                                            client_secret=self.client_secret)
        self.long_poll = VkBotLongPoll(self.group_session, self.group_id)
        self.group_api = self.group_session.get_api()
        self.service_api = self.service_session.get_api()

    def send_message(self, user_id: int, message: str, keyboard: str = None) -> None:
        """
        sends a message to user using method messages.send
        (https://vk.com/dev/messages.send)

        :param user_id: recipient user ID
        :param message: message text
        :param keyboard: json describing keyboard attached with message
        :return: None
        """
        self.group_api.messages.send(user_id=user_id,
                                     random_id=get_random_id(),
                                     message=message,
                                     keyboard=keyboard)
        print(f'message {message[:15]}{"..." if len(message) > 15 else ""} to {user_id} has been sent')

    def get_posts(self, owner_id: int, count: int = 1) -> Union[List[dict], dict]:
        """
        gets posts from user's or group's wall using method wall.get
        (https://vk.com/dev/wall.get)

        :param owner_id: wall's owner ID
        :param count: count of posts
        :return: list of dictionaries of dictionary, describing post
        """
        posts = self.service_api.wall.get(owner_id=owner_id, count=count)
        print(f'group {owner_id} posts received')
        return posts['items'] if len(posts['items']) > 1 else posts['items'][0]

    def get_subscriptions(self, user_id: int, extended: bool = False) -> List[int]:
        """
        gets user's subscriptions using method users.getSubscriptions
        (https://vk.com/dev/users.getSubscriptions)

        :param user_id: user ID
        :param extended: get extended information or not
        :return: list of numbers defining user IDs
        """
        subscriptions = self.service_api.users.getSubscriptions(user_id=user_id, extended=int(extended))
        print(f'received subscriptions from {"user" if user_id > 0 else "group"} {abs(user_id)}')
        return subscriptions['groups']['items']

    def get_group_info(self, group_id: int) -> Union[Dict[str, Union[str, int]], List[Dict[str, Union[str, int]]]]:
        """
        gets information about one or more groups using method groups.getById
        (https://vk.com/dev/groups.getById)

        :param group_id: group ID
        :return: list of dictionaries of dictionary, describing information
        about group
        """
        info = self.service_api.groups.getById(group_id=group_id)
        print(f'received info from {group_id}')
        if len(info) == 1:
            return info[0]
        else:
            return info

    def listen(self) -> None:
        """
        gets updates from server and handling them
        :return: None
        """
        for event in self.long_poll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                self.process_new_message(event)

    def process_new_message(self, event):
        from_id = event.object['message']['from_id']
        payload = json.loads(event.object['message']['payload'])
        if 'command' in payload and payload['command'] == 'start':
            keyboard = VkKeyboard(one_time=True)
            keyboard.add_button('Начать анализ',
                                color=VkKeyboardColor.POSITIVE,
                                payload=json.dumps({'button': 'start_analysis'}))
            message = 'Перед началом анализа, пожалуйста, откройте список ваших' \
                      ' групп для всех пользователей в настройках приватности.'
            self.send_message(from_id, message, keyboard.get_keyboard())
            user_status = self.database_session.query(UserStatuses).filter(UserStatuses.user_id == from_id).first()
            if user_status:
                user_status.status = 'started'
            else:
                self.database_session.add(UserStatuses(user_id=from_id, status='started'))
            self.database_session.commit()
        elif 'button' in payload:
            message = 'Анализ начат. Пожалуйста, подождите.'
            self.send_message(from_id, message)
            # TODO:
            #  1. получить подписки пользователя методом get_subscriptions (обработать приватную страницу)
            #  2. получить n(?) постов с каждой, взять текст поста (одной строкой?)
            #  3. вызвать predict нейросети, получить вероятности отношения к каждой категории
            #  4. отправить сообщение с тремя(?) наиболее вероятными категориями
            #  5. показать первую страницу рекомендаций

            message = '1. [Категория 1] - XX%\n2. [Категория 2] - XX%\n3. [Категория 3] - XX%'
            self.send_message(from_id, message)
            groups_ids = [338, 376, 817]
            groups_names = [self.get_group_info(_id)['name'] for _id in groups_ids]
            message = '\n'.join([f'{i + 1}. {groups_names[i]} -- https://vk.com/club{groups_ids[i]}'
                                 for i in range(len(groups_ids))])
            keyboard = VkKeyboard(one_time=True)
            keyboard.add_button('Начать анализ повторно',
                                color=VkKeyboardColor.SECONDARY,
                                payload=json.dumps({'button': 'start_analysis'}))
            self.send_message(from_id, message, keyboard.get_keyboard())
            user_status = self.database_session.query(UserStatuses).filter(UserStatuses.user_id == from_id).first()
            user_status.status = 'show_page'
            user_status.page = 1
            self.database_session.commit()


if __name__ == '__main__':
    bot = Bot()
    bot.listen()
