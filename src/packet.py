from __future__ import division, print_function
from functools import partial
from operator import attrgetter

import simpy

class Packet(object):
    """docstring for Packet"""
    def __init__(self, arg):
        super(Packet, self).__init__()
        self.arg = arg

    @property
    def size(self):
        """Size of packet in bytes.
        """
        raise NotImplementedError()

    def reach_router(router):
        raise NotImplementedError()

    def reach_host(host):
        raise NotImplementedError()

class DataPacket(Packet):
    """docstring for DataPacket"""

    def __init__(self, src, dest, message):
        super(DataPacket, self).__init__()
        self.src = src
        self.dest = dest
        self.message = message

    def reach_router(router):
        router.send(self, router.look_up(self.dest))
        
    def reach_host(host):
        print('{} -> {} : {}'.format(self.src, self.dest, self.message))
        # TODO: Acknowledge

class AckPacket(Packet):
    """docstring for AckPacket"""
    def __init__(self, src, dest, arg):
        super(AckPacket, self).__init__()
        self.src = src
        self.dest = dest
        self.arg = arg

    def reach_router(router):
        router.send(self, router.look_up(self.dest))
        
    def reach_host(host):
        raise NotImplementedError()
        
class RoutingPacket(Packet):
    """docstring for RoutingPacket"""
    def __init__(self, arg):
        super(RoutingPacket, self).__init__()
        self.arg = arg
        