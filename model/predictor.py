import os
from tensorflow.keras.models import load_model


class Predictor:
    def __init__(self, model_path):
        self.model = load_model(model_path)
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


if __name__ == '__main__':
    p = Predictor('export_model')
    print(p.predict('олег'))
