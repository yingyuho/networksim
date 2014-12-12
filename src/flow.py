from __future__ import division, print_function
from collections import deque, namedtuple
from math import ceil
import heapq

import simpy

from packet import DataPacket, AckPacket

class PacketRecord(object):
    """Tracking record for a sent data packet.

    Attributes:
        packet_no: Packet number starting from 1.
        timestamp: Time when this packet was sent.
        acked: Whether this packet has been acknowledged.
        retransmit: Whether this packet is a retransmitted one.
    """

    def __init__(
        self, packet_no, timestamp, 
        acked=False, retransmit=False
    ):
        self.packet_no = packet_no
        self.timestamp = timestamp
        # self.expiration = expiration
        self.acked = acked
        self.retransmit = retransmit

class SlidingWindow(object):
    """A generic transmission window.

    It is a list with possibly non-zero starting index that can only increase.

    Attributes:
        offset: Index number for the first element in storage.
    """

    def __init__(self, first_packet=1):
        self._offset = first_packet
        self._queue = deque()

    def __len__(self):
        return len(self._queue)

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
            raise IndexError('packet number not in window {}'.format(
                (i, j, self._offset, [p.packet_no for p in self._queue])))

class BaseFlow(object):
    """Basic functionality for a TCP flow.

    Attributes:
        env: SimPy environment.
        id: Flow ID.
        src: Source host ID.
        dest: Target host ID.
        data: Data amount in megabytes.
        start: Time in seconds when this flow is scheduled to start.
        num_packets: Total number of packets to be sent.
        next_packet: simpy.Store object with packets ready for transmission
            inside.
        window: SlidingWindow object that keeps track of send packets.
        cwnd: Congestion window size.
        timeout: Current timeout setting.
        base_rtt: Base round-trip time as measured.
        curr_rtt: The most recent round-trip time.
        ssthresh: Threshold for Slow Start -> Congestion Avoidance.
        state: Current state of congestion control.
    """

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
        self._packet_start = 1
        self._packet_end = self._packet_start + self.num_packets
        self.packet_cursor = self._packet_start

        # Transmit window access control
        self.window = SlidingWindow()
        self._cwnd = 1
        self._cwnd_frac = 0.0
        self._cwnd_balance = simpy.Container(env, init=self._cwnd)
        self._cwnd_debt = 0

        # Timeout
        self.timeout = 1.0
        self._timer = JKTimer()
        self._alarm = None
        self._deadlines = []
        self._last_ss = 0.0

        # RTT
        self.base_rtt = 1
        self.curr_rtt = 1

        # Dup ack counter
        self.last_pkinfo = None
        self._ndup = 0

        # State
        self._ssthresh = None
        self._state_constr = state_constr
        self._state = None
        self.state = init_state

        # Activate main process
        self._main_proc = self.env.process(self.proc_next_packet())
        self._finished = False

    @property
    def ssthresh(self):
        return self._ssthresh
    @ssthresh.setter
    def ssthresh(self, value):
        self._ssthresh = value
        print('{:.6f} ssthresh {} {:.3f}'.format(
            self.env.now, self.id, value))
    

    @property
    def state(self):
        if self._state is not None:
            return self._state.name
        else:
            return None
    @state.setter
    def state(self, value):
        if self._state is not None:
            print('{:.6f} state {} {}'.format(
                self.env.now, self.id, value))
        self._state = self._state_constr[value](self, value)
    
    @property
    def cwnd(self):
        """Congestion window."""
        return self._cwnd + self._cwnd_frac
    @cwnd.setter
    def cwnd(self, value):

        if value < 1:
            raise ValueError('Attempt to set cwnd < 1')

        self._cwnd_frac = value - int(value)

        value = int(value)

        old = self._cwnd

        income = value - old

        if income > 0:
            repayment = min(income, self._cwnd_debt)
            saving = income - repayment
            self._cwnd_debt -= repayment
            if saving > 0:
                self._cwnd_balance.put(saving)
        else:
            self._cwnd_debt -= income

        self._cwnd = value

        print('{:.6f} window_size {} {:.3f}'.format(
            self.env.now, self.id, value + self._cwnd_frac))
        # print('{:f} balance {} {}'.format(
        #     self.env.now, self.id, self._cwnd_balance._level))

    def inc_balance(self, n=1):
        """Indicates that outstanding packet(s) has been acknowledged.

        Args:
            n: Number of outstanding acknowledged.
        """
        n = int(n)
        if self._cwnd_debt >= n:
            self._cwnd_debt -= n
        elif self._cwnd_debt > 0:
            self._cwnd_balance.put(n - self._cwnd_debt)
            self._cwnd_debt = 0
        else:
            self._cwnd_balance.put(n)

    def zero_debt(self):
        self._cwnd_debt = 0

    def make_packet(self, packet_no):
        """Make a data packet with the given packet number."""
        return DataPacket(
            self.src, self.dest, self.id, packet_no, self.env.now)

    def retransmit(self, packet_no):
        """Retransmit for a packet number."""
        self._ret_packets.append(packet_no)
        self._cwnd_balance.put(1)

    def add_alarm(self, packet_no, cur_time, timeout):
        """Schedule a timeout event."""
        expiration = cur_time + timeout
        heapq.heappush(self._deadlines, (expiration, packet_no, cur_time))

    def run_alarm(self):
        """Reset SimPy process when the list of timeout event is updated"""
        if (self._alarm is not None) and (not self._alarm.processed):
            self._alarm.interrupt()

        d = self._deadlines
        while d:
            pktt = self.window[d[0][1]]
            if pktt:
                assert pktt.packet_no == d[0][1]
            if pktt is None or pktt.packet_no >= self.packet_cursor:
                heapq.heappop(d)
            else:
                break
        if d:
            timeout = d[0][0] - self.env.now
            assert timeout >= 0
            self._alarm = self.env.process(self.proc_alarm(timeout))

    def proc_alarm(self, timeout):
        """SimPy process for timeout events."""
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
        """Handles arrival of AckPacket.

        Args:
            ack_no: Packet number of AckPacket.
            timestamp: Time when the corresponding data packet was sent.
        """

        if self._finished:
            return

        if ack_no == self._packet_end:
            print('{:06f} finish {}'.format(self.env.now, self.id))
            self.done()
            return

        packet_no = ack_no - 1
        q = self.window

        expected = self.window.offset

        if packet_no < expected:
            if packet_no == self.last_pkinfo.packet_no:
                # Dup ack
                self._ndup += 1
                print('{:06f} dupack {} {}'.format(
                    self.env.now, ack_no, q[ack_no].timestamp))
                self._state.event_dupack(q[ack_no], self._ndup)
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
            if timestamp is not None:
                pktt.timestamp = timestamp
            delay = self.env.now - pktt.timestamp
            print('{:.6f} packet_rtt {} {}'.format(
                self.env.now, self.id, delay))
            self.timeout = self._timer(delay)

            self.curr_rtt = delay

            if delay < self.base_rtt:
                self.base_rtt = delay

            # Shift transmission window
            # pdiff = min(packet_no - expected + 1, len(q))

            q.offset = packet_no + 1

            # Reset alarm
            self.run_alarm()

            self._state.event_ack(pktt)

            bal_inc = min(packet_no + 1, self.packet_cursor) - expected

            self.inc_balance(max(1, bal_inc))

    def go_back(self, packet_no=None):
        """Rewinds the window for retransmission."""
        old_cur = self.packet_cursor
        if packet_no is None:
            self.packet_cursor = self.window.offset
        else:
            self.packet_cursor = packet_no
        self.inc_balance(old_cur - self.packet_cursor)
        self.run_alarm()

    def done(self):
        """Stops making packets."""
        self._finished = True
        for proc in [self._main_proc, self._alarm]:
            if (proc is not None) and (not proc.processed):
                proc.interrupt()

    def proc_next_packet(self):
        """SimPy process for making packets ready for transmission."""
        yield self.env.timeout(self.start)

        while True:
            try:
                yield self._cwnd_balance.get(1)
            except simpy.Interrupt:
                break

            j = None
            retransmit = False

            if self._ret_packets:
                j = self._ret_packets.popleft()
                pktt = self.window[j]

                if pktt is None:
                    continue

                retransmit = True

            if not retransmit:
                j = i = max(self.packet_cursor, self.window.offset)
                if i >= self._packet_end:
                    continue
                self.packet_cursor = i + 1

            packet = self.make_packet(j)

            t = self.env.now

            if retransmit:
                print('{:.6f} retransmit {} {}'.format(
                    self.env.now, self.id, j))

            if self.window[j] is None:
                self.window[j] = PacketRecord(j, t, False, retransmit)
            else:
                self.window[j].retransmit = retransmit

            try:
                yield self.next_packet.put(packet)
            except simpy.Interrupt:
                break

            self.add_alarm(j, t, self.timeout)

            self.run_alarm()

