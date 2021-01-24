import os
import re
import pymorphy2
from tensorflow.keras import Sequential, layers
from tensorflow.keras.layers.experimental.preprocessing import (
        TextVectorization)


class Predictor:
    def __init__(self, model_path):
        with open(os.path.join(model_path, 'class_names.txt'),
                  'r', encoding='utf-8') as f:
            self.class_names = [line.rstrip() for line in f.readlines()]

        self.ma = pymorphy2.MorphAnalyzer()

        self.model = None
        self.load_model(model_path)

    def clean_text(self, text):
        text = text.replace('\\', ' ').replace('╚', ' ').replace('╩', ' ')
        text = text.lower()
        text = re.sub(r'http\S+', '', text)
        text = re.sub(r'[^\w\s]', ' ', text)
        text = ' '.join(self.ma.parse(word)[0].normal_form
                        for word in text.split())
        text = ' '.join(word for word in text.split() if len(word) > 3)

        return text

    def predict(self, text_list):
        """return list of class predictions based on list of strings"""
        if isinstance(text_list, str):
            text_list = [text_list]
        if not text_list or text_list == ['']:
            return None
        text_list = [self.clean_text(text) for text in text_list]
        return [self.class_names[list(pr).index(max(pr))]
                for pr in self.model.predict(text_list)]

    def load_model(self, model_path):
        try:
            with open(os.path.join(model_path, 'params.txt'), 'r') as f:
                max_features = int(f.readline())
                sequence_length = int(f.readline())
                embedding_dim = int(f.readline())
        except FileNotFoundError:
            max_features = 20000
            sequence_length = 40
            embedding_dim = 160

        vectorize_layer = TextVectorization(
            max_tokens=max_features,
            output_mode='int',
            output_sequence_length=sequence_length)

        # ATTENTION: this model MUST be absolutely
        # identical to the original one
        self.model = Sequential([vectorize_layer, Sequential([
            layers.Embedding(max_features + 1, embedding_dim),
            layers.Dropout(0.3),
            layers.GlobalAveragePooling1D(),
            layers.Dropout(0.3),
            layers.Dense(len(self.class_names), activation='sigmoid')])])
        self.model.load_weights(os.path.join(model_path, 'checkpoint'))
        self.model.predict(["define", "input", "shape"])


if __name__ == '__main__':
    p = Predictor('weights')
    print(p.predict(['лингвистика', 'олег', 'фИзика', 'программирование']))
