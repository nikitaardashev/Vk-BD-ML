from random import randint

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

    def listen(self):
        for event in self.long_poll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                subscriptions = self.service_api.users.getSubscriptions(user_id=event.object.message['from_id'],
                                                                        extended=0)
                for group_id in subscriptions['groups']['items']:
                    group_info = self.service_api.groups.getById(group_id=group_id)
                    try:
                        group_post = self.service_api.wall.get(owner_id=-group_id, count=1)
                        message = f'{group_info[0]["name"]}\n{group_post["items"][0]["text"]}'
                    except vk_api.ApiError:
                        message = f'{group_info[0]["name"]}\nнет доступа'
                    self.group_api.messages.send(user_id=event.object.message['from_id'],
                                                 random_id=randint(0, 2147483647),
                                                 peer_id=event.object.message['peer_id'],
                                                 message=message)
                self.group_api.messages.send(user_id=event.object.message['from_id'],
                                             random_id=randint(0, 2147483647),
                                             peer_id=event.object.message['peer_id'],
                                             message='канец')


if __name__ == '__main__':
    bot = Bot()
    bot.listen()
