import os
import csv
import vk_api

from utils.cleaner import Cleaner


def csv_dataset_from_db(db, post_count=1, max_posts=None):
    app_id = int(os.environ.get('APP_ID'))
    service_token = os.environ.get('SERVICE_TOKEN')
    client_secret = os.environ.get('CLIENT_SECRET')
    service_session = vk_api.VkApi(app_id=app_id, token=service_token,
                                   client_secret=client_secret)
    api = service_session.get_api()

    session = db.create_session()
    cleaner = Cleaner()

    posts_loaded = 0
    class_names = sorted(set([
        cat[0].lower()
        for cat in session.query(db.Groups.subject).distinct(db.Groups.subject)
    ]))

    with open('data/dataset.csv', 'w', encoding='utf-8') as f:
        csv_file = csv.writer(f, delimiter=',')
        groups = session.query(db.Groups).order_by(db.Groups.group_id)
        total = groups.count()
        for i, group in enumerate(groups):
            if isinstance(max_posts, int) and posts_loaded >= max_posts:
                break
            try:
                posts = api.wall.get(owner_id=-int(group.group_id),
                                     count=post_count)
            except vk_api.exceptions.ApiError:
                print(f'\rAccess denied: wall {group.group_id} id disabled')
                continue
            else:
                print(f'\rPosts from group {group.group_id} received')
                if not posts:
                    continue
            for post in posts['items']:
                text = cleaner.clean_text(post['text'])
                if not post['marked_as_ads'] and text:
                    csv_file.writerow([
                        text,
                        class_names.index(group.subject.lower())
                    ])
                    posts_loaded += 1
            print(f'\r[{("#"*int((i + 1) / total * 10)).ljust(10, " ")}] '
                  f'{i + 1} of {total} ({posts_loaded} posts)', end='')

    with open('data/ds_info.txt', 'w', encoding='utf-8') as f:
        f.write(f"{','.join(class_names)}\n")
        f.write(str(posts_loaded))
