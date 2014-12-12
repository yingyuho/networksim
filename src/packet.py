from __future__ import division, print_function
from functools import partial
from operator import attrgetter

import simpy
import random
import copy

class Packet(object):
    """Base class for all kinds of packets."""
    def __init__(self):

        super(Packet, self).__init__()

    _size = 0

    @property
    def size(self):
        """Returns the size of packet in bytes."""
        return self._size

    def reach_router(self, router, port_id):
        raise NotImplementedError()

    def reach_host(self, host):
        raise NotImplementedError()

class DataPacket(Packet):
    """Represents data sent from one source to another."""

    _size = 1024

    payload_size = 1024

    def __init__(self, src, dest, flow_id, packet_no, timestamp):
        """Creates a data packet.

        Args:
            src: Host ID of the source.
            dest: Host ID of the target.
            flow_id: Flow ID this packet belongs to.
            packet_no: Packet number.
            timestamp: Time when the packet was sent.
        """
        super(DataPacket, self).__init__()
        self.src = src
        self.dest = dest
        self.flow_id = flow_id
        self.packet_no = packet_no
        self.timestamp = timestamp

    def reach_router(self, router, port_id):
        """Visitor method called by Router object.

        Instructs the calling router to forward this data packet to another
        router or the target host.

        Args: 
            router: The router this packet arrives at.
            port_id: The port where this packet came in from.
        """
        router.send(self, router.look_up(self.dest))

        
    def reach_host(self, host):
        """Visitor method called by Host object.
        
        Instructs the calling host to acknowledge this data packet.

        Args:
            host: The host this packet arrives at.
        """
        # Get acknowledgement number
        n = host.get_data(self.flow_id, self.packet_no)
        # Send AckPacket
        if n is not None:
            if n > self.packet_no:
                timestamp = self.timestamp
            else:
                timestamp = None
            host.send_except(AckPacket(
                self.dest, self.src, self.flow_id, n, timestamp))

class AckPacket(Packet):
    """Represents acknowledgement of a data packet."""

    _size = 64

    def __init__(self, src, dest, flow_id, packet_no, timestamp):
        """Creates an acknowledgement.

        Args:
            src: Host ID of the source.
            dest: Host ID of the target.
            flow_id: Flow ID the data packet belongs to.
            packet_no: Acknowledgement number.
            timestamp: Time when the data packet was sent.
        """
        super(AckPacket, self).__init__()
        self.src = src
        self.dest = dest
        self.flow_id = flow_id
        self.packet_no = packet_no
        self.timestamp = timestamp

    def reach_router(self, router, port_id):
        """Visitor method called by Router object.

        Instructs the calling router to forward this ack packet to another
        router or the source host.

        Args: 
            router: The router this packet arrives at.
            port_id: The port where this packet came in from.
        """
        router.send(self, router.look_up(self.dest))

    def reach_host(self, host):
        host.get_ack(self.flow_id, self.packet_no, self.timestamp)

class SonarPacket(Packet):
    """Signal for network exploration using Dijkstra's algorithm.

    This SonarPacket is passed around the system
    and keeps track of which port is the best for
    a specific host
    """
    _size = 64

    def __init__(self, src, version):
        """Creates a SonarPacket

        Attributes:
            src: The source host initiating network exploration.
            version: The round number of dynamic routing.
        """
        super(SonarPacket, self).__init__()
        self.src = src
        self.version = version

    def reach_router(self, router, port_id):
        """Visitor method called by Router object.

        For a given source and within the same version, if this SonarPacket 
        comes first, records <port_id> in reverse routing table and broadcasts 
        this packet to all directions except <port_id>.

        Args: 
            router: The router this packet arrives at.
            port_id: The port where this packet came in from.
        """
        src = self.src
        vtable = router.table_version
        version = self.version
        if src not in vtable or vtable[src] < version:
            vtable[src] = version
            router.table_reverse[src] = port_id
            router.send_except(self, port_id)

    def reach_host(self, host):
        """Visitor method called by Host object.

        Sends back an EchoPacket.

        Args: 
            host: The host this packet arrives at.
        """
        host.send_except(EchoPacket(self.src, host.dev_id, self.version))

