from __future__ import division, print_function
from collections import namedtuple, deque
from math import ceil
import heapq
import simpy
from packet import DataPacket, AckPacket

class Flow(object):

    _first_packet = 1

    def __init__(self, env, flow_id, src_id, dest_id, data_mb, start_s):
        self.env = env
        self.id = flow_id
        self.src = src_id
        self.dest = dest_id
        self.data = data_mb
        self.start = start_s

        self.num_packets = int(ceil(
            data_mb * 1.0E6 / DataPacket.payload_size))

        self.next_packet = simpy.Store(env)

        env.process(self._schedule())

    def _schedule(self):
        yield self.env.timeout(self.start)
        self.env.process(self.make_packet())

    def hello(self):
        yield self.env.event().succeed()
        print('Hello!')

    def make_packet(self):
        i = self._first_packet
        while True:
            packet = DataPacket(self.src, self.dest, self.id, i)
            yield self.next_packet.put(packet)
            yield self.env.timeout(0.0005)
            i += 1

    def get_ack(self, packet_no):
        # raise NotImplemented()
        print('{:.6f} : {} : Ack {}'.format(
            self.env.now, self.id, packet_no))

class GoBackNAcker(object):
    """Used by the client-side of flow to find the ack number.
    """
    def __init__(self, first_no=1):
        self._expected = first_no
        self._partial = []

    def __call__(self, n):
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

class ExpDecayTimer(object):
    """Compute timeout according to round-trip delay.
    """
    def __init__(self, b=0.1, n=4):
        self.b = b
        self.n = n
        self.a = None
        self.d = None

    def __call__(self, t):
        a = self.a
        d = self.d
        b = self.b

        if a is None:
            self.a = self.d = t
        else:
            self.a = (1 - b) * a + b * t
            self.d = (1 - b) * d + b * (t - a)

        return self.a + self.n * self.d

class TCPTahoeFlow(Flow):
    """docstring for TCPTahoeFlow"""
    def __init__(self, env, flow_id, src_id, dest_id, data_mb, start_s):
        super(AckPacket, self).__init__(
            env, flow_id, src_id, dest_id, data_mb, start_s)

        self.timeout = 0.1
        self._timer = ExpDecayTimer()

        # Max window size
        self.n = 1
        self.n_prev = self.n
        self.window = simpy.Container(env, init=self.n)

    def make_packet(self):
        pass

    def get_ack(self, packet_no):
        pass
