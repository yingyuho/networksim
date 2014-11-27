from __future__ import division, print_function
from collections import deque, namedtuple
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

        # Transmit window access control
        self._cwnd = 1
        self._cwnd_balance = simpy.Container(env, init=self._cwnd)
        self.allowance = self._cwnd_balance # TODO: remove later
        self._cwnd_debt = 0

        env.process(self._schedule_process())

    @property
    def cwnd(self):
        """Congestion window."""
        return self._cwnd
    @cwnd.setter
    def cwnd(self, value):
        old = self._cwnd

        if value > old:
            diff = value - old
            transfer = min(value - old, self._cwnd_debt)
            if self._cwnd_debt >= diff:
                self._cwnd_debt -= diff
            elif self._cwnd_debt > 0:
                self._cwnd_balance.put(diff - self._cwnd_debt)
                self._cwnd_debt = 0
            else:
                self._cwnd_balance.put(diff)
        elif value < old:
            self._cwnd_debt += old - value

        self._cwnd = value

    def _schedule_process(self):
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
        # All packets with packet_no < expected have been received
        self._expected = first_no
        # Packet numbers not received in order
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
            self.d = (1 - b) * d + b * abs(t - a)

        return self.a + self.n * self.d

class _PktTrack(object):
    def __init__(self, packet_no, timestamp, expiration, acked):
        self.packet_no = packet_no
        self.timestamp = timestamp
        self.expiration = expiration
        self.acked = acked

