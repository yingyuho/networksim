from __future__ import division, print_function
from collections import deque, namedtuple
from math import ceil
import heapq

import simpy

from packet import DataPacket, AckPacket

class PacketRecord(object):
    def __init__(
        self, packet_no, timestamp, expiration, 
        acked=False, retransmit=False
    ):
        self.packet_no = packet_no
        self.timestamp = timestamp
        self.expiration = expiration
        self.acked = acked
        self.retransmit = retransmit

_PktTrack = PacketRecord

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
            print((i, j, self._offset, [p.packet_no for p in self._queue]))
            raise IndexError('packet number not in window')

class BaseFlow(object):

    _first_packet = 1

    def __init__(
        self, env, flow_id, src_id, dest_id, data_mb, start_s, 
        state_constr, init_state):
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
        self.window = SlidingWindow()
        self._cwnd = 1
        self._cwnd_balance = simpy.Container(env, init=self._cwnd)
        self._cwnd_debt = 0

        # Timeout
        self.timeout = 1.0
        self._timer = ExpDecayTimer()
        self._alarm = None
        self._deadlines = []
        self._last_ss = 0.0

        # Dup ack counter
        self.last_pkinfo = None
        self._ndup = 0

        # State
        self.ssthresh = None
        self._state_constr = state_constr
        self.state = init_state

        # Activate main process
        self.env.process(self.proc_next_packet())

    @property
    def state(self):
        if self._state is not None:
            return self._state.name
        else:
            return None
    @state.setter
    def state(self, value):
        self._state = self._state_constr[value](self, value)
        print('{:.6f} state {} {}'.format(
            self.env.now, self.id, value))
    
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
            self._cwnd_debt += (old - value)

        self._cwnd = value
        print('{:.6f} window_size {} {}'.format(
            self.env.now, self.id, value))

    def inc_balance(self, n=1):
        if self._cwnd_debt >= n:
            self._cwnd_debt -= n
        elif self._cwnd_debt > 0:
            self._cwnd_balance.put(n - self._cwnd_debt)
            self._cwnd_debt = 0
        else:
            self._cwnd_balance.put(n)

    def make_packet(self, packet_no):
        return DataPacket(
            self.src, self.dest, self.id, packet_no, self.env.now)

    def retransmit(self, packet_no):
        self._ret_packets.append(packet_no)
        self._cwnd_balance.put(1)

    def add_alarm(self, packet_no, cur_time, timeout):
        expiration = cur_time + timeout
        heapq.heappush(self._deadlines, (expiration, packet_no, cur_time))

    def run_alarm(self):
        if (self._alarm is not None) and (not self._alarm.processed):
            self._alarm.interrupt()

        d = self._deadlines
        while d:
            pktt = self.window[d[0][1]]
            if pktt:
                assert pktt.packet_no == d[0][1]
            if pktt is None or pktt.acked:
                heapq.heappop(d)
            else:
                break
        if d:
            timeout = d[0][0] - self.env.now
            assert timeout >= 0
            self._alarm = self.env.process(self.proc_alarm(timeout))

    def proc_alarm(self, timeout):
        try:
            yield self.env.timeout(timeout)

            # Alarm expires
            self._alarm = None
            deadlines = self._deadlines
            packet_no = deadlines[0][1]
            pktt = self.window[packet_no]
            timestamp = pktt.timestamp
            assert pktt.packet_no == packet_no
            assert packet_no >= self.window.offset
            heapq.heappop(deadlines)

            print('{:06f} timeout {}'.format(self.env.now, packet_no))

            # Call event handler for timeout
            self._state.event_timeout(pktt)

            self.run_alarm()

        except simpy.Interrupt:
            pass

    def get_ack(self, ack_no, timestamp):
        packet_no = ack_no - 1
        q = self.window

        expected = self.window.offset

        if packet_no < expected:
            if packet_no == self.last_pkinfo.packet_no:
                # Dup ack
                self._ndup += 1
                print('{:06f} dupack {}'.format(self.env.now, ack_no))
                self._state.event_dupack(self.last_pkinfo, self._ndup)
            return
        else:
            # Normal ack

            self._ndup = 0

            # Locate the packet tracker
            pktt = q[packet_no]
            self.last_pkinfo = pktt
            assert pktt.packet_no == packet_no

            # Mark the packet as acked
            pktt.acked = True

            # Update timeout
            delay = self.env.now - timestamp
            print('{:.6f} packet_rtt {} {}'.format(
                self.env.now, self.id, delay))
            self.timeout = self._timer(delay)

            # Shift transmission window
            pdiff = packet_no - expected + 1

            self.inc_balance(pdiff)
            q.offset += pdiff

            # Reset alarm
            self.run_alarm()

            self._state.event_ack(pktt)

    def proc_next_packet(self):
        yield self.env.timeout(self.start)

        i = self._first_packet
        end = i + self.num_packets

        while True:
            yield self._cwnd_balance.get(1)

            j = None
            retransmit = False

            if self._ret_packets:
                j = self._ret_packets.popleft()
                pktt = self.window[j]

                if (pktt is None) or (pktt.acked):
                    break

                retransmit = True

            if not retransmit:
                if i < end:
                    j = i
                    i += 1
                else:
                    break

            packet = self.make_packet(j)

            t = self.env.now

            if retransmit:
                print('{:.6f} retransmit {} {}'.format(
                    self.env.now, self.id, j))

            self.window[j] = PacketRecord(
                j, t, t + self.timeout, False, retransmit)

            yield self.next_packet.put(packet)

            self.add_alarm(j, t, self.timeout)

            self.run_alarm()