class FlowState(object):
    """State controller for congestion control algorithms.

    Attributes:
        name: Name of congestion control state.
        context: The Flow object this controller belongs to.
    """

    def __init__(self, context, name):
        self.name = name
        self.context = context
        self.start_time = self.context.env.now

    def event_timeout(self, packet_info):
        raise NotImplementedError()

    def event_dupack(self, packet_info, ndup):
        raise NotImplementedError()

    def event_ack(self, packet_info):
        raise NotImplementedError()

class TCPTahoeSS(FlowState):

    def __init__(self, context, name):
        super(TCPTahoeSS, self).__init__(context, name)

    def event_timeout(self, packet_info):
        """Handles timeout for TCP Tahoe Slow Start."""
        cont = self.context

        if packet_info.timestamp >= self.start_time:
            cont.ssthresh = max(1, cont.cwnd / 2)

        cont.cwnd = 1
        cont.go_back()

        self.context.state = 'ss'

    def event_dupack(self, packet_info, ndup):
        """Handles 3 dup ack for TCP Tahoe Slow Start."""
        if ndup == 3:
            self.event_timeout(packet_info)

    def event_ack(self, packet_info):
        """Updates window size for TCP Tahoe Slow Start."""
        if packet_info.timestamp >= self.start_time:
            self.context.cwnd += 1

        if (self.context.ssthresh is not None and 
            self.context.cwnd >= self.context.ssthresh):
            self.context.state = 'ca'

