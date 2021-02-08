import requests
import csv
import os
import shutil
from time import time

key = ''
count = 1  # Количество постов с каждой стены


def get_posts(owner_id, count, key):
    global error
    owner_id = -abs(int(owner_id))
    try:
        res = requests.get('https://api.vk.com/method/wall.get', {
            'access_token': key,
            'owner_id': owner_id,
            'v': 5.126,
            'count': count
        }, timeout=1).json()

        if "error" in res:
            print(f'\r{res["error"]["error_msg"]} (owner_id: {owner_id}){" " * 20}')
            error += 1

            if res["error"]["error_code"] == 29:
                exit(res["error"]["error_code"])
            else:
                return []

        return res["response"]["items"]
    except requests.exceptions.ReadTimeout:
        error += 1
        return []


error = 0

try:
    shutil.rmtree("dataset")
except FileNotFoundError:
    pass
os.mkdir("dataset")
os.mkdir("dataset/train")
os.mkdir("dataset/test")

try:
    with open('obrazovanie_2.csv', 'r', encoding='utf-8-sig') as f:
        line_total = sum(1 for row in f)
        line_count = 0

    with open('obrazovanie_2.csv', 'r', encoding='utf-8-sig') as csv_file:
        reader = csv.reader(csv_file, delimiter=';')
        written = {}
        print("==================\nDownoading data...")
        print("0% ", end='')
        start_time = time()

        for owner_id, domain, label in reader:
            label = label.lower()
            if label not in written:
                written[label] = 0
                os.mkdir(f'dataset/train/{label}')
            for post in get_posts(owner_id, count, key):
                if not post["marked_as_ads"]:
                    fname = f'dataset/train/{label}/post_{written[label]}.txt'
                    with open(fname, 'w') as f:
                        f.write(post["text"])
                    written[label] += 1

            line_count += 1
            percent = round((line_count / line_total) * 100, 2)
            time_left = (time() - start_time) / percent * 100
            print(f"\r[{('#' * (int(percent) // 10)).ljust(10, ' ')}] "
                  f"{percent}% ({int(time_left) // 60}m left) "
                  f"(Errors: {error}) "
                  f"({line_count}/{line_total})",
                  end='')

        print(f'\r=================={" " * 50}')
        print(f"Successfully loaded {line_count - error} of {line_total} "
              f"(Errors: {error})")
except FileNotFoundError:
    print("csv not found")
