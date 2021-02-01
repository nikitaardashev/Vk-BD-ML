# http://projector.tensorflow.org (Embedding Projector)
# $ tensorboard --logdir logs (to see logs)

if __name__ == '__main__':
    import os
    import shutil
    import io
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
    parser.add_argument('-d', '--dropout', metavar="N",
                        dest='epochs', default=0.3, type=int)
    parser.add_argument('--data_dir', metavar='PATH', default='data', type=str)
    args = parser.parse_args()
    print(args)

    logging = False
    export_embedding = False

    batch_size = args.batch_size
    max_features = args.max_features
    sequence_length = args.sequence_length
    embedding_dim = args.embedding_dim
    epochs = args.epochs
    dropout = 0.3
    seed = 42
    val_split = 0.2
    data_dir = args.data_dir
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


    print(f'Loading dataset from "{os.path.abspath(data_dir)}" ...')

    # Load a csv dataset
    with open(os.path.join(data_dir, 'ds_info.txt'),
              encoding='utf-8') as f:
        class_names = f.readline().rstrip().split(',')
        ds_len = int(f.readline())

    ds = tf.data.experimental.CsvDataset(os.path.join(data_dir, 'dataset.csv'),
                                         [str(), int()])

    # ds_len = ds.reduce(int(), lambda x, _: x + 1).numpy()
    train_ds_len = int(ds_len * (1 - val_split))

    raw_train_ds = ds.take(train_ds_len).batch(batch_size)
    raw_val_ds = ds.skip(ds_len - train_ds_len).batch(batch_size)
    raw_test_ds = raw_val_ds

    # #  Load dataset like in tutorial
    # raw_train_ds = preprocessing.text_dataset_from_directory(
    #     os.path.join(data_dir, 'train'),
    #     batch_size=batch_size,
    #     validation_split=val_split,
    #     subset='training',
    #     seed=seed)
    # train_ds_len = raw_train_ds.cardinality().numpy() * batch_size
    # class_names = raw_train_ds.class_names
    # raw_val_ds = preprocessing.text_dataset_from_directory(
    #     os.path.join(data_dir, 'train'),
    #     batch_size=batch_size,
    #     validation_split=val_split,
    #     subset='validation',
    #     seed=seed)
    # raw_test_ds = raw_val_ds

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
        0.001,
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
    export_model.save_weights('model/weights/checkpoint')

    with open('model/weights/params.txt', 'w') as f:
        f.write(f'{max_features}\n')
        f.write(f'{sequence_length}\n')
        f.write(f'{embedding_dim}\n')

    with open('model/weights/class_names.txt', 'w') as f:
        f.write(f"{','.join(class_names)}\n")

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
            shutil.rmtree('data/embedding')
        except FileNotFoundError:
            pass
        os.mkdir('data/embedding')

        weights = model.get_layer('embedding').get_weights()[0]
        vocab = vectorize_layer.get_vocabulary()
        out_v = io.open('data/embedding/vectors.tsv', 'w', encoding='utf-8')
        out_m = io.open('data/embedding/metadata.tsv', 'w', encoding='utf-8')
        for index, word in enumerate(vocab):
            if index == 0:
                continue  # skip 0, it's padding.
            vec = weights[index]
            out_v.write('\t'.join([str(x) for x in vec]) + "\n")
            out_m.write(word + "\n")
        out_v.close()
        out_m.close()
