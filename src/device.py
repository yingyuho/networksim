from __future__ import division, print_function
from functools import partial
import simpy

from simpy_ext import SizedStore

class PacketBuffer(SizedStore):
    """Specialized version of :class:`simpy_ext.SizedStore` for 
    :class:`packet.Packet`.

    The *env* parameter is the :class:`~simpy.core.Environment` instance the
    container is bound to.

    The *capacity* defines the size of the buffer in bytes.

    """
    def __init__(self, env, capacity):
        super(PacketBuffer, self).__init__(env, capacity, attrgetter('size'))

class Port(object):
    """docstring for Port"""
    def __init__(self):
        super(Port, self).__init__()
        self.queue_in = None
        self.queue_out = None

class Device(object):
    """docstring for Device"""

    def __init__(self, env, dev_id):
        super(Device, self).__init__()
        self._env = env
        self._dev_id = dev_id
        self._ports = {}
        
    @property
    def dev_id(self):
        """Unique ID of this device in the network.
        """
        return self._dev_id

    _max_degree = None

    @property
    def degree(self):
        """Number of other devices this device connects to.
        """
        return len(self._ports)

    @property
    def max_degree(self):
        """Maximal number of other devices this device can connect to
        or None if there is no upper limit.
        """
        return self._max_degree

    def add_port(self, to_id, port):
        """Add an I/O port to this device.
        """
        if to_id in self._ports:
            raise Exception('Duplicate port name')

        if self.max_degree is not None and self.degree >= self.max_degree:
            raise Exception('Connectd to too many devices')

        self._ports[to_id] = port

    def send(packet, to_id):
        self._ports[to].receive(packet, self._dev_id)

    def receive(packet, from_id):
        raise NotImplementedError()


class Host(Device):
    """docstring for Host"""

    _max_degree = 1

    def __init__(self, env, dev_id):
        super(Host, self).__init__(env, dev_id)

    def receive(packet):
        packet.reach_host(self)

class BufferedPipe(object):
    """docstring for Pipe"""
    def __init__(self, env, rate, delay, buf_size):
        super(Pipe, self).__init__()
        self._env = env
        self._rate = rate
        self._delay = delay

        self._buffer = PacketBuffer(env, buf_size)

class Link(Device):
    """Full-duplex link

    """

    _max_degree = 2

    def __init__(self, env, dev_id, rate, delay, buf_size):
        super(Link, self).__init__(env, dev_id)

        self._rate = rate
        self._delay = delay
        self._buf_size = buf_size

    @property
    def rate(self):
        """Link rate in Mbps."""
        return self._rate

    @property
    def delay(self):
        """Link delay in milliseconds."""
        return self._delay

    @property
    def buf_size(self):
        """Link buffer capacity in kilobytes."""
        return self._buf_size

    def receive(packet):
        # TODO
        raise NotImplementedError()
        
class Router(Device):
    """docstring for Router
    """

    def __init__(self, env, dev_id):
        super(Router, self).__init__(env, dev_id)
        self._table = {}

    def look_up(dest_id):
        return self._table[dest]

    def receive(packet):
        packet.reach_router(self)
        