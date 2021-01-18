from random import randint
from typing import List, Union, Dict

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType


class Bot:
    def __init__(self):
        self.group_token = ''  # ключ доступа группы
        self.group_id = 0  # ID группы
        self.service_token = ''  # сервисный ключ доступа (из приложения)
        self.app_id = 0  # ID приложения
        self.client_secret = ''  # защищённый ключ (из приложения)
        self.group_session = vk_api.VkApi(token=self.group_token, api_version='5.126')
        self.service_session = vk_api.VkApi(app_id=self.app_id, token=self.service_token,
                                            client_secret=self.client_secret)
        self.long_poll = VkBotLongPoll(self.group_session, self.group_id)
        self.group_api = self.group_session.get_api()
        self.service_api = self.service_session.get_api()

    def send_message(self, user_id: int, message: str) -> None:
        """
        sends a message to user using method messages.send (https://vk.com/dev/messages.send)
        :param user_id: recipient user ID
        :param message: message text
        :return: None
        """
        self.group_api.messages.send(user_id=user_id,
                                     random_id=randint(0, 2147483647),
                                     message=message)
        print(f'message {message[:15]}{"..." if len(message) > 15 else ""} to {user_id} has been sent')

    def get_posts(self, owner_id: int, count: int = 1) -> Union[List[dict], dict]:
        """
        gets posts from user's or group's wall using method wall.get (https://vk.com/dev/wall.get)
        :param owner_id: wall's owner ID
        :param count: count of posts
        :return: list of dictionaries of dictionary, describing post
        """
        posts = self.service_api.wall.get(owner_id=owner_id, count=count)
        print(f'group {owner_id} posts received')
        return posts['items'] if len(posts['items']) > 1 else posts['items'][0]

    def get_subscriptions(self, user_id: int, extended: bool = False) -> List[int]:
        """
        gets user's subscriptions using method users.getSubscriptions (https://vk.com/dev/users.getSubscriptions)
        :param user_id: user ID
        :param extended: get extended information or not
        :return: list of numbers defining user IDs
        """
        subscriptions = self.service_api.users.getSubscriptions(user_id=user_id, extended=int(extended))
        print(f'received subscriptions from {"user" if user_id > 0 else "group"} {abs(user_id)}')
        return subscriptions['groups']['items']

    def get_group_info(self, group_id: int) -> Union[Dict[str, Union[str, int]], List[Dict[str, Union[str, int]]]]:
        """
        gets information about one or more groups using method groups.getById (https://vk.com/dev/groups.getById)
        :param group_id: group ID
        :return: list of dictionaries of dictionary, describing information about group
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
                subscriptions = self.get_subscriptions(event.object.message['from_id'])
                for i, group_id in enumerate(subscriptions):
                    if i > 10:
                        break
                    group_info = self.get_group_info(group_id)
                    try:
                        group_post = self.get_posts(-group_id)
                        message = f'{group_info["name"]}\n{group_post["text"]}'
                    except vk_api.ApiError:
                        message = f'{group_info["name"]}\nнет доступа'
                    self.send_message(event.object.message['from_id'], message)
                self.send_message(event.object.message['from_id'], 'канец')


if __name__ == '__main__':
    bot = Bot()
    bot.listen()
