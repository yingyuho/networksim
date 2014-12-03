from __future__ import division, print_function
from collections import deque, namedtuple
from math import ceil
import heapq

import simpy

from packet import DataPacket, AckPacket

class PacketInfo(object):
    def __init__(self, packet_no, timestamp, expiration, acked):
        self.packet_no = packet_no
        self.timestamp = timestamp
        self.expiration = expiration
        self.acked = acked

_PktTrack = PacketInfo

class SlidingWindow(object):

    def __init__(self, first_packet=1):
        self._offset = first_packet
        self._queue = deque()

    @property
    def offset(self):
        return self._offset
    @offset.setter
    def offset(self, value):
        i = value - self._offset
        s = len(self._queue)
        if i < 0:
            raise ValueError('cannot slide back')

        if i < s:
            for _ in xrange(i):
                self._queue.popleft()
        else:
            self._queue.clear()

        self._offset = value
    
    def __getitem__(self, i):
        j = i - self._offset
        s = len(self._queue)
        if 0 <= j and j < s:
            return self._queue[i - self.offset]
        else:
            return None

    def __setitem__(self, i, x):
        j = i - self._offset
        s = len(self._queue)
        if 0 <= j and j < s:
            self._queue[j] = x
        elif j == s:
            self._queue.append(x)
        else:
            raise IndexError('packet number not in window')

class FlowState(object):

    def __init__(self, context, name):
        self.name = name
        self.context = context

    def event_timeout(self, packet_no):
        raise NotImplementedError()

    def event_dupack(self, packet_no, ndup):
        raise NotImplementedError()

    def event_ack(self, packet_no):
        raise NotImplementedError()

class BaseFlow(object):

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
        self._ret_packets = deque()

        # Transmit window access control
        self._window = SlidingWindow()
        self._cwnd = 1
        self._cwnd_balance = simpy.Container(env, init=self._cwnd)
        self._cwnd_debt = 0

        # Activate main process
        self.env.process(self.proc_next_packet())

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

    def make_packet(self, packet_no):
        return DataPacket(self.src, self.dest, self.id, packet_no)

    def proc_next_packet(self):
        yield self.env.timeout(self.start)

        i = self._first_packet
        end = i + self.num_packets

        while True:
            yield self.allowance.get(1)

            if self._ret_packets:
                j = self._ret_packets.popleft()
            elif i < end:
                j = i
                i += 1
            else:
                break

            packet = make_packet(i)

            yield self.next_packet.put(packet)

            t = self.env.now

            self._out_packets[i] = _PktTrack(i, t, t + self.timeout, False)

            heapq.heappush(self._deadlines, (t + self.timeout, i))

            self.set_alarm()

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
        self._out_packets = SlidingWindow()
        self._cwnd = 1
        self._cwnd_balance = simpy.Container(env, init=self._cwnd)
        self.allowance = self._cwnd_balance # TODO: remove later
        self._cwnd_debt = 0

        # TODO: classify these things
        self.ssthresh = None
        self.timeout = 1.0
        self._timer = ExpDecayTimer()

        self._alarm = None
        self._deadlines = []

        # Different flow control states
        self._allowed_states = ['ss', 'ca', 'fr']
        self.state = 'ss'

        env.process(self._start_process())

    @property
    def state(self):
        """Flow control states. Allowed values are
            'ss': Slow Start.
            'ca': Congestion Avoidance.
            'fr': Fast Retransmit/Fast Recovery.
        """
        return self._state
    @state.setter
    def state(self, value):
        allowed = self._allowed_states
        if any(value == s for s in allowed):
            self._state = value
        else:
            raise ValueError(
                'Allowed states are \'{}\''.format('\', \''.join(allowed)))

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

    def inc_balance(self, n=1):
        if self._cwnd_debt >= n:
            self._cwnd_debt -= n
        elif self._cwnd_debt > 0:
            self._cwnd_balance.put(n - self._cwnd_debt)
            self._cwnd_debt = 0
        else:
            self._cwnd_balance.put(n)

    def _start_process(self):
        yield self.env.timeout(self.start)
        self.env.process(self.make_packet())

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