class TCPTahoeCA(TCPTahoeSS):

    def event_ack(self, packet_info):
        """Updates window size for TCP Tahoe Congestion Avoidance."""
        self.context.cwnd += 1 / self.context.cwnd

class TCPTahoeFlow(BaseFlow):

    def __init__(self, env, flow_id, src_id, dest_id, data_mb, start_s):

        states = {
            'ss':   TCPTahoeSS,
            'ca':   TCPTahoeCA }

        super(TCPTahoeFlow, self).__init__(
            env, flow_id, src_id, dest_id, data_mb, start_s,
            states, 'ss')

class TCPRenoSS(TCPTahoeSS):

    def event_dupack(self, packet_info, ndup):
        """Handles 3 dup ack for TCP Reno Slow Start."""
        cont = self.context
        if ndup >= 3:
            if packet_info.timestamp >= self.start_time:
                cont.ssthresh = max(1, cont.cwnd / 2)
            if cont.ssthresh is not None:
                cont.cwnd = cont.ssthresh + ndup
            else:
                cont.cwnd = 1
            cont.retransmit(packet_info.packet_no)
            cont.state = 'frfr'

class TCPRenoCA(TCPRenoSS):

    def event_ack(self, packet_info):
        """Updates window size for TCP Reno Congestion Avoidance."""
        self.context.cwnd += 1 / self.context.cwnd

class TCPRenoFRFR(FlowState):

    def __init__(self, context, name):
        super(TCPRenoFRFR, self).__init__(context, name)
        self.timeout_no = 0

    def event_timeout(self, packet_info):
        """Handles timeout for TCP Reno FR/FR."""
        cont = self.context
        
        if packet_info.timestamp >= self.start_time:
            cont.cwnd = 1
            cont.go_back()
            cont.state = 'ss'
        else:
            self.timeout_no = max(self.timeout_no, packet_info.packet_no)

    def event_dupack(self, packet_info, ndup):
        """Handles 3 dup ack for TCP Reno FR/FR."""
        self.context.cwnd += 1

    def event_ack(self, packet_info):
        """Updates window size for TCP Reno FR/FR."""
        cont = self.context
        if packet_info.packet_no >= self.timeout_no:
            cont.cwnd = cont.ssthresh
            cont.state = 'ca'
        else:
            cont.cwnd = 1
            cont.go_back()
            cont.state = 'ss'

