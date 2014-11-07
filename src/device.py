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
        super(PipePair, self).__init__()
        self.pipe_in = pipe_in
        self.pipe_out = pipe_out

class Device(object):
    """docstring for Device"""

    def __init__(self, env, dev_id):
        super(Device, self).__init__()
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

    def _packet_listener(self, adj_id, port):
        while True:
            packet = yield port.pipe_in.get()
            self.receive(packet, adj_id)

    def add_port(self, adj_id, port):
        """Add and listen to an I/O port to this device."""
        if adj_id in self._ports:
            raise Exception('Duplicate port name')

        if self.max_degree is not None and self.degree >= self.max_degree:
            raise Exception('Connectd to too many devices')

        self._ports[adj_id] = port

        # Add a listener process
        self.env.process(self._packet_listener(adj_id, port))

    def send(self, packet, to_id):
        self._ports[to_id].pipe_out.put(packet)

    def receive(self, packet, from_id):
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


class Link(Device):
    """Full-duplex link

    Attributes:
        rate: Link rate in Mbps.
        delay: Link delay in milliseconds.
        buf_size: Link buffer capacity in kilobytes.

    """

    _max_degree = 2

    def __init__(self, env, dev_id, rate, delay, buf_size):
        super(Link, self).__init__(env, dev_id)

        self.rate = rate
        self.delay = delay
        self.buf_size = buf_size

        self._packet_buffers = {}

    def add_port(self, adj_id, port):
        """Add and listen to an I/O port to this device."""
        super(Link, self).add_port(adj_id, port)

        # Packet sizes are measured in bytes. Hence the factor 1024. 
        self._packet_buffers[adj_id] = SizedStore(
            self.env, 1024 * self.buf_size, attrgetter('size'))

        return self._buf_size

    def receive(self, packet, from_id):
        # Just relay incoming packets to the other side
        for adj_id in self._ports:
            if adj_id != from_id:
                self.send(packet, adj_id)
        # TODO: Add latency, etc.
        
class Router(Device):
    """docstring for Router

    Attributes:
        table: A dictionary mapping dest_id to link_id.

    """

    def __init__(self, env, dev_id):
        super(Router, self).__init__(env, dev_id)
        self.table = {}

    def receive(self, packet, from_id):
        packet.reach_router(self)
        