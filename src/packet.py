from __future__ import division, print_function
from functools import partial
from operator import attrgetter

import simpy
import random

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
    """
    The DataPacket is sent from one host to another.
    """

    _size = 1536

    payload_size = 1024

    def __init__(self, src, dest, flow_id, packet_no, timestamp):
        """
        Initiates the DataPacket

        Args:
            src: which host_id the packet starts in.
            dest: which host_id the packet should end in.
            flow_id: the ID of the flow that the packet is from.
            packet_no: the packet number.
            timestamp: time when the packet was sent
        """
        super(DataPacket, self).__init__()
        self.src = src
        self.dest = dest
        self.flow_id = flow_id
        self.packet_no = packet_no
        self.timestamp = timestamp

    def reach_router(self, router, port_id):
        """
        When it reaches a router, it goes through the port
        that has the shortest time.

        Args: 
            router: the router that the packet arrived to.
            port_id: the port it came in from.

        Purpose:
            The packet is sent to through the port into the router.
        """
        router.send(self, router.table[self.dest])
        
    def reach_host(self, host):
        """
        when the packet arrives at the host.

        Args:
            host: The host that the packet arrived at.

        Purpose:
            Sends an acknowledge packet back when the host receives the packet
        """
        # print('{:.6f} : {} -> {} : Dta {}'.format(
        #     host.env.now, self.src, self.dest, self.packet_no))
        n = host.get_data(self.flow_id, self.packet_no)
        if n is not None:
            host.send_except(AckPacket(
                self.dest, self.src, self.flow_id, n, self.timestamp))

class AckPacket(Packet):
    """
    This packet allows hsots to know their packet was recieved
    """

    _size = 64

    def __init__(self, src, dest, flow_id, packet_no, timestamp):
        """
        Initiates the AckPacket

        Args:
            src: the source of the packet
            dest: the destination of the packet
            flow_id: the id of the flow
            packet_no: the packet number
            timestamp: time when the original data packet was sent
        """
        super(AckPacket, self).__init__()
        self.src = src
        self.dest = dest
        self.flow_id = flow_id
        self.packet_no = packet_no
        self.timestamp = timestamp

    def reach_router(self, router, port_id):
        """
        The packet arrived at the router

        Args:
            router: the router that the packet arrived at.
            port_id: the port that the packet arrived from

        Purpose: 
            The packet is sent throught the port specified 
            by the routing table.
        """
        print("routing packet " + str(self.packet_no) + str(router.table[self.dest]))
        if self.dest not in router.table:
            router.send(self, random.choice(router.table.values()))
        else:
            router.send(self, router.table[self.dest])

    def reach_host(self, host):
        host.get_ack(self.flow_id, self.packet_no, self.timestamp)

class RoutingPacket(Packet):
    """
    The RoutingPacket is passed around the system to find
    the fastest path to hosts.
    """

    _size = 64

    def __init__(self, router_start_id, recorded_time):
        """
        Initiates RoutingPacket

        Args/private variables:
            router_start_id: initiating router ID 
            recorded_time: initially the current time
            end_id: the host or router ID
            passedTable: the dictionary containing routing table
            passedTimeTable: the dictionary containing the fastest times
        """
        super(RoutingPacket, self).__init__()
        self.router_start_id = router_start_id
        self.recorded_time = recorded_time
        self.end_id = None
        self.passedTable = None
        self.passedTimeTable = None
    
    def reach_router(self, router, port_id):
        """
        Called when the packet arrives at a router

        Args:
            router: the router that the packet arrived at
            port_id: the port it arrived through
        Purpose:
            Dijkstra. If the packet arrives to a router that
            it didn't start in, then the packet copies the 
            timeTable and the routing table of the router.
            It then goes through the port it arrived from.

            If the routing packet started at that router, 
            then we check to see if there was a dictionary passed.
            If there was we go through the ditionary and find the shortest
            path to all hosts in that dictionary. If not, 
            then we check to see if the end_id(host id) is in the
            dictionary. If it is, we check to see if the time is faster.
            if it is, we replace the time and the port_id.
        """
        if self.router_start_id == router.dev_id:
            if self.passedTable == None:
                if self.end_id not in router.table \
                   or router.timeTable[self.end_id] >= self.recorded_time:
                    router.table[self.end_id] = port_id
                    router.timeTable[self.end_id] = self.recorded_time
            else:
                for host in self.passedTable:
                    if host not in router.table or router.timeTable[host] >= self.passedTimeTable[host] + self.recorded_time:
                        router.table[host] = port_id
                        router.timeTable[host] = self.passedTimeTable[host] + self.recorded_time
        else:
            self.passedTable = copy.copy(router.table)
            self.passedTimeTable = copy.copy(router.timeTable)
            self.recorded_time = router.env.now - self.recorded_time
            router.send(self, port_id)
    
    def reach_host(self, host):
        """
        Called when the packet reaches a host

        Args:
            host: The host that the packet arrived at.

        Purpose:
            If the end_id is not initialized, then the packet records
            how long it took for the packet to get to the host. 
            it then sends the packet to the router it came from. 
        """
        if self.end_id == None:
            self.recorded_time = host.env.now - self.recorded_time
            self.end_id = host.dev_id;
            print(host.dev_id)
            host.send(self, self.router_start_id)
