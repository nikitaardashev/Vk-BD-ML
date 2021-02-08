# http://projector.tensorflow.org (Embedding Projector)
# $ tensorboard --logdir logs (to see logs)

import os
import shutil
import io
import tensorflow as tf

from time import time
from tensorflow.keras import layers
from tensorflow.keras.layers.experimental.preprocessing import (
    TextVectorization)


def train_model(ds_name, model_name,
                batch_size=64, max_features=20000, sequence_length=100,
                embedding_dim=160, epochs=10, dropout=0.3, init_lr=0.001):

    logging = False
    export_embedding = True

    val_split = 0.2
    callbacks = [tf.keras.callbacks.EarlyStopping(patience=5)]

    loss_f = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
    metrics = [tf.metrics.SparseCategoricalAccuracy()]

    vectorize_layer = TextVectorization(
        max_tokens=max_features,
        output_mode='int',
        output_sequence_length=sequence_length)

    def vectorize_text(text, cat):
        text = tf.expand_dims(text, -1)
        return vectorize_layer(text), cat

    print(f'Loading "{ds_name}" dataset ...')

    # ds_info.txt:
    #     {cat1},{cat2},{...
    #     {number of rows in dataset.csv}
    with open(f'data/{ds_name}/ds_info.txt', encoding='utf-8') as f:
        class_names = f.readline().rstrip().split(',')
        ds_len = int(f.readline())

    # dataset.csv
    #     {text},{cat_id}
    #     {text},{cat_id}
    #     ...
    ds = tf.data.experimental.CsvDataset(f'data/{ds_name}/dataset.csv',
                                         [str(), int()])
    print('Shuffling dataset ...')
    ds = ds.shuffle(ds_len)

    # ds_len = ds.reduce(int(), lambda x, _: x + 1).numpy()
    train_ds_len = int(ds_len * (1 - val_split))

    raw_train_ds = ds.take(train_ds_len).batch(batch_size)
    raw_val_ds = ds.skip(ds_len - train_ds_len).batch(batch_size)
    raw_test_ds = raw_val_ds


    print("Performing adapt ...")
    train_text = raw_train_ds.map(lambda x, y: x)
    vectorize_layer.adapt(train_text)

    model = tf.keras.Sequential([
        layers.Embedding(max_features + 1, embedding_dim),
        layers.Dropout(dropout),
        layers.GlobalAveragePooling1D(),
        layers.Dropout(dropout),
        layers.Dense(len(class_names))])

    lr_schedule = tf.keras.optimizers.schedules.InverseTimeDecay(
        init_lr,
        decay_steps=int(train_ds_len / batch_size) * 1000,
        decay_rate=1,
        staircase=False)

    def get_optimizer():
        return tf.keras.optimizers.Adam(lr_schedule)

    if logging:
        callbacks.append(tf.keras.callbacks.TensorBoard(log_dir="data/logs"))
        try:
            shutil.rmtree('data/logs')
        except FileNotFoundError:
            pass

    train_ds = raw_train_ds.map(vectorize_text)
    val_ds = raw_val_ds.map(vectorize_text)
    test_ds = raw_test_ds.map(vectorize_text)
    autotune = tf.data.AUTOTUNE
    train_ds = train_ds.cache().prefetch(buffer_size=autotune)
    val_ds = val_ds.cache().prefetch(buffer_size=autotune)
    test_ds = test_ds.cache().prefetch(buffer_size=autotune)

    model.summary()
    model.compile(get_optimizer(), loss_f, metrics)
    begin_time = time()
    model.fit(train_ds, validation_data=val_ds,
              epochs=epochs, callbacks=callbacks)
    end_time = time()
    loss, accuracy = model.evaluate(test_ds)
    print("Loss: ", loss)
    print("Accuracy: ", accuracy)

    export_model = tf.keras.Sequential([vectorize_layer, model])
    export_model.compile(get_optimizer(), loss_f, metrics)
    export_model.predict(['str1', 'str2'])

    exist = os.listdir('models')

    if model_name in exist:
        new_name = model_name + '_1'
        i = 2
        while new_name in exist:
            new_name = model_name + f'_{i}'
            i += 1
        model_name = new_name

    os.mkdir(f'models/{model_name}')

    export_model.save_weights(f'models/{model_name}/checkpoint')

    with open(f'models/{model_name}/params.txt', 'w') as f:
        f.write(f'{max_features}\n')
        f.write(f'{sequence_length}\n')
        f.write(f'{embedding_dim}\n')

    with open(f'models/{model_name}/class_names.txt', 'w') as f:
        f.write(f"{','.join(class_names)}\n")

    if logging:
        with open(f'data/{ds_name}/stat.txt', 'a') as f:
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
        os.mkdir(f'models/{model_name}/embedding')

        weights = model.get_layer('embedding').get_weights()[0]
        vocab = vectorize_layer.get_vocabulary()
        out_v = io.open(f'models/{model_name}/embedding/vectors.tsv',
                        'w', encoding='utf-8')
        out_m = io.open(f'models/{model_name}/embedding/metadata.tsv',
                        'w', encoding='utf-8')
        for index, word in enumerate(vocab):
            if index == 0:
                continue  # skip 0, it's padding.
            vec = weights[index]
            out_v.write('\t'.join([str(x) for x in vec]) + "\n")
            out_m.write(word + "\n")
        out_v.close()
        out_m.close()
