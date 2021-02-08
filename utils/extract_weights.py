from tensorflow.keras.models import load_model

from tensorflow.keras import Sequential, layers
from tensorflow.keras.layers.experimental.preprocessing import (
        TextVectorization)

model = load_model('model/export_model')
model.save_weights('weights/checkpoint')
model.load_weights('weights/checkpoint')

print(model.predict(['лингвистика']))

vectorize_layer = TextVectorization(
    max_tokens=20000,
    output_mode='int',
    output_sequence_length=40)

model = Sequential([vectorize_layer, Sequential([
    layers.Embedding(20001, 160),
    layers.Dropout(0.3),
    layers.GlobalAveragePooling1D(),
    layers.Dropout(0.3),
    layers.Dense(40)])])
model.load_weights('weights/checkpoint')

print(model.predict(['лингвистика']))
