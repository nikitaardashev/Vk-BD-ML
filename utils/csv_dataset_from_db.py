import csv
import vk_api

from database import db_session
from database.models.GroupsIds import GroupsIds
from utils.cleaner import Cleaner


def csv_dataset_from_db(csv_path: str = 'data/dataset.csv', post_count=1):
    service_token = '5c0ff5695c0ff5695c0ff569145c7b34f055c0f5c0ff56903ac3c08de3d59cf69e6645b'  # сервисный ключ доступа (из приложения)
    app_id = 7651737  # ID приложения
    client_secret = 'yeRqPtdVKHU4bEJug1aX'  # защищённый ключ (из приложения)
    service_session = vk_api.VkApi(app_id=app_id, token=service_token, client_secret=client_secret)
    api = service_session.get_api()

    session = db_session.create_session()
    cleaner = Cleaner()

    with open(csv_path, 'w') as f:
        csv_file = csv.writer(f, delimiter=';')
        csv_file.writerow(['category', 'post'])
        for group in session.query(GroupsIds).order_by(GroupsIds.group_id):
            try:
                posts = api.wall.get(owner_id=-int(group.group_id), count=post_count)
            except vk_api.exceptions.ApiError:
                print(f'Access denied: wall {group.group_id} id disabled')
            else:
                print(f'Posts from group {group.group_id} received')
            for post in posts['items']:
                if not post['marked_as_ads'] and post['text']:
                    csv_file.writerow([group.subject,
                                       cleaner.clean_text(post['text'])])
