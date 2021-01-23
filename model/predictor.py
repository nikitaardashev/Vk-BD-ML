import os
from tensorflow.keras import Sequential, layers, models, losses, metrics
from tensorflow.keras.layers.experimental.preprocessing import (
        TextVectorization)


class Predictor:
    def __init__(self, model_path):
        self.model = None
        self.load_model(model_path)

        self.class_names = []
        with open(os.path.join(model_path, 'class_names.txt'), 'r') as f:
            for line in f.readlines():
                self.class_names.append(line.rstrip())

    def predict(self, text_list):
        """return list of class predictions based on list of strings"""
        if isinstance(text_list, str):
            text_list = [text_list]
        return [self.class_names[list(pr).index(max(pr))]
                for pr in self.model.predict(text_list)]

    def load_model(self, model_path):
        ckpt = os.path.join(model_path, 'checkpoint')
        if os.path.isfile(ckpt):
            vectorize_layer = TextVectorization(
                max_tokens=20000,
                output_mode='int',
                output_sequence_length=40)

            # ATTENTION: this model MUST be absolutely
            # identical to the original one
            self.model = Sequential([vectorize_layer, Sequential([
                layers.Embedding(20001, 160),
                layers.Dropout(0.3),
                layers.GlobalAveragePooling1D(),
                layers.Dropout(0.3),
                layers.Dense(40)])])
            self.model.load_weights('weights/checkpoint')
        else:
            self.model = models.load_model(model_path)


if __name__ == '__main__':
    p1 = Predictor('weights')
    print(p1.predict(['лингвистика', 'олег', 'физика', 'программирование']))

    p2 = Predictor('export_model')
    print(p2.predict(['лингвистика', 'олег', 'физика', 'программирование']))
