import os
import json
import threading

from random import sample
from typing import List, Union, Dict
from operator import itemgetter
from sqlalchemy import or_

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id

from model.predictor import Predictor


class Bot:
    def __init__(self, users_db, groups_db, model_name):
        group_token = os.environ['GROUP_TOKEN']
        group_id = int(os.environ['GROUP_ID'])
        service_token = os.environ['SERVICE_TOKEN']
        app_id = int(os.environ['APP_ID'])
        client_secret = os.environ['CLIENT_SECRET']

        self.visited = set()
        self.processing = set()

        self.admin_pwd = os.environ['ADMIN_PWD']
        self.new_cats = sorted(['физика', 'математика', 'лингвистика',
                                'информатика', 'литература', 'химия',
                                'география', "психология", "обществознание",
                                "история", "музыка", "астрономия", "маркетинг",
                                "биология", "спорт", "искусство", "бизнес"])

        self.predictor = Predictor(model_name)
        self.users_db = users_db
        self.groups_db = groups_db
        self.groups_session = vk_api.VkApi(token=group_token,
                                          api_version='5.126')
        self.service_session = vk_api.VkApi(app_id=app_id,
                                            token=service_token,
                                            client_secret=client_secret)
        self.long_poll = VkBotLongPoll(self.groups_session, group_id)
        self.group_api = self.groups_session.get_api()
        self.service_api = self.service_session.get_api()

        # For dataset filtering
        groups_session = groups_db.create_session()
        self.latest_id = groups_session.query(
            groups_db.Groups.group_id).order_by(
            groups_db.Groups.group_id.desc()).first()
        if self.latest_id is None:
            self.latest_id = 0
        else:
            self.latest_id = self.latest_id[0]

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
        print(f'<-- message {message[:30]}{"..." if len(message) > 30 else ""}'
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

    def get_subscriptions(self, user_id: int, count=100) -> List[int]:
        """
        gets user's subscriptions using method users.getSubscriptions
        (https://vk.com/dev/users.getSubscriptions)

        :param user_id: user ID
        :param count: get random {count} groups
        :return: list of numbers defining user IDs
        """
        subscriptions = self.service_api.users.getSubscriptions(
            user_id=user_id,
            extended=1
        )
        print(f'received subscriptions from '
              f'{"user" if user_id > 0 else "group"} {abs(user_id)}')
        ids = [i['id'] for i in subscriptions['items']
               if not i['is_closed'] and
               'type' in i and
               'deactivated' not in i]
        return ids if len(ids) <= count else sample(ids, count)

    def get_group_info(self, group_id: int) -> Union[
        Dict[str, Union[str, int]], List[Dict[str, Union[str, int]]]
    ]:
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
                threading.Thread(
                    target=self.process_new_message, args=(event,)
                ).start()

    def process_new_message(self, event):
        from_id = event.object['message']['from_id']
        cmd = event.object['message']['text']
        print(f'--> {from_id} sent "{cmd}"')

        if from_id in self.processing:
            self.send_message(from_id, 'Подождите, анализ выполняется')
            return

        payload = json.loads(event.object['message'].get('payload', '{}'))

        if payload.get('button') == 'start_analysis':
            self.command_start_analysis(from_id)
        elif ('button' in payload and
              'show_recommendation' in payload['button']):
            self.command_show_recommendation(from_id, payload)
        elif ''.join(filter(str.isalpha, cmd.lower())) == self.admin_pwd:
            self.command_admin(from_id)
        elif ('button' in payload and
              'dataset_filter' in payload['button']):
            self.command_dataset_filter(from_id, payload)
        else:
            self.command_start(from_id)

    def command_start(self, from_id):
        users_session = self.users_db.create_session()
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('Начать анализ',
                            color=VkKeyboardColor.POSITIVE,
                            payload=json.dumps({'button': 'start_analysis'}))
        msg = ('Здравствуйте, я - Виталя, бот-рекомендатор. Я помогу вам '
               'определить ваши интересы и подскажу, где найти ещё больше '
               'полезных групп ВКонтакте. Начнём анализ?')

        user = self.get_user(from_id, users_session)
        if user and user.subjects:
            keyboard.add_button('Перейти к рекомендациям',
                                color=VkKeyboardColor.SECONDARY,
                                payload=json.dumps(
                                    {'button': 'show_recommendation_1'}))
            msg = ('С возвращением! Желаете провести анализ снова или '
                   'посмотреть, что я рекомендовал вам в прошлый раз?'
                   if from_id in self.visited else 'Нужно нажать на кнопку')
            self.visited.add(from_id)
        self.send_message(from_id, msg, keyboard.get_keyboard())
        user_status = self.get_user(from_id, users_session)
        if user_status:
            user_status.status = 'started'
        else:
            users_session.add(
                self.users_db.UserStatuses(user_id=from_id, status='started'))
            print(f'=== user {from_id} added')
        users_session.commit()

    def command_start_analysis(self, from_id):
        users_session = self.users_db.create_session()
        groups_session = self.groups_db.create_session()
        texts = []

        user_status = self.get_user(from_id, users_session)
        if not user_status:
            users_session.add(
                self.users_db.UserStatuses(user_id=from_id, status='started'))
            print(f'=== user {from_id} added (stranger analysis)')
        users_session.commit()

        try:
            group_ids = self.get_subscriptions(from_id)
        except vk_api.exceptions.ApiError:
            message = 'Ваш профиль закрыт, я не могу увидеть подписки'
            keyboard = VkKeyboard(one_time=True)
            keyboard.add_button('Теперь профиль открыт, начать анализ',
                                color=VkKeyboardColor.POSITIVE,
                                payload=json.dumps(
                                    {'button': 'start_analysis'}))
            self.send_message(from_id, message, keyboard.get_keyboard())
            return

        message = ('Анализ может занять несколько минут. Пожалуйста, '
                   'подождите.')
        self.send_message(from_id, message)
        self.processing.add(from_id)

        for _id in group_ids:
            try:
                posts = map(itemgetter('text'),
                            filter(lambda x: not x['marked_as_ads'],
                                   self.get_posts(-_id, 10)))
                texts.append('\n'.join(posts))
            except TypeError:
                continue

        prediction = list(map(itemgetter(0),
                              self.predictor.predict(texts)[:3]))

        user_status = self.get_user(from_id, users_session)
        user_status.subjects = '&'.join(prediction)
        user_status.status = 'show_page'
        user_status.page = 1
        users_session.commit()

        message = 'В ходе анализа было выявлено, что вас ' \
                  'интересуют следующие категории групп:\n'
        message += '\n'.join([f'{i}. {category.capitalize()}'
                              for i, category in enumerate(prediction, 1)])

        self.send_message(from_id, message)

        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('Начать анализ повторно',
                            color=VkKeyboardColor.SECONDARY,
                            payload=json.dumps(
                                {'button': 'start_analysis'}))

        group_ids = groups_session.query(self.groups_db.Groups).filter(
            or_(self.groups_db.Groups.subject == prediction[0],
                self.groups_db.Groups.subject == prediction[1],
                self.groups_db.Groups.subject == prediction[2])
        ).all()

        if len(group_ids) > 0:
            show_groups = group_ids[:10]
            message = 'Страница 1:\n'
            message += '\n'.join([
                f'{i + 1}. {show_groups[i].name} -- '
                f'https://vk.com/club{show_groups[i].group_id} '
                for i in range(len(show_groups))
            ])
            page_number = len(group_ids) // 10 + 1

            keyboard.add_line()
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
        else:
            message = "Проанализировать ещё раз?"
        self.send_message(from_id, message, keyboard.get_keyboard())

        self.processing.discard(from_id)

    def command_show_recommendation(self, from_id, payload):
        users_session = self.users_db.create_session()
        groups_session = self.groups_db.create_session()

        page = int(payload['button'].split('_')[2])
        recommendation = self.get_user(from_id, users_session)
        recommendation = recommendation.subjects.split('&')
        group_ids = groups_session.query(self.groups_db.Groups).filter(or_(
            self.groups_db.Groups.subject == recommendation[0],
            self.groups_db.Groups.subject == recommendation[1],
            self.groups_db.Groups.subject == recommendation[2])).all()
        show_groups = group_ids[(page - 1) * 10:page * 10]
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
            group_ids) // 10 + 1
        keyboard.add_button(f'Страница {page_number}',
                            color=VkKeyboardColor.PRIMARY,
                            payload=json.dumps({
                                'button':
                                    f'show_recommendation_{page_number}'
                            }))
        page_number = (page + 1) % (len(group_ids) // 10 + 1)
        page_number = page_number or len(group_ids) // 10 + 1
        keyboard.add_button(f'Страница {page_number}',
                            color=VkKeyboardColor.PRIMARY,
                            payload=json.dumps({
                                'button':
                                    f'show_recommendation_{page_number}'
                            }))
        self.send_message(from_id, message, keyboard.get_keyboard())
        user_status = self.get_user(from_id, users_session)
        user_status.status = 'show_page'
        user_status.page = page
        users_session.commit()

    def command_admin(self, from_id):
        users_session = self.users_db.create_session()
        print(f'*** {from_id} entered admin panel')

        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('Фильтровать датасет',
                            color=VkKeyboardColor.PRIMARY,
                            payload=json.dumps({'button': 'dataset_filter'}))
        keyboard.add_button('Выйти',
                            color=VkKeyboardColor.NEGATIVE,
                            payload=json.dumps({'command': 'start'}))
        msg = 'Вы вошли в панель администратора'
        self.send_message(from_id, msg, keyboard.get_keyboard())

        user_status = self.get_user(from_id, users_session)
        if user_status:
            user_status.status = 'admin'
        else:
            users_session.add(
                self.users_db.UserStatuses(user_id=from_id, status='admin'))
        users_session.commit()

    def command_dataset_filter(self, from_id, payload):
        users_session = self.users_db.create_session()
        groups_session = self.groups_db.create_session()

        user_status = self.get_user(from_id, users_session)
        if user_status.status == 'admin':
            if '#' in payload['button']:
                _, gr_id, cat = payload['button'].split('#')
                gr_id = int(gr_id)
                if gr_id > self.latest_id:
                    self.latest_id = gr_id
                    cat = self.new_cats[int(cat)] if cat != '-1' else 'other'
                    old_group = groups_session.query(
                        self.groups_db.Groups).get(self.latest_id)
                    users_session.add(self.groups_db.Groups(group_id=self.latest_id,
                                                       name=old_group.name,
                                                       subject=cat,
                                                       link=old_group.link))
                    msg = (f"{old_group.name} теперь относится к группе "
                           f"{cat.capitalize()}")
                else:
                    msg = f'Группа {gr_id} уже была добавлена'
                self.send_message(from_id, msg)

            group = groups_session.query(self.groups_db.Groups).order_by(
                self.groups_db.Groups.group_id.asc()
            ).filter(self.groups_db.Groups.group_id > self.latest_id).first()

            keyboard = VkKeyboard(one_time=True)
            msg = ('К какой категории относится эта группа?\n'
                   f'https://vk.com/club{group.group_id}\n\n')
            for i, cat in enumerate(self.new_cats):
                keyboard.add_button(cat.capitalize(),
                                    color=VkKeyboardColor.SECONDARY,
                                    payload=json.dumps({'button': f'dataset_filter#{group.group_id}#{self.new_cats.index(cat)}'}))
                if (i + 1) % 3 == 0:
                    keyboard.add_line()
            if (i + 1) % 3 != 0:
                keyboard.add_line()
            keyboard.add_button('Ни к одной',
                                color=VkKeyboardColor.NEGATIVE,
                                payload=json.dumps({'button': f'dataset_filter#{group.group_id}#-1'}))
            keyboard.add_button('Завершить',
                                color=VkKeyboardColor.NEGATIVE,
                                payload=json.dumps({'command': 'start'}))
            self.send_message(from_id, msg, keyboard.get_keyboard())
        else:
            keyboard = VkKeyboard(one_time=True)
            keyboard.add_button('Начать анализ',
                                color=VkKeyboardColor.POSITIVE,
                                payload=json.dumps(
                                    {'button': 'start_analysis'}))
            msg = 'Начнём анализ?'
            self.send_message(from_id, msg, keyboard.get_keyboard())
    
    def get_user(self, user_id, users_session):
        return users_session.query(self.users_db.UserStatuses).filter(
            self.users_db.UserStatuses.user_id == user_id).first()