class EchoPacket(Packet):
    """A candidate target's response to network exploration.

    An EchoPacket is sent when a SonarPacket arrives to a host.
    """
    _size = 64

    def __init__(self, src, dest, version):
        """Initiates an EchoPacket

        Attributes:
            src: The source host initiating network exploration.
            dest: The target host responding to incoming SonarPacket.
            version: The round number of dynamic routing.
        """
        super(EchoPacket, self).__init__()
        self.src = src
        self.dest = dest
        self.version = version

    def reach_router(self, router, port_id):
        """Visitor method called by Router object.

        If the version number matches with that of <router>, update the routing 
        table for <router> and forward this packet back to the source using
        reverse routing table built by SonarPacket.

        Args: 
            router: The router this packet arrives at.
            port_id: The port where this packet came in from.
        """
        src = self.src
        vtable = router.table_version
        if src in vtable and vtable[src] == self.version:
            router.table_forward[self.dest] = port_id
            router.send(self, router.table_reverse[src])

    def reach_host(self, host):
        """Visitor method called by Host object.

        The source host ignores EchoPacket.

        Args: 
            host: Doesn't matter.
        """
        pass

class RoutingPacket(Packet):
    """Routing with mixed Dijkstra and Bellman-Ford algorithms.

    The RoutingPacket is passed around the system to find the fastest 
    path to hosts.
    """

    _size = 64

    def __init__(self, start_id, recorded_time, static=False):
        """
        Initiates RoutingPacket

        Args/private variables:
            start_id: initiating router ID 
            recorded_time: initially the current time
            end_id: the host or router ID
            passedTable: the dictionary containing routing table
            passedTimeTable: the dictionary containing the fastest times

        Attributes:

        """
        super(RoutingPacket, self).__init__()
        self.start_id = start_id
        self.recorded_time = recorded_time
        self.end_id = None
        self.passedTable = None
        self.passedTimeTable = None
        self.stat = static
    
    def reach_router(self, router, port_id):
        """Visitor method called by Router object.

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
        if self.stat:
            if self.start_id not in router.table:
                router.table[self.start_id] = port_id
                router.timeTable[self.start_id] = router.env.now - self.recorded_time
            router.send_except(self, port_id)
        else:
            if self.start_id == router.dev_id:
                if self.passedTable is None:
                    if self.end_id not in router.table \
                       or router.timeTable[self.end_id] >= self.recorded_time:
                        router.table[self.end_id] = port_id
                        router.timeTable[self.end_id] = self.recorded_time
                else:
                    for host in self.passedTable:
                        if host not in router.timeTable or (
                            host in self.passedTimeTable and 
                            router.timeTable[host] >= 
                            (self.passedTimeTable[host] + self.recorded_time)
                        ):
                            router.table[host] = port_id
                            if host in self.passedTimeTable:
                                router.timeTable[host] = (
                                    self.passedTimeTable[host] + 
                                    self.recorded_time)
                            else:
                                router.timeTable[host] = self.recorded_time
            else:
                self.passedTable = copy.deepcopy(router.table)
                self.passedTimeTable = copy.deepcopy(router.timeTable)
                self.recorded_time = router.env.now - self.recorded_time
                router.send(self, port_id)
    
    def reach_host(self, host):
        """Visitor method called by Host object.

        Args:
            host: The host that the packet arrived at.

        Purpose:
            If the end_id is not initialized, then the packet records
            how long it took for the packet to get to the host. 
            it then sends the packet to the router it came from. 
        """
        if self.stat:
            pass
        elif self.end_id == None:
            self.recorded_time = host.env.now - self.recorded_time
            self.end_id = host.dev_id;
            host.send_except(self)
