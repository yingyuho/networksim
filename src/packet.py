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

    def __init__(self, src, dest, flow_id, packet_no):
        super(DataPacket, self).__init__()
        self.src = src
        self.dest = dest
        self.flow_id = flow_id
        self.packet_no = packet_no

    @property
    def payload_size(self):
        """Capacity for payload in bytes.
        """
        return self._payload_size

    def reach_router(self, router):
        router.send(self, router.table[self.dest])
        
    def reach_host(self, host):
        print('{:.6f} : {} -> {} : Dta {}'.format(
            host.env.now, self.src, self.dest, self.packet_no))
        host.send_except(
            AckPacket(self.dest, self.src, self.flow_id, self.packet_no))

class AckPacket(Packet):
    """docstring for AckPacket"""

    _size = 64

    def __init__(self, src, dest, flow_id, packet_no):
        super(AckPacket, self).__init__()
        self.src = src
        self.dest = dest
        self.flow_id = flow_id
        self.packet_no = packet_no

    def reach_router(self, router):
        router.send(self, router.table[self.dest])
        
    def reach_host(self, host):
        print('{:.6f} : {} -> {} : Ack {}'.format(
            host.env.now, self.src, self.dest, self.packet_no))
        
class RoutingPacket(Packet):
    """docstring for RoutingPacket"""

    _size = 64

    def __init__(self, arg):
        super(RoutingPacket, self).__init__()
        self.arg = arg

    def reach_router(self, router):
        # TODO
        raise NotImplementedError()
        
    def reach_host(self, host):
        # Nothing, really
        pass
        