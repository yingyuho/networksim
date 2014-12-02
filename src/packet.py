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
    """
    The routing packets start at the router
    The router_start_id is the ID of the router.
    The recorded_time is initially the time that the routing packet is sent.
    The host_id is the id of the host.
    """
        super(RoutingPacket, self).__init__()
        self.router_start_id = router_start_id
        self.recorded_time = recorded_time
        self.host_id = None
    
    def reach_router(self, router, port_id):
    """
    When the packet reaches a router, it checks to see 
    if the packet initialized there.
    If it started at that router, then it checks to see if
    the host_id is already in the table or if the time 
    is faster than the initial arrival. If either case is true,
    then we add the entry port as the destination for the packets.
    We also keep track of the smallest time that it has arrived at so far.
    If it's not the router that it started in, it sends to every port except
    the entry port. 
    """
        if self.router_start_id == router.dev_id:
            if self.host_id not in router.table \
               or router.timeTable[self.host_id] > self.recorded_time:
                router.table[self.host_id] = port_id
                router.timeTable[self.host_id] = self.recorded_time
        else:
            router.send_except(self, except_id=port_id)
    
    def reach_host(self, host):
    """
    If it arrives at a host, then it finds the time it took to get to the host.
    It also stores the host_id. If the host_id is not None,
    then it doesn't do anything.
    """
        if self.host_id == None:
            self.recorded_time = host.env.now - self.recorded_time
            self.host_id = host.dev_id;
            print(host.dev_id)
            host.send(self, self.router_start_id)