class TCPTahoeFlow(Flow):
    """docstring for TCPTahoeFlow"""
    def __init__(self, env, flow_id, src_id, dest_id, data_mb, start_s):
        super(TCPTahoeFlow, self).__init__(
            env, flow_id, src_id, dest_id, data_mb, start_s)

        self.timeout = 1.0
        self._timer = ExpDecayTimer()

        self._out_packets = deque()
        self._expected = 1

        self._alarm = None
        self._deadlines = []

    def make_packet(self):
        i0 = self._first_packet
        for i in range(i0, i0 + self.num_packets):
            packet = DataPacket(self.src, self.dest, self.id, i)

            yield self.allowance.get(1)
            yield self.next_packet.put(packet)

            t = self.env.now

            self._out_packets.append(_PktTrack(i, t, t + self.timeout, False))

            heapq.heappush(self._deadlines, (t + self.timeout, i))
            self.set_alarm()

            print('{:.6f} : {} : Dta {}'.format(self.env.now, self.id, i))

    def countdown(self, timeout):
        try:
            yield self.env.timeout(timeout)

            # Alarm expires
            self._alarm = None
            deadlines = self._deadlines
            packet_no = deadlines[0][1]
            pktt = self.find_pkt_tracker(packet_no)
            heapq.heappop(deadlines)

            assert packet_no >= self._expected

            # Half N
            if packet_no == self._expected:
                self.cwnd = max(self.cwnd // 2, 1)

            print('{:06f} : Timeout {}'.format(self.env.now, packet_no))

            self.set_alarm()

            packet = DataPacket(self.src, self.dest, self.id, packet_no)
            self.inc_allowance()
            yield self.allowance.get(1)

            if packet_no >= self._expected:

                yield self.next_packet.put(packet)

                t = self.env.now
                print('{:06f} : Retransmit {}'.format(t, packet_no))

                pktt.timestamp = t
                pktt.expiration = t + self.timeout

                heapq.heappush(deadlines, (pktt.expiration, packet_no))

                self.set_alarm()

        except simpy.Interrupt:
            pass

    def find_pkt_tracker(self, packet_no):
        opkts = self._out_packets
        i = packet_no - self._expected
        if i < 0 or i >= len(opkts):
            return None
        else:
            assert opkts[i].packet_no == packet_no
            return opkts[i]

    def set_alarm(self):
        if (self._alarm is not None) and (not self._alarm.processed):
            self._alarm.interrupt()

        d = self._deadlines
        while d:
            pktt = self.find_pkt_tracker(d[0][1])
            if pktt is None or pktt.acked:
                heapq.heappop(d)
            else:
                break
        if d:
            timeout = d[0][0] - self.env.now
            # print(d[0])
            # print(self.env.now)
            assert timeout >= 0
            self._alarm = self.env.process(self.countdown(timeout))

    def get_ack(self, ack_no):
        packet_no = ack_no - 1
        q = self._out_packets

        if packet_no < self._expected:
            return

        # Locate the packet tracker
        pktt = self.find_pkt_tracker(packet_no)

        # Mark the packet as acked
        pktt.acked = True

        # Update timeout
        delay = self.env.now - pktt.timestamp
        self.timeout = self._timer(delay)

        pdiff = packet_no - self._expected + 1

        # Expect the next packet
        self._expected = packet_no + 1

        # Remove acked packets from queue
        for _ in range(pdiff):
            q.popleft()

        self.inc_allowance(pdiff)

        deadlines = self._deadlines

        # Reset alarm
        self.set_alarm()

        # Increase N
        self.cwnd += 1
        # print('{:.6f} {}'.format(self.env.now, packet_no))
        print('{:.6f} : {} : Ack {}'.format(self.env.now, self.id, packet_no))

class FASTTCP(Flow):
    """docstring for FASTTCP"""
    def __init__(self, env, flow_id, src_id, dest_id, data_mb, start_s):
        super(FASTTCP, self).__init__(
            env, flow_id, src_id, dest_id, data_mb, start_s)

        # minimum RTT
        self.baseRTT = 1

        # current RTT
        self.RTT = 1

        # average RTT
        self.avgRTT

        # window size
        self.window_size = 1
        self.allowance = simpy.Container(env, init=self.window_size)
        self.debt = 0

        # calculated queue delay
        self.queue_delay = 0

        # queue used to check for packet loss. should always be 3 elements
        # long. contains the last three packet numbers
        self._packet_acks = dict()

    def make_packet(self):
        i0 = self._first_packet
        for i in range(i0, i0 + self.num_packets):
            packet = DataPacket(self.src, self.dest, self.id, i)

            yield self.allowance.get(1)
            yield self.next_packet.put(packet)

            t = self.env.now

            self._out_packets.append(_PktTrack(i, t, t + self.timeout, False))

            heapq.heappush(self._deadlines, (t + self.timeout, i))
            self.set_alarm()

            print('{:.6f} : {} : Dta {}'.format(self.env.now, self.id, i))

    def inc_allowance(self, n=1):
        if self.debt >= n:
            self.debt -= n
        elif self.debt > 0:
            self.allowance.put(n - self.debt)
            self.debt = 0
        else:
            self.allowance.put(n)

    def get_ack(self, ack_no):
        packet_no = ack_no - 1
        pktt = self.find_pkt_tracker(packet_no)

        # add packet acknowledgement to dictionary
        if packet_no in self._packet_acks.keys():
            self._packet_acks[packet_no] = self._packet_acks[packet_no] + 1
        else
            self._packet_acks[packet_no] = 1

        # Check if positive or negative ack
        # Negative ack
        if self._packet_acks[packet_no] == 3:
            packet = DataPacket(self.src, self.dest, self.id, packet_no)

            yield self.allowance.get(1)
            yield self.next_packet.put(packet)

            t = self.env.now
            print('{:06f} : Retransmit {}'.format(t, packet_no))

            pktt.timestamp = t
            pktt.expiration = t + self.timeout
        
        # Positive ack
        else
            self.RTT = self.env.now - pktt.timestamp
            if self.RTT < self.baseRTT:
                self.baseRTT = self.RTT
            weight = min(3/self.window_size, 1/4)
            self.avgRTT = (1 - weight * self.avgRTT + weight * self.RTT)
            self.queue_delay = self.avgRTT - self.baseRTT

            # Window control
            gamma = .5
            alpha = 1
            self.window_size = min(2 * self.window_size, 
                (1 - gamma)*self.window_size + gamma(self.baseRTT/self.RTT * self.window_size + alpha))
            inc_allowance(self, self.window_size)

