import csv
import vk_api

from database import db_session
from database.models.GroupsIds import GroupsIds


def fill_groups_db_from_csv(csv_path: str = 'data/obrazovanie_2.csv'):
    service_token = '5c0ff5695c0ff5695c0ff569145c7b34f055c0f5c0ff56903ac3c08de3d59cf69e6645b'  # сервисный ключ доступа (из приложения)
    app_id = 7651737  # ID приложения
    client_secret = 'yeRqPtdVKHU4bEJug1aX'  # защищённый ключ (из приложения)
    service_session = vk_api.VkApi(app_id=app_id, token=service_token, client_secret=client_secret)
    api = service_session.get_api()
    session = db_session.create_session()
    with open(csv_path, encoding='utf-8-sig') as file:
        csv_file = csv.reader(file, delimiter=';', )
        for i, row in enumerate(csv_file):
            if int(row[0]) <= 20591965:
                continue
            group = session.query(GroupsIds).filter(GroupsIds.group_id == int(row[0])).first()
            if group:
                continue
            info = api.groups.getById(group_id=int(row[0]))[0]
            session.add(GroupsIds(group_id=int(row[0]), name=info['name'], subject=row[2], link=info['screen_name']))
            print(f'adding: id = {row[0]}, name = {info["name"]}, subject = {row[2]}, link = {info["screen_name"]}')
            if i % 100 == 0:
                session.commit()
                print(f'{i}: commit completed')
    session.commit()
