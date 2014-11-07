from __future__ import division, print_function
import simpy
from packet import DataPacket, AckPacket

class Flow(object):
    def __init__(self, env, flow_id, src_id, dest_id, data_mb, start_s):
        self.env = env
        self.id = flow_id
        self.src = src_id
        self.dest = dest_id
        self.data = data_mb
        self.start = start_s

        self.next_packet = simpy.Store(env, capacity=1)

        env.process(self.test_run())

    def test_run(self):
        i = 0
        while True:
            packet = DataPacket(self.src, self.dest, i)
            yield self.next_packet.put(packet)
            yield self.env.timeout(1)
            i += 1