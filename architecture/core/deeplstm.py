import numpy as np
import tensorflow as tf


class DeepLstm(tf.keras.layers.Layer):

    def __init__(self, hidden_units=384, num_lstm=3):
        super(DeepLstm, self).__init__()
        cells = [tf.keras.layers.LSTMCell(hidden_units) for _ in range(num_lstm)]
        self.cell = tf.keras.layers.StackedRNNCells(cells)
        self.rnn = tf.keras.layers.RNN(self.cell)
    
    def get_initial_state(self, x):
        batch_size = tf.shape(x)[0]
        initial_state = self.cell.get_initial_state(batch_size=batch_size, dtype=tf.float32)
        return initial_state

    def call(self, x, initial_state):
        outputs, new_state = self.rnn(x, initial_state=initial_state)
        return outputs, new_state