class FlowState(object):

    def __init__(self, context, name):
        self.name = name
        self.context = context

    def event_timeout(self, packet_info):
        raise NotImplementedError()

    def event_dupack(self, packet_info, ndup):
        raise NotImplementedError()

    def event_ack(self, packet_info):
        raise NotImplementedError()

class TCPTahoeSS(FlowState):

    def event_timeout(self, packet_info):
        self.context.state = 'ret'

    def event_dupack(self, packet_info, ndup):
        if ndup == 3:
            self.context.state = 'ret'

    def event_ack(self, packet_info):
        self.context.cwnd += 1

        if (self.context.ssthresh is not None and 
            self.context.cwnd >= self.context.ssthresh):
            self.context.state = 'ca'

class TCPTahoeRet(FlowState):

    def __init__(self, context, name):
        super(TCPTahoeRet, self).__init__(context, name)
        self.packet_no = self.context.last_pkinfo.packet_no + 1
        self.context.ssthresh = max(1, self.context.cwnd / 2)
        self.context.cwnd = 1
        self.context.retransmit(self.packet_no)

    def event_timeout(self, packet_info):
        self.context.retransmit(packet_info.packet_no)

    def event_dupack(self, packet_info, ndup):
        pass

    def event_ack(self, packet_info):
        self.context.cwnd += 1
        self.context.state = 'ss'

class TCPTahoeCA(TCPTahoeSS):

    def event_ack(self, packet_info):
        self.context.cwnd += 1 / self.context.cwnd

class TCPTahoeFlow(BaseFlow):

    def __init__(self, env, flow_id, src_id, dest_id, data_mb, start_s):

        states = {
            'ss':   TCPTahoeSS,
            'ca':   TCPTahoeCA,
            'ret':  TCPTahoeRet }

        super(TCPTahoeFlow, self).__init__(
            env, flow_id, src_id, dest_id, data_mb, start_s,
            states, 'ss')

class TCPRenoSS(FlowState):

    def event_timeout(self, packet_info):
        self.context.state = 'ret'

    def event_dupack(self, packet_info, ndup):
        if ndup >= 3:
            self.context.state = 'frfr'

    def event_ack(self, packet_info):
        self.context.cwnd += 1

        if (self.context.ssthresh is not None and 
            self.context.cwnd >= self.context.ssthresh):
            self.context.state = 'ca'

class TCPRenoCA(TCPRenoSS):

    def event_ack(self, packet_info):
        self.context.cwnd += 1 / self.context.cwnd

TCPRenoRet = TCPTahoeRet

class TCPRenoFRFR(FlowState):

    def __init__(self, context, name):
        super(TCPRenoFRFR, self).__init__(context, name)
        self.start_time = self.context.env.now
        self.packet_no = self.context.last_pkinfo.packet_no + 1

        self.context.ssthresh = max(1, self.context.cwnd / 2)
        self.context.cwnd = self.context.ssthresh + 3
        self.context.retransmit(self.packet_no)

    def event_timeout(self, packet_info):
        if packet_info.timestamp >= self.start_time:
            self.context.state = 'ret'
        else:
            self.context.retransmit(packet_info.packet_no)

    def event_dupack(self, packet_info, ndup):
        self.context.cwnd += 1

    def event_ack(self, packet_info):
        self.context.cwnd = self.context.ssthresh
        self.context.state = 'ca'

class TCPRenoFlow(BaseFlow):

    def __init__(self, env, flow_id, src_id, dest_id, data_mb, start_s):

        states = {
            'ss':   TCPRenoSS,
            'ca':   TCPRenoCA,
            'ret':  TCPRenoRet,
            'frfr': TCPRenoFRFR }

        super(TCPRenoFlow, self).__init__(
            env, flow_id, src_id, dest_id, data_mb, start_s,
            states, 'ss')

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
    def __init__(self, b=0.1, n=4, c=1.1):
        self.b = b
        self.n = n
        self.a = None
        self.d = None
        self.c = c

    def __call__(self, t):
        a = self.a
        d = self.d
        b = self.b

        if a is None:
            self.a = self.d = t
        else:
            self.a = (1 - b) * a + b * t
            self.d = (1 - b) * d + b * abs(t - a)

        return self.c * (self.a + self.n * self.d)

class FASTTCP(BaseFlow):
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

