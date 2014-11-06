from __future__ import division, print_function
import simpy

class Flow(object):
	def __init__(self, env, flow_id, src_id, dest_id, data_mb, start_s):
		self.env = env
		self.id = flow_id
		self.src = src_id
		self.dest = dest_id
		self.data = data_mb
		self.start = start_s