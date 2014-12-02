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

    def reach_router(self, router, port_id):
        raise NotImplementedError()

    def reach_host(self, host):
        raise NotImplementedError()

class DataPacket(Packet):
    """docstring for DataPacket"""

    _size = 1536

    payload_size = 1024

    def __init__(self, src, dest, flow_id, packet_no):
        super(DataPacket, self).__init__()
        self.src = src
        self.dest = dest
        self.flow_id = flow_id
        self.packet_no = packet_no

    def reach_router(self, router, port_id):
        router.send(self, router.table[self.dest])
        
    def reach_host(self, host):
        # print('{:.6f} : {} -> {} : Dta {}'.format(
        #     host.env.now, self.src, self.dest, self.packet_no))
        n = host.get_data(self.flow_id, self.packet_no)
        if n is not None:
            host.send_except(AckPacket(self.dest, self.src, self.flow_id, n))

class AckPacket(Packet):
    """docstring for AckPacket"""

    _size = 64

    def __init__(self, src, dest, flow_id, packet_no):
        super(AckPacket, self).__init__()
        self.src = src
        self.dest = dest
        self.flow_id = flow_id
        self.packet_no = packet_no

    def reach_router(self, router, port_id):
        router.send(self, router.table[self.dest])

    def reach_host(self, host):
        host.get_ack(self.flow_id, self.packet_no)

class RoutingPacket(Packet):
    """docstring for RoutingPacket"""

    _size = 64

    def __init__(self, router_start_id, recorded_time):
        super(RoutingPacket, self).__init__()
        self.router_start_id = router_start_id
        self.recorded_time = recorded_time
        self.start_id = None
        self.recorded_time = None

    def reach_router(self, router, port_id):
        if self.router_start_id == router.dev_id:
            if self.start_id not in router.table \
               or router.timeTable[self.start_id] > self.recorded_time:
                router.table[self.start_id] = port_id
                router.timeTable[self.start_id] = self.recorded_time
        else:
            router.send_except(self, except_id=port_id)
        
    def reach_host(self, host):
        if self.start_id == None:
            if self.recorded_time == None:
                self.recorded_time = host.env.now
            else:
                self.recorded_time = host.env.now - self.recorded_time
            self.start_id = host.dev_id;
            print(host.dev_id)
            host.send(self, self.router_start_id)
