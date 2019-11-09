import numpy as np
import tensorflow as tf

from core.deeplstm import DeepLstm
from core.deepmlp import DeepMlp
from core.glu import Glu
from entity_encoder.model_utils import get_padding_bias
from entity_encoder.transformer import Transformer, Transformer_layer
from scalar_encoder.embedding_layer import Embedding_layer


class Pulsar(tf.keras.Model):

    def __init__(self, training):
        super(Pulsar, self).__init__()
        self.training = training
        with tf.name_scope("scalar_encoder"):
            self.match_time_encoder = Embedding_layer(num_units=64)
        with tf.name_scope("entity_encoder"):
            self.transformer = Transformer(num_trans_layers=3, hidden_size=256, num_heads=2,
                                           attention_dropout=0.5, hidden_layer_size=1024,
                                           train=True)
        with tf.name_scope("core"):
            self.deeplstm = DeepLstm(hidden_units=384, num_lstm=3)
        with tf.name_scope("embedding_1"):
            mlp_1_units = 256
            self.deepmlp_1 = DeepMlp(num_units=mlp_1_units, num_layers=5)
            self.glu_1 = Glu(input_size=mlp_1_units, output_size=512)
        with tf.name_scope("embedding_2"):
            self.lstm_projection = tf.keras.layers.Dense(mlp_1_units, activation=tf.nn.relu, name="lstm_projection")
            self.deepmlp_2 = DeepMlp(num_units=256, num_layers=3)
            self.attention = Transformer_layer(hidden_size=256, num_heads=2, attention_dropout=0.5,
                                               hidden_layer_size=1024, train=training)
    
    def call(self, scalar_features, entities, entity_masks, state=None):
        """
        Foward-pass neural network Pulsar.

        Args:
            scalar_features: dict of each scalar features. dict should include
                'match_time' : seconds. Required shape = [batch, 1]
            entities: array of entities. Required shape = [batch_size, n_entities, feature_size]
            entity_masks: mask for entities. Required shape = [batch_size, n_entities]
            state: previous lstm state. None for initial state.

        Returns:
            new_state: the new deep lstm state
        """
        with tf.name_scope("scalar_encoder"):
            encoded_match_time = self.match_time_encoder(scalar_features['match_time'])
            embedded_scalar = tf.concat([encoded_match_time], axis=-1)
            scalar_context = tf.concat([encoded_match_time], axis=-1)
        with tf.name_scope("entity_encoder"):
            bias = get_padding_bias(entity_masks)
            entity_embeddings, embedded_entity = self.transformer(entities, bias)
        with tf.name_scope("core"):
            core_input = tf.concat([embedded_entity, embedded_scalar], axis=-1)
            if state == None:
                state = self.deeplstm.get_initial_state(core_input)
            core_output, new_state = self.deeplstm(core_input, state)
        with tf.name_scope("embedding_1"):
            embedding_1 = self.deepmlp_1(core_output, self.training)
            action_xyvel_layer = self.glu_1(embedding_1, scalar_context)
        with tf.name_scope("embedding_2"):
            core_projection = self.lstm_projection(core_output)
            auto_regressive_embedding = core_projection + embedding_1
            embedding_2 = self.deepmlp_2(auto_regressive_embedding, self.training)
            embedding_2 = tf.expand_dims(embedding_2, axis=1)
            attention_input = tf.concat([embedding_2, entity_embeddings], axis=1)
            action_yaw_layer = self.attention(attention_input, 0)
        
        return action_xyvel_layer, action_yaw_layer
