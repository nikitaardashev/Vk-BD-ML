# if __name__ == '__main__':
#     # Search imports in parent directory (for model.predictor)
#     import sys
#
#     sys.path.insert(0, '..')

import sys
import os
import json
from typing import List, Union, Dict
from operator import itemgetter
from sqlalchemy import or_
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id

from model.predictor import Predictor
from database import db_session
from database.models.UserStatuses import UserStatuses
from database.models.GroupsIds import GroupsIds


class Bot:
    def __init__(self):
        group_token = os.environ['GROUP_TOKEN']
        group_id = int(os.environ['GROUP_ID'])
        service_token = os.environ['SERVICE_TOKEN']
        app_id = int(os.environ['APP_ID'])
        client_secret = os.environ['CLIENT_SECRET']

        self.predictor = Predictor(os.path.join('model', 'weights'))
        self.database_session = db_session.create_session()
        self.group_session = vk_api.VkApi(token=group_token,
                                          api_version='5.126')
        self.service_session = vk_api.VkApi(app_id=app_id,
                                            token=service_token,
                                            client_secret=client_secret)
        self.long_poll = VkBotLongPoll(self.group_session, group_id)
        self.group_api = self.group_session.get_api()
        self.service_api = self.service_session.get_api()

    def send_message(self,
                     user_id: int,
                     message: str,
                     keyboard: str = None) -> None:
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
        print(f'message {message[:30]}{"..." if len(message) > 30 else ""}'
              f' to {user_id} has been sent')

    def get_posts(self,
                  owner_id: int,
                  count: int = 1) -> Union[List[dict], dict]:
        """
        gets posts from user's or group's wall using method wall.get
        (https://vk.com/dev/wall.get)

        :param owner_id: wall's owner ID
        :param count: count of posts
        :return: list of dictionaries of dictionary, describing post
        """
        posts = self.service_api.wall.get(owner_id=owner_id, count=count)
        print(f'group {owner_id} posts received')
        try:
            if len(posts['items']) > 1:
                return posts['items']
            else:
                return posts['items'][0]
        except IndexError:
            print(f'error: {owner_id} {posts}')

    def get_subscriptions(self, user_id: int,
                          extended: bool = False) -> List[int]:
        """
        gets user's subscriptions using method users.getSubscriptions
        (https://vk.com/dev/users.getSubscriptions)

        :param user_id: user ID
        :param extended: get extended information or not
        :return: list of numbers defining user IDs
        """
        subscriptions = self.service_api.users.getSubscriptions(
            user_id=user_id,
            extended=int(extended)
        )
        print(f'received subscriptions from '
              f'{"user" if user_id > 0 else "group"} {abs(user_id)}')
        return subscriptions['groups']['items']

    def get_group_info(self,
                       group_id: int) -> \
            Union[Dict[str, Union[str, int]],
                  List[Dict[str, Union[str, int]]]]:
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

        if 'payload' in event.object['message']:
            payload = json.loads(event.object['message']['payload'])
        else:
            payload = {'command': 'start'}

        if 'command' in payload and payload['command'] == 'start':
            keyboard = VkKeyboard(one_time=True)
            keyboard.add_button('Начать анализ',
                                color=VkKeyboardColor.POSITIVE,
                                payload=json.dumps({'button':
                                                        'start_analysis'}))
            message = 'Перед началом анализа, пожалуйста, откройте список' \
                      ' ваших групп для всех пользователей в настройках' \
                      ' приватности.'
            user = self.database_session.query(UserStatuses).filter(
                UserStatuses.user_id == from_id).first()
            if user and user.subjects:
                keyboard.add_button('Перейти к рекомендациям',
                                    color=VkKeyboardColor.SECONDARY,
                                    payload=json.dumps(
                                        {'button': 'show_recommendation_1'}))
                message += '\nВы уже выполнили анализ, поэтому вы можете ' \
                           'сразу просмотреть свои рекомендации. '
            self.send_message(from_id, message, keyboard.get_keyboard())
            user_status = self.database_session.query(UserStatuses).filter(
                UserStatuses.user_id == from_id).first()
            if user_status:
                user_status.status = 'started'
            else:
                self.database_session.add(
                    UserStatuses(user_id=from_id, status='started'))
            self.database_session.commit()
        elif 'button' in payload and payload['button'] == 'start_analysis':
            message = 'Анализ начат. Пожалуйста, подождите.'
            self.send_message(from_id, message)

            texts = []

            groups_ids = self.get_subscriptions(from_id)
            for _id in groups_ids:
                try:
                    posts = map(itemgetter('text'),
                                filter(lambda x: not x['marked_as_ads'],
                                       self.get_posts(-_id, 10)))
                    texts.append('\n'.join(posts))
                except TypeError:
                    continue

            prediction = list(map(itemgetter(0),
                                  self.predictor.predict(texts)[:3]))

            user_status = self.database_session.query(UserStatuses).filter(
                UserStatuses.user_id == from_id).first()
            user_status.subjects = '&'.join(prediction)
            user_status.status = 'show_page'
            user_status.page = 1
            self.database_session.commit()

            message = 'В ходе анализа было выявлено, что вас ' \
                      'интересуют следующие категории групп:\n'
            message += '\n'.join([f'{i}. {category.capitalize()}'
                                  for i, category in enumerate(prediction, 1)])

            self.send_message(from_id, message)
            groups_ids = self.database_session.query(GroupsIds).filter(
                or_(GroupsIds.subject == prediction[0],
                    GroupsIds.subject == prediction[1],
                    GroupsIds.subject == prediction[2])
            ).all()
            show_groups = groups_ids[:10]
            print(show_groups)
            message = 'Страница 1:\n'
            message += '\n'.join([
                f'{i + 1}. {show_groups[i].name} -- '
                f'https://vk.com/club{show_groups[i].group_id} '
                for i in range(len(show_groups))
            ])
            keyboard = VkKeyboard(one_time=True)
            keyboard.add_button('Начать анализ повторно',
                                color=VkKeyboardColor.SECONDARY,
                                payload=json.dumps(
                                    {'button': 'start_analysis'}))
            keyboard.add_line()
            page_number = len(groups_ids) // 10 + 1
            keyboard.add_button(f'Страница {page_number}',
                                color=VkKeyboardColor.PRIMARY,
                                payload=json.dumps({
                                    'button':
                                        f'show_recommendation_{page_number}'
                                }))
            keyboard.add_button(f'Страница 2',
                                color=VkKeyboardColor.PRIMARY,
                                payload=json.dumps({
                                    'button':
                                        f'show_recommendation_2'
                                }))
            self.send_message(from_id, message, keyboard.get_keyboard())
        elif 'button' in payload and \
                'show_recommendation' in payload['button']:
            page = int(payload['button'].split('_')[2])
            recommendation = self.database_session.query(UserStatuses).filter(
                UserStatuses.user_id == from_id).first()
            recommendation = recommendation.subjects.split('&')
            groups_ids = self.database_session.query(GroupsIds).filter(or_(
                GroupsIds.subject == recommendation[0],
                GroupsIds.subject == recommendation[1],
                GroupsIds.subject == recommendation[2])).all()
            show_groups = groups_ids[(page - 1) * 10:page * 10]
            message = f'Страница {page}:\n'
            message += '\n'.join([
                f'{i + 1}. {show_groups[i].name} -- '
                f'https://vk.com/club{show_groups[i].group_id}'
                for i in range(len(show_groups))
            ])
            keyboard = VkKeyboard(one_time=True)
            keyboard.add_button('Начать анализ повторно',
                                color=VkKeyboardColor.SECONDARY,
                                payload=json.dumps(
                                    {'button': 'start_analysis'}))
            keyboard.add_line()
            page_number = page - 1 if page > 1 else len(
                groups_ids) // 10 + 1
            keyboard.add_button(f'Страница {page_number}',
                                color=VkKeyboardColor.PRIMARY,
                                payload=json.dumps({
                                    'button':
                                        f'show_recommendation_{page_number}'
                                }))
            page_number = (page + 1) % (len(groups_ids) // 10 + 1)
            page_number = page_number or len(groups_ids) // 10 + 1
            keyboard.add_button(f'Страница {page_number}',
                                color=VkKeyboardColor.PRIMARY,
                                payload=json.dumps({
                                    'button':
                                        f'show_recommendation_{page_number}'
                                }))
            self.send_message(from_id, message, keyboard.get_keyboard())
            user_status = self.database_session.query(UserStatuses).filter(
                UserStatuses.user_id == from_id).first()
            user_status.status = 'show_page'
            user_status.page = page
            self.database_session.commit()


if __name__ == '__main__':
    bot = Bot()
    bot.listen()
