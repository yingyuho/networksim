from __future__ import division, print_function
from functools import partial
from collections import defaultdict, deque
from operator import attrgetter

import simpy

from flow import GoBackNAcker
from packet import RoutingPacket, SonarPacket

class Device(object):
    """Superclass for Host, Router, and Link.

    Attributes:
        env: Simpy environment where the Device is stored.
        _dev_id: ID of the device.
        _ports: The ports available on the Device, where other devices are 
            attached.
        _max_degree: The maximum number of Devices that can be attached."""

    def __init__(self, env, dev_id):
        self.env = env
        self._dev_id = dev_id
        self._ports = {}
        
    @property
    def dev_id(self):
        """Unique ID of this device in the network."""
        return self._dev_id

    _max_degree = None

    @property
    def degree(self):
        """Number of other devices this device connects to."""
        return len(self._ports)

    @property
    def max_degree(self):
        """Maximal number of other devices this device can connect to
        or None if there is no upper limit."""
        return self._max_degree

    def add_port(self, adj_id, port):
        """Add and listen to an I/O port to this device."""
        if adj_id in self._ports:
            raise Exception('Duplicate port name')

        if self.max_degree is not None and self.degree >= self.max_degree:
            raise Exception('Connectd to too many devices')

        self._ports[adj_id] = port

    def send(self, packet, to_id):
        """Sends packet from the current Device to the other Device."""
        # self._ports[to_id].pipe_out.put(packet)
        self._ports[to_id].receive(packet, self.dev_id)

    def send_except(self, packet, except_id=None):
        for adj_id in self._ports:
            if except_id is None or adj_id != except_id:
                self.send(packet, adj_id)

    def receive(self, packet, from_id):
        """Receives packet for the current Device."""
        raise NotImplementedError()

    def activate_ports(self):
        """Activates ports for the current Device."""
        raise NotImplementedError()

    def init_routing(self):
        """Send a routing packet to all the ports."""
        yield self.env.timeout(0.1)
        while True:
            rp = RoutingPacket(self.dev_id, self.env.now)
            self.send_except(rp)
            yield self.env.timeout(5)
    def init_static_routing(self):
        """Send a routing packet to all the ports."""
        rp = RoutingPacket(self.dev_id, self.env.now, static = True)
        self.send_except(rp)
        yield self.env.event().succeed()

class Host(Device):
    """The Host class represents the hosts in the network.

    Attributes:
        flows: A list of the flows that send packets from this Host.
        _acker: 
        """

    _max_degree = 1

    def __init__(self, env, dev_id):
        """Constructor for Host object."""
        super(Host, self).__init__(env, dev_id)
        self._flows = {}
        self._acker = defaultdict(GoBackNAcker)
        self.env.process(self.proc_routing())

    def receive(self, packet, from_id):
        """Receives packets """
        packet.reach_host(self)

    def add_flow(self, flow):
        """Add/initiate flow to Host."""
        self._flows[flow.id] = flow

        def send_packet():
            """Sends packets according to flow."""
            while True:
                packet = yield flow.next_packet.get()
                for adj_id in self._ports:
                    self.send(packet, adj_id)

                print('{:.6f} send_data {} {} {} {}'.format(
                    self.env.now, flow.id, self.dev_id, 
                    packet.size, packet.packet_no))

        self.env.process(send_packet())

    def get_data(self, flow_id, packet_no):
        """Gets acknowledgement data for packets."""
        print('{:.6f} receive_data {} {} {}'.format(
            self.env.now, flow_id, self.dev_id, packet_no))
        n = self._acker[flow_id](packet_no)
        if n is not None:
            print('{:.6f} send_ack {} {} {}'.format(
                self.env.now, flow_id, self.dev_id, packet_no))
        return n

    def get_ack(self, flow_id, packet_no, timestamp):
        """Gets acknowledgement """
        print('{:.6f} receive_ack {} {} {}'.format(
            self.env.now, flow_id, self.dev_id, packet_no))
        self._flows[flow_id].get_ack(packet_no, timestamp)

    def proc_routing(self):
        ver = 0
        while True:
            self.send_except(SonarPacket(self.dev_id, ver))
            yield self.env.timeout(5)
            ver += 1

