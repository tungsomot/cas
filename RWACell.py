##########################################################################################
# Author: Jared L. Ostmeyer
# Date Started: 2017-04-11
# Purpose: Recurrent weighted cverage cell for tensorflow.
# License: See LICENSE
##########################################################################################

import tensorflow as tf

class RWACell(tf.contrib.rnn.RNNCell):

	def __init__(self, num_units, decay=None):
		self.num_units = num_units
		self.activation = tf.nn.tanh
		if decay is None:
			self.decay = 1.0
		else:
			self.decay = decay

	def zero_state(self, batch_size, dtype):
		num_units = self.num_units

		n = tf.zeros([batch_size, num_units], dtype=dtype)
		d = tf.zeros([batch_size, num_units], dtype=dtype)
		h = tf.zeros([batch_size, num_units], dtype=dtype)
		a_max = tf.fill([batch_size, num_units], -1E25)	# Start off with a tiny number with room for this value to decay

		return (n, d, h, a_max)

	def __call__(self, inputs, state, scope='RWACell'):
		num_inputs = inputs.get_shape()[1]
		num_units = self.num_units
		activation = self.activation
		decay = self.decay
		x = inputs
		n, d, h, a_max = state

		def load_params():
			return (
				tf.get_variable('W_u', [num_inputs, num_units], initializer=tf.contrib.layers.xavier_initializer()),
				tf.get_variable('b_u', [num_units], initializer=tf.constant_initializer(0.0)),
				tf.get_variable('W_g', [num_inputs+num_units, num_units], initializer=tf.contrib.layers.xavier_initializer()),
				tf.get_variable('b_g', [num_units], initializer=tf.constant_initializer(0.0)),
				tf.get_variable('W_a', [num_inputs+num_units, num_units], initializer=tf.contrib.layers.xavier_initializer())
			)
		try:
			with tf.variable_scope(scope, reuse=True):
				W_u, b_u, W_g, b_g, W_a = load_params()
		except ValueError:
			with tf.variable_scope(scope):
				W_u, b_u, W_g, b_g, W_a = load_params()
				s = tf.get_variable('s', [num_units], initializer=tf.random_normal_initializer(stddev=1.0))
				h += activation(tf.expand_dims(s, 0))

		xh = tf.concat([x, h], 1)

		u = tf.matmul(x, W_u)+b_u
		g = tf.matmul(xh, W_g)+b_g
		a = tf.matmul(xh, W_a)     # The bias term when factored out of the numerator and denominator cancels and is unnecessary
		z = tf.multiply(u, tf.nn.tanh(g))

		a_decay = a_max+tf.log(decay)
		n_decay = tf.multiply(n, decay)
		d_decay = tf.multiply(d, decay)

		a_newmax = tf.maximum(a_decay, a)
		exp_diff = tf.exp(a_max-a_newmax)
		exp_scaled = tf.exp(a-a_newmax)
		n = tf.multiply(n_decay, exp_diff)+tf.multiply(z, exp_scaled)	# Numerically stable update of numerator
		d = tf.multiply(d_decay, exp_diff)+exp_scaled	# Numerically stable update of denominator
		h = activation(tf.div(n, d))
		a_max = a_newmax

		return h, (n, d, h, a_max)

	@property
	def output_size(self):
		return self.num_units

	@property
	def state_size(self):
		return (self.num_units, self.num_units, self.num_units, self.num_units)
