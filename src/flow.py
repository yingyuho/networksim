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
        self.start = float(start_s)

        self.next_packet = simpy.Store(env, capacity=5)

        env.process(self.test_run())

    def hello(self):
        yield self.env.event().succeed()
        print('Hello!')

    def test_run(self):
        self.env.timeout(self.start)
        i = 0
        while True:
            packet = DataPacket(self.src, self.dest, i)
            t1 = self.next_packet.put(packet)
            ret = yield t1 | self.env.event().succeed()
            if t1 not in ret:
                print('Failed to send Packet {0}'.format(i))
            yield self.env.timeout(1)
            i += 1