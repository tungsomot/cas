##########################################################################################
# Author: Jared L. Ostmeyer
# Date Started: 2017-04-11
# Purpose: Recurrent weighted average cell for tensorflow.
# License: See LICENSE
##########################################################################################

"""Module implementing RWA cells with customizable attention spans.

This module provides an implementation of a recurrent weighted average (RWA)
model (https://arxiv.org/abs/1703.01253). The RWACell extends the `RNNCell`
class to create a model that conforms with the recurrent neural network
framework in TensorFlow.

The initial state of the RWA model is defined by a set of parameters that
must be learned. In this implementation, the initial state is zero. The
initial state can be parameterized and passed through the `initial_state`
in `dynamic_rnn` to match the published model.
"""

import tensorflow as tf


class RWACell(tf.contrib.rnn.RNNCell):
	"""Recurrent weighted averge cell (https://arxiv.org/abs/1703.01253)"""

	def __init__(self, num_units, decay_rate=0.0):
		"""Initialize the RWA cell.
		Args:
			num_units: int, The number of units in the RWA cell.
			decay_rate: (optional) If this is a float it sets the
				decay rate for every unit. If this is a list or
				tensor of shape `[num_units]` it sets the decay
				rate for each individual unit. The decay rate is
				defined as `ln(2.0)/hl` where `hl` is the desired
				half-life of the memory.
		"""
		self.num_units = num_units
		self.activation = tf.nn.tanh
		if type(decay_rate) is not tf.Variable:
			decay_rate = tf.constant(decay_rate)
		self.decay_rate = decay_rate

	def __call__(self, inputs, state, scope='RWACell'):
		num_inputs = inputs.get_shape()[1]
		num_units = self.num_units
		activation = self.activation
		decay_rate = self.decay_rate
		x = inputs
		n, d, h, a_max = state

		with tf.variable_scope(scope):
			W_u = tf.get_variable('W_u', [num_inputs, num_units], initializer=tf.contrib.layers.xavier_initializer())
			b_u = tf.get_variable('b_u', [num_units], initializer=tf.constant_initializer(0.0))
			W_g = tf.get_variable('W_g', [num_inputs+num_units, num_units], initializer=tf.contrib.layers.xavier_initializer())
			b_g = tf.get_variable('b_g', [num_units], initializer=tf.constant_initializer(0.0))
			W_a = tf.get_variable('W_a', [num_inputs+num_units, num_units], initializer=tf.contrib.layers.xavier_initializer())

		xh = tf.concat([x, h], 1)

		u = tf.matmul(x, W_u)+b_u
		g = tf.matmul(xh, W_g)+b_g
		a = tf.matmul(xh, W_a)     # The bias term when factored out of the numerator and denominator cancels and is unnecessary
		z = tf.multiply(u, tf.nn.tanh(g))

		a_decay = a_max-decay_rate
		n_decay = tf.multiply(n, tf.exp(-decay_rate))
		d_decay = tf.multiply(d, tf.exp(-decay_rate))

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

