import requests
from bs4 import BeautifulSoup
from model.cleaner import Cleaner


def get_referat(category):
    r = requests.get(f'https://yandex.ru/referats/?t={category}')
    soup = BeautifulSoup(r.text, 'html.parser')
    text = soup.find('div', {'class': 'referats__text'}).findChildren('p')
    return ' '.join(i.text for i in text)


def yandex_referats_to_ds(count=10):
    categories = [
        'astronomy',
        'geology',
        'gyroscope',
        'literature',
        'marketing',
        'mathematics',
        'music',
        'polit',
        'agrobiologia',
        'law',
        'psychology',
        'geography',
        'physics',
        'philosophy',
        'chemistry',
        'estetica'
    ]

    c = Cleaner()

    with open('data/ds2/ds_info.txt', 'w', encoding='utf-8') as f:
        f.write(f"{','.join(categories)}\n{len(categories) * count}")

    with open('data/ds2/dataset.csv', 'w', encoding='utf-8') as f:
        for i, cat in enumerate(categories):
            text = ''
            for j in range(count):
                print(f'\r{cat.ljust(20, " ")}'
                      f'({i + 1}/{len(categories)})\t'
                      f'({j + 1}/{count})', end='')
                text += f'{c.clean_text(get_referat(cat))},{i}\n'
            print()
            f.write(text)
