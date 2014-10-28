from __future__ import division, print_function
import simpy

class Packet(object):
    """docstring for Packet"""
    def __init__(self, arg):
        super(Packet, self).__init__()
        self.arg = arg

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

class AckPacket(Packet):
    """docstring for AckPacket"""
    def __init__(self, arg):
        super(AckPacket, self).__init__()
        self.arg = arg
        
class RoutingPacket(Packet):
    """docstring for RoutingPacket"""
    def __init__(self, arg):
        super(RoutingPacket, self).__init__()
        self.arg = arg
        