class BufferedCable(object):
    """The general object for a one-way connector between objects. Includes 
        buffers for packets.

    Attributes:
        rate: Link rate in Mbps.
        delay: Link delay in milliseconds.
        buf_size: Link buffer capacity in bytes.
        io: 

    """
    def __init__(self, link, src_id):

        self.link = link

        self.env = link.env

        self.link_id = link.dev_id
        self.src_id = src_id

        self.rate = link.rate
        self.delay = link.delay
        self.buf_size = 1000 * link.buf_size

        self._packet_queue = deque()

        self._buffer_level = (
            simpy.Container(self.env, capacity=self.buf_size),
            simpy.Container(self.env, capacity=self.buf_size)
        )

        self._cable = simpy.Store(self.env)

        self.env.process(self._feed_cable())

    def feed(self, packet):
        self.env.process(self._feed_buffer(packet))

    def _feed_buffer(self, packet):
        with self._buffer_level[0].put(packet.size) as req:
            ret = yield req | self.env.event().succeed()
            if req in ret:
                self._buffer_level[1].put(packet.size)
                self._packet_queue.append(packet)
                print('{:06f} buffer_diff {} {}'.format(
                    self.env.now, 
                    self.link_id, 
                    packet.size))
            else:
                if hasattr(packet, 'flow_id'):
                    print('{:06f} packet_loss {} {} {}'.format(
                        self.env.now, 
                        self.link_id, 
                        packet.flow_id, 
                        packet.packet_no))

    def _feed_cable(self):
        while True:
            yield self._buffer_level[1].get(1)
            packet = self._packet_queue.popleft()
            yield self._buffer_level[1].get(packet.size - 1)

            yield self.env.timeout(packet.size * 8 / (self.rate * 1.0E6))

            yield self._buffer_level[0].get(packet.size)

            print('{:06f} buffer_diff {} {}'.format(
                self.env.now, 
                self.link_id, 
                -1 * packet.size))

            print('{:06f} transmission {} {}'.format(
                self.env.now, 
                self.link_id, 
                packet.size))

            self.env.process(self._latency(packet))

    def _latency(self, packet):
        yield self.env.timeout(self.delay / 1.0E3)
        self.link.send_except(packet, self.src_id)

class Link(Device):
    """Full-duplex link between hosts and routers.

    Attributes:
        rate: Link rate in Mbps. Do not modify.
        delay: Link delay in milliseconds. Do not modify.
        buf_size: Link buffer capacity in kilobytes. Do not modify.
        _cables: 

    """

    _max_degree = 2

    def __init__(self, env, dev_id, rate, delay, buf_size):
        super(Link, self).__init__(env, dev_id)

        self.rate = rate
        self.delay = delay
        self.buf_size = buf_size

        self._cables = {}

    def add_port(self, adj_id, port):
        """Add and listen to an I/O port to this device."""
        super(Link, self).add_port(adj_id, port)

        self._cables[adj_id] = BufferedCable(self, adj_id)

    def receive(self, packet, from_id):
        self._cables[from_id].feed(packet)
        
class Router(Device):
    """Router creates the router objects in the network.

    Attributes:
        table: A dictionary mapping dest_id to link_id.
        timeTable: 
    """

    def __init__(self, env, dev_id):
        """Constructor for a Router."""
        super(Router, self).__init__(env, dev_id)
        self.table = {}
        self.timeTable = {}
        # self.env.process(self.init_routing())

        self.table_version = {}
        self.table_reverse = {}
        self.table_forward = {}

    def look_up(self, dest):
        if dest in self.table_forward:
            return self.table_forward[dest]
        # elif dest in self.table_reverse:
        #     return self.table_reverse[dest]
        else:
            return None

    def receive(self, packet, from_id):
        """Recieves a packet from a port if the packet is a routing packet.
        then, send the packet to all the other ports.
        """
        packet.reach_router(self, from_id)
