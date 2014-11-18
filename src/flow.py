from __future__ import division, print_function
from collections import namedtuple
from math import ceil
import heapq
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

        self.num_packets = int(ceil(
            data_mb * 1.0E6 / DataPacket.payload_size))

        self.window = 1

        self._num_out_packets = 0

        self.next_packet = simpy.Store(env)

        env.process(self.make_packet())

    def hello(self):
        yield self.env.event().succeed()
        print('Hello!')

    def make_packet(self):
        yield self.env.timeout(self.start)
        i = 0
        while True:
            packet = DataPacket(self.src, self.dest, self.id, i)
            t1 = self.next_packet.put(packet)
            ret = yield t1 | self.env.event().succeed()
            if t1 not in ret:
                print('Failed to send Packet {0}'.format(i))
            yield self.env.timeout(0.0005)
            i += 1

    def get_ack(self, packet_no):
        # raise NotImplemented()
        print('{:.6f} : {} : Ack {}'.format(
            self.env.now, self.id, packet_no))

class GoBackNAcker(object):
    def __init__(self, env, flow_id):
        self.env = env
        self.id = flow_id
        self._expected = 1
        self._partial = []

    def _get(self, n):
        expected = self._expected
        partial = self._partial

        if n < expected:
            return None
        elif n == expected:
            expected += 1
            while partial:
                if partial[0] < expected:
                    heapq.heappop(partial)
                elif partial[0] == expected:
                    expected += 1
                    heapq.heappop(partial)
                elif partial[0] > expected:
                    break
            self._expected = expected
            return expected

        else:
            heapq.heappush(self._partial, n)
            self._expected = expected
            return expected

    def _put(self, n):
        pass

    def acknowledge(self, packet):
        pass

class TCPTahoeFlow(Flow):
    """docstring for TCPTahoeFlow"""
    pass

        