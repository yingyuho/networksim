from __future__ import division, print_function
from functools import partial
from operator import attrgetter
import simpy

from simpy_ext import SizedStore

class PipePair(object):
    """A named two-tuple of :class:`~simpy.core.Environment` objects for
    inter-device communication.
    """
    def __init__(self, pipe_in, pipe_out):
        self.pipe_in = pipe_in
        self.pipe_out = pipe_out

class Device(object):
    """docstring for Device"""

    def __init__(self, env, dev_id):
        self.env = env
        self._dev_id = dev_id
        self._ports = {}
        
    @property
    def dev_id(self):
        """Unique ID of this device in the network."""
        return self._dev_id

    _max_degree = None

    @property
    def degree(self):
        """Number of other devices this device connects to."""
        return len(self._ports)

    @property
    def max_degree(self):
        """Maximal number of other devices this device can connect to
        or None if there is no upper limit.
        """
        return self._max_degree

    def _add_packet_listener(self, adj_id, port):
        def listener():
            while True:
                packet = yield port.pipe_in.get()
                self.receive(packet, adj_id)
        self.env.process(listener())

    def add_port(self, adj_id, port):
        """Add and listen to an I/O port to this device."""
        if adj_id in self._ports:
            raise Exception('Duplicate port name')

        if self.max_degree is not None and self.degree >= self.max_degree:
            raise Exception('Connectd to too many devices')

        self._ports[adj_id] = port

        # Add a listener process
        self._add_packet_listener(adj_id, port)

    def send(self, packet, to_id):
        self._ports[to_id].pipe_out.put(packet)

    def send_except(self, packet, except_id=None):
        for adj_id in self._ports:
            if except_id is None or adj_id != except_id:
                self.send(packet, adj_id)

    def receive(self, packet, from_id):
        raise NotImplementedError()

    def activate_ports(self):
        raise NotImplementedError()

class Host(Device):
    """docstring for Host"""

    _max_degree = 1

    def __init__(self, env, dev_id):
        super(Host, self).__init__(env, dev_id)
        self._flows = {}

    def receive(self, packet, from_id):
        packet.reach_host(self)

    def add_flow(self, flow):
        self._flows[flow.id] = flow

        def send_packet():
            while True:
                packet = yield flow.next_packet.get()
                for adj_id in self._ports:
                    self.send(packet, adj_id)

        self.env.process(send_packet())


class BufferedCable(object):
    """docstring for BufferedCable

    Attributes:
        rate: Link rate in Mbps.
        delay: Link delay in milliseconds.
        buf_size: Link buffer capacity in kilobytes.

    """
    def __init__(self, env, rate, delay, buf_size):
        self.env = env

        self.rate = rate
        self.delay = delay
        self.buf_size = buf_size

        # Packet sizes are measured in bytes. Hence the factor 1024. 
        self._packet_buffer = SizedStore(
            self.env, 1024 * self.buf_size, attrgetter('size'))

        self._cable = simpy.Store(env)

        self.io = PipePair(simpy.Store(env), simpy.Store(env))

        self.env.process(self.feed_buffer())
        self.env.process(self.feed_cable())

    def feed_buffer(self):
        while True:
            packet = yield self.io.pipe_in.get()
            # print('At Packet {0}'.format(packet.packet_no))
            # print('Buffer level: {}'.format(self._packet_buffer._level))

            with self._packet_buffer.put(packet) as req:
                ret = yield req | self.env.event().succeed()
                if req not in ret:
                    # TODO: Packet loss
                    print('Packet {0} is lost'.format(packet.packet_no))

    def feed_cable(self):
        while True:
            packet = yield self._packet_buffer.get()
            self.env.process(self.latency(packet))
            yield self.env.timeout(packet.size * 8 / (self.rate * 1.0E6))

    def latency(self, packet):
        yield self.env.timeout(self.delay / 1.0E3)
        self.io.pipe_out.put(packet)

class Link(Device):
    """Full-duplex link

    Attributes:
        rate: Link rate in Mbps. Do not modify.
        delay: Link delay in milliseconds. Do not modify.
        buf_size: Link buffer capacity in kilobytes. Do not modify.

    """

    _max_degree = 2

    def __init__(self, env, dev_id, rate, delay, buf_size):
        super(Link, self).__init__(env, dev_id)

        self.rate = rate
        self.delay = delay
        self.buf_size = buf_size

        self._cables = {}

    def add_port(self, adj_id, port):
        """Add and listen to an I/O port to this device."""
        super(Link, self).add_port(adj_id, port)

        self._cables[adj_id] = BufferedCable(
            self.env, self.rate, self.delay, self.buf_size)

        def listener(adj_id):
            while True:
                packet = yield self._cables[adj_id].io.pipe_out.get()
                for to_id in self._ports:
                    if to_id != adj_id:
                        self.send(packet, to_id)

        self.env.process(listener(adj_id))

    def receive(self, packet, from_id):
        self._cables[from_id].io.pipe_in.put(packet)
        
class Router(Device):
    """docstring for Router

    Attributes:
        table: A dictionary mapping dest_id to link_id.

    """

    def __init__(self, env, dev_id):
        super(Router, self).__init__(env, dev_id)
        self.table = {}

        self.env.process(self.sendRP())

    def sendRP(self):
	rp = RoutingPacket (self.dev_id)
	

        yield self.env.event().succeed()

    def receive(self, packet, from_id):
        packet.reach_router(self, from_id)
        
