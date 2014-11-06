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

class Device(object):
    """docstring for Device"""

    def __init__(self, env, dev_id):
        super(Device, self).__init__()
        self._env = env
        self._dev_id = dev_id
        self.iports = {}
        self.oports = {}
        
    @property
    def dev_id(self):
        """Unique ID of this device in the network.
        """
        return self._dev_id

    def send(packet, to_id):
        # self._ports[to].receive(packet, self._dev_id)
        raise NotImplementedError()

    def receive(packet, from_id):
        raise NotImplementedError()


class Host(Device):
    """docstring for Host"""

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

    Attributes:

    """

    def __init__(self, env, dev_id, adj_ids, rate, delay, buf_size):
        super(Link, self).__init__(env, dev_id)

        self._rate = rate
        self._delay = delay
        self._buf_size = buf_size

        self._adj_ids = adj_ids

        if len(adj_ids) != 2:
            raise ValueError('Wrong number of link connections')

        for adj_id in adj_ids:
            self.iports[adj_id] = SizedStore(env)
            self.oports[adj_id] = SizedStore(env)

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
        