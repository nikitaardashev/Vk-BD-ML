import re
import pymorphy2


class Cleaner:
    def __init__(self):
        self.ma = pymorphy2.MorphAnalyzer()

    def clean_text(self, text):
        text = text.replace('\\', ' ').replace('╚', ' ').replace('╩', ' ')
        text = text.lower()
        text = re.sub(r'http\S+', '', text)
        text = re.sub(r'[^\w\s]', ' ', text)
        text = ' '.join(self.ma.parse(word)[0].normal_form
                        for word in text.split())
        text = ' '.join(word for word in text.split() if len(word) > 3)

        return text
