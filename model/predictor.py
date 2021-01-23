import os
from tensorflow.keras import Sequential, layers, models
from tensorflow.keras.layers.experimental.preprocessing import (
        TextVectorization)


class Predictor:
    def __init__(self, model_path):
        self.model = None
        self.class_names = []

        with open(os.path.join(model_path, 'class_names.txt'), 'r') as f:
            for line in f.readlines():
                self.class_names.append(line.rstrip())

        self.load_model(model_path)

    def predict(self, text_list):
        """return list of class predictions based on list of strings"""
        if isinstance(text_list, str):
            text_list = [text_list]
        return [self.class_names[list(pr).index(max(pr))]
                for pr in self.model.predict(text_list)]

    def load_model(self, model_path):
        ckpt = os.path.join(model_path, 'checkpoint')
        if os.path.isfile(ckpt):
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
                layers.Dense(len(self.class_names))])])
            self.model.load_weights(ckpt)
        else:
            self.model = models.load_model(model_path)


if __name__ == '__main__':
    p1 = Predictor('weights')
    print(p1.predict(['лингвистика', 'олег', 'физика', 'программирование']))

    p2 = Predictor('export_model')
    print(p2.predict(['лингвистика', 'олег', 'физика', 'программирование']))
