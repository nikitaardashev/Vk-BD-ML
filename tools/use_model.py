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
        if isinstance(text_list, str):
            text_list = [text_list]
        prediction = list(self.model.predict(text_list)[0])
        return self.class_names[prediction.index(max(prediction))]