class TCPTahoeFlow(Flow):
    """docstring for TCPTahoeFlow"""
    def __init__(self, env, flow_id, src_id, dest_id, data_mb, start_s):
        super(TCPTahoeFlow, self).__init__(
            env, flow_id, src_id, dest_id, data_mb, start_s)

    def make_packet(self):
        i0 = self._first_packet
        for i in range(i0, i0 + self.num_packets):
            packet = DataPacket(self.src, self.dest, self.id, i)

            yield self.allowance.get(1)
            yield self.next_packet.put(packet)

            t = self.env.now

            self._out_packets[i] = _PktTrack(i, t, t + self.timeout, False)

            heapq.heappush(self._deadlines, (t + self.timeout, i))
            self.set_alarm()

            # print('{:.6f} : {} : Dta {}'.format(self.env.now, self.id, i))

    def countdown(self, timeout):
        try:
            yield self.env.timeout(timeout)

            # Alarm expires
            self._alarm = None
            deadlines = self._deadlines
            packet_no = deadlines[0][1]
            pktt = self._out_packets[packet_no]
            assert pktt.packet_no == packet_no

            assert packet_no >= self._out_packets.offset
            heapq.heappop(deadlines)

            # Half N
            if packet_no == self._out_packets.offset:
                self.cwnd = max(self.cwnd // 2, 1)

            print('{:06f} timeout {}'.format(self.env.now, packet_no))

            self.set_alarm()

            packet = DataPacket(self.src, self.dest, self.id, packet_no)
            self.inc_balance()
            yield self.allowance.get(1)

            if packet_no >= self._out_packets.offset:

                yield self.next_packet.put(packet)

                t = self.env.now
                print('{:06f} retransmit {}'.format(t, packet_no))

                pktt.timestamp = t
                pktt.expiration = t + self.timeout

                heapq.heappush(deadlines, (pktt.expiration, packet_no))

                self.set_alarm()

        except simpy.Interrupt:
            pass

    def set_alarm(self):
        if (self._alarm is not None) and (not self._alarm.processed):
            self._alarm.interrupt()

        d = self._deadlines
        while d:
            pktt = self._out_packets[d[0][1]]
            if pktt:
                assert pktt.packet_no == d[0][1]
            if pktt is None or pktt.acked:
                heapq.heappop(d)
            else:
                break
        if d:
            timeout = d[0][0] - self.env.now
            assert timeout >= 0
            self._alarm = self.env.process(self.countdown(timeout))

    def get_ack(self, ack_no):
        packet_no = ack_no - 1
        q = self._out_packets

        expected = self._out_packets.offset

        if packet_no < expected:
            return

        # Locate the packet tracker
        pktt = q[packet_no]
        assert pktt.packet_no == packet_no

        # Mark the packet as acked
        pktt.acked = True

        # Update timeout
        delay = self.env.now - pktt.timestamp
        self.timeout = self._timer(delay)

        pdiff = packet_no - expected + 1

        # Remove acked packets from queue
        q.offset += pdiff

        self.inc_balance(pdiff)

        # Reset alarm
        self.set_alarm()

        # Increase N
        self.cwnd += 1
        # print('{:.6f} ack {}'.format(self.env.now, self.id, packet_no))

class FASTTCP(TCPTahoeFlow):
    """docstring for FASTTCP"""
    def __init__(self, env, flow_id, src_id, dest_id, data_mb, start_s):
        super(FASTTCP, self).__init__(
            env, flow_id, src_id, dest_id, data_mb, start_s)

        # minimum RTT
        self.baseRTT = 1

        # current RTT
        self.RTT = 1

        # average RTT
        self.avgRTT = None

        # window size
        self._cwnd = 1
        self.allowance = simpy.Container(env, init=self._cwnd)
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

    def get_ack(self, ack_no):
        packet_no = ack_no - 1
        pktt = self.find_pkt_tracker(packet_no)

        # add packet acknowledgement to dictionary
        if packet_no in self._packet_acks.keys():
            self._packet_acks[packet_no] = self._packet_acks[packet_no] + 1
        else:
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
        else:
            self.RTT = self.env.now - pktt.timestamp
            if self.RTT < self.baseRTT:
                self.baseRTT = self.RTT
            weight = min(3/self._cwnd, 1/4)
            self.avgRTT = (1 - weight * self.avgRTT + weight * self.RTT)
            self.queue_delay = self.avgRTT - self.baseRTT

            # Window control
            gamma = .5
            alpha = 1
            wind_size = min(2 * self._cwnd, 
                (1 - gamma)*self._cwnd + gamma(self.baseRTT/self.RTT * self._cwnd + alpha))
            self.cwnd(self, wind_size)