class TCPRenoFlow(BaseFlow):

    def __init__(self, env, flow_id, src_id, dest_id, data_mb, start_s):

        states = {
            'ss':   TCPRenoSS,
            'ca':   TCPRenoCA,
            'frfr': TCPRenoFRFR }

        super(TCPRenoFlow, self).__init__(
            env, flow_id, src_id, dest_id, data_mb, start_s,
            states, 'ss')

class FastTCPCA(TCPRenoSS):

    def event_ack(self, packet_info):
        """Updates window size for FAST-TCP Congestion Avoidance."""
        cont = self.context

        cwnd = cont.cwnd

        weight = min(3 / cwnd, 1/4)

        if cont.avg_rtt is None:
            cont.avg_rtt = cont.curr_rtt

        cont.avg_rtt = (1 - weight * cont.avg_rtt + weight * cont.curr_rtt)

        cont.queue_delay = cont.avg_rtt - cont.base_rtt

        # Exp decay factor
        gamma = 0.05
        # Desired number of packets in buffer
        alpha = 3
        
        ratio = cont.base_rtt / cont.curr_rtt
        new_cwnd = (1 - gamma) * cwnd + gamma * (ratio * cwnd + alpha)
        cont.cwnd = min(2 * cwnd, new_cwnd)

class FastTCPFlow(BaseFlow):

    def __init__(self, env, flow_id, src_id, dest_id, data_mb, start_s):

        states = {
            'ss':   FastTCPCA,
            'ca':   FastTCPCA,
            'frfr': TCPRenoFRFR }

        super(FastTCPFlow, self).__init__(
            env, flow_id, src_id, dest_id, data_mb, start_s,
            states, 'ss')

        # Average RTT
        self.avg_rtt = None

        # Calculated queue delay
        self.queue_delay = 0

class CubicTCPSS(TCPRenoSS):

    def __init__(self, context, name):
        super(CubicTCPSS, self).__init__(context, name)
        if context.ssthresh is not None:
            context.w_max = context.ssthresh * 2
        context.cubic_thresh = context.w_max * (1 - context.beta)

    def event_ack(self, packet_info):
        """Updates window size for CUBIC-TCP Slow Start."""
        if packet_info.timestamp >= self.start_time:
            self.context.cwnd += 1

        if self.context.cwnd >= self.context.cubic_thresh:
            self.context.state = 'ca'

class CubicTCPCA(CubicTCPSS):

    def event_ack(self, packet_info):
        """Updates window size for CUBIC-TCP Congestion Avoidance."""

        cont = self.context

        # Current window size, before update
        cur_cwnd = cont.cwnd

        w_max = cont.w_max
        c = cont.c
        beta = cont.beta

        k = (w_max * beta / c) ** (1 / 3.0)

        t = cont.env.now - self.start_time

        cont.cwnd = max(1, c * (t - k) ** 3 + w_max)

class CubicTCPFlow(BaseFlow):
    def __init__(self, env, flow_id, src_id, dest_id, data_mb, start_s):
        states = {
            'ss':   CubicTCPSS,
            'ca':   CubicTCPCA,
            'frfr': TCPRenoFRFR }

        # Constants
        # Scaling factor for window update
        self.c = .4
        # multiplication decrease factor at the time of loss event
        self.beta = .8

        self.w_max = 160

        super(CubicTCPFlow, self).__init__(
            env, flow_id, src_id, dest_id, data_mb, start_s,
            states, 'ss')

class SelectiveReceiver(object):
    """Used by the client-side of flow to find the ack number."""
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

class JKTimer(object):
    """Compute timeout using Jacobson/Karels Algorithm."""
    def __init__(self, b=0.1, n=4, c=1.25):
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
