from __future__ import division, print_function
from functools import partial
from operator import attrgetter

import simpy

class Packet(object):
    """docstring for Packet"""
    def __init__(self):
        super(Packet, self).__init__()

    _size = 0

    @property
    def size(self):
        """Size of packet in bytes.
        """
        return self._size

    def reach_router(self, router):
        raise NotImplementedError()

    def reach_host(self, host):
        raise NotImplementedError()

class DataPacket(Packet):
    """docstring for DataPacket"""

    _size = 1536

    _payload_size = 1024

    def __init__(self, src, dest, message):
        super(DataPacket, self).__init__()
        self.src = src
        self.dest = dest
        self.message = message

    @property
    def payload_size(self):
        """Capacity for payload in bytes.
        """
        return self._payload_size

    def reach_router(self, router):
        router.send(self, router.look_up(self.dest))
        
    def reach_host(self, host):
        print('{:.3f} : {} -> {} : {}'.format(
            host.env.now, self.src, self.dest, self.message))
        # TODO: Acknowledge

class AckPacket(Packet):
    """docstring for AckPacket"""

    _size = 64

    def __init__(self, src, dest, arg):
        super(AckPacket, self).__init__()
        self.src = src
        self.dest = dest
        self.arg = arg

    def reach_router(self, router):
        router.send(self, router.look_up(self.dest))
        
    def reach_host(self, host):
        raise NotImplementedError()
        
class RoutingPacket(Packet):
    """docstring for RoutingPacket"""

    _size = 64

    def __init__(self, arg):
        super(RoutingPacket, self).__init__()
        self.arg = arg
        