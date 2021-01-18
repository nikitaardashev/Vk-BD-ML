# http://projector.tensorflow.org (Embedding Projector)
# $ tensorboard --logdir logs (to see logs)

import os
import shutil
import re
import io
import string
import argparse
import tensorflow as tf

from time import time
from tensorflow.keras import layers
from tensorflow.keras import preprocessing
from tensorflow.keras.layers.experimental.preprocessing import (
    TextVectorization)

parser = argparse.ArgumentParser(description='train model on dataset')
parser.add_argument('-bs', '--batch_size', metavar="N",
                    dest='batch_size', default=64, type=int)
parser.add_argument('-mf', '--max_features', metavar="N",
                    dest='max_features', default=20000, type=int)
parser.add_argument('-sl', '--sequence_length', metavar="N",
                    dest='sequence_length', default=40, type=int)
parser.add_argument('-ed', '--embedding_dim', metavar="N",
                    dest='embedding_dim', default=160, type=int,
                    help="output dimension of embedding layer")
parser.add_argument('-e', '--epochs', metavar="N",
                    dest='epochs', default=10, type=int)
parser.add_argument('ds_path', metavar='PATH', type=str,
                    help='path to dataset')
args = parser.parse_args()
print(args)

logging = False
export_embedding = False

batch_size = args.batch_size
max_features = args.max_features
sequence_length = args.sequence_length
embedding_dim = args.embedding_dim
epochs = args.epochs
seed = 42
val_split = 0.9
ds_path = os.path.abspath(args.ds_path)
callbacks = [tf.keras.callbacks.EarlyStopping(patience=5)]

loss_f = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
metrics = [tf.metrics.SparseCategoricalAccuracy()]

model = tf.keras.Sequential([
    layers.Embedding(max_features + 1, embedding_dim),
    layers.Dropout(0.3),
    layers.GlobalAveragePooling1D(),
    layers.Dropout(0.3),
    layers.Dense(40)])

lr_schedule = tf.keras.optimizers.schedules.InverseTimeDecay(
  0.001,
  decay_steps=int(555372*(1-val_split)/batch_size)*1000,
  decay_rate=1,
  staircase=False)


def get_optimizer():
    return tf.keras.optimizers.Adam(lr_schedule)


vectorize_layer = TextVectorization(
    max_tokens=max_features,
    output_mode='int',
    output_sequence_length=sequence_length)


def vectorize_text(text, label):
    text = tf.expand_dims(text, -1)
    return vectorize_layer(text), label


print(f'Loading dataset from "{ds_path}" ...')
raw_train_ds = preprocessing.text_dataset_from_directory(
    os.path.join(ds_path, 'train'),
    batch_size=batch_size,
    validation_split=val_split,
    subset='training',
    seed=seed)
raw_val_ds = preprocessing.text_dataset_from_directory(
    os.path.join(ds_path, 'train'),
    batch_size=batch_size,
    validation_split=0.01,
    subset='validation',
    seed=seed)
raw_test_ds = raw_val_ds

print("Performing adapt ...")
train_text = raw_train_ds.map(lambda x, y: x)
vectorize_layer.adapt(train_text)

if logging:
    callbacks.append(tf.keras.callbacks.TensorBoard(log_dir="logs"))
    try:
        shutil.rmtree('logs')
    except FileNotFoundError:
        pass

train_ds = raw_train_ds.map(vectorize_text)
val_ds = raw_val_ds.map(vectorize_text)
test_ds = raw_test_ds.map(vectorize_text)
AUTOTUNE = tf.data.AUTOTUNE
train_ds = train_ds.cache().prefetch(buffer_size=AUTOTUNE)
val_ds = val_ds.cache().prefetch(buffer_size=AUTOTUNE)
test_ds = test_ds.cache().prefetch(buffer_size=AUTOTUNE)

model.summary()
model.compile(get_optimizer(), loss_f, metrics)
begin_time = time()
history = model.fit(train_ds, validation_data=val_ds,
                    epochs=epochs, callbacks=callbacks)
end_time = time()
loss, accuracy = model.evaluate(test_ds)
print("Loss: ", loss)
print("Accuracy: ", accuracy)

export_model = tf.keras.Sequential([vectorize_layer, model])
export_model.compile(get_optimizer(), loss_f, metrics)
# Input shape is determined from calling .predict()
export_model.predict(['лингвистика'])
export_model.save('model')
with open('../model/class_names.txt', 'w') as f:
    for label in raw_train_ds.class_names:
        f.write(f'{label}\n')

if logging:
    with open('stat.txt', 'a') as f:
        f.write(f'Loss: {loss}\n'
                f'Accuracy: {accuracy}\n'
                f'batch_size = {batch_size}\n'
                f'max_features = {max_features}\n'
                f'sequence_length = {sequence_length}\n'
                f'embedding_dim = {embedding_dim}\n'
                f'epochs = {epochs}\n'
                f'loss_f: {loss_f}\n'
                f'metrics: {str(metrics)}\n'
                f'Time: {round(end_time - begin_time, 2)}s\n\n')

# Export embedding data for visualisation
if export_embedding:
    try:
        shutil.rmtree('embedding')
    except FileNotFoundError:
        pass
    os.mkdir('embedding')

    weights = model.get_layer('embedding').get_weights()[0]
    vocab = vectorize_layer.get_vocabulary()
    out_v = io.open('embedding/vectors.tsv', 'w', encoding='utf-8')
    out_m = io.open('embedding/metadata.tsv', 'w', encoding='utf-8')
    for index, word in enumerate(vocab):
        if index == 0:
            continue  # skip 0, it's padding.
        vec = weights[index]
        out_v.write('\t'.join([str(x) for x in vec]) + "\n")
        out_m.write(word + "\n")
    out_v.close()
    out_m.close()
