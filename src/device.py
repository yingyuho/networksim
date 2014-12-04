from __future__ import division, print_function
from functools import partial
from collections import defaultdict
from operator import attrgetter

import simpy

from simpy_ext import SizedStore
from flow import GoBackNAcker
from packet import RoutingPacket, SonarPacket

class PipePair(object):
    """A named two-tuple of :class:`~simpy.core.Environment` objects for
    inter-device communication.
    """
    def __init__(self, pipe_in, pipe_out):
        self.pipe_in = pipe_in
        self.pipe_out = pipe_out

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

    def _add_packet_listener(self, adj_id, port):
        """Adds a listener to the port. Used in add_port."""
        def listener():
            while True:
                packet = yield port.pipe_in.get()
                self.receive(packet, adj_id)
        self.env.process(listener())

    def add_port(self, adj_id, port):
        """Add and listen to an I/O port to this device."""
        if adj_id in self._ports:
            raise Exception('Duplicate port name')

        if self.max_degree is not None and self.degree >= self.max_degree:
            raise Exception('Connectd to too many devices')

        self._ports[adj_id] = port

        # Add a listener process
        self._add_packet_listener(adj_id, port)

    def send(self, packet, to_id):
        """Sends packet from the current Device to the other Device."""
        self._ports[to_id].pipe_out.put(packet)

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
            yield self.env.timeout(1)
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
        self.env.process(self.init_static_routing())

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
        buf_size: Link buffer capacity in kilobytes.
        io: 

    """
    def __init__(self, env, link_id, src_id, rate, delay, buf_size):
        self.env = env

        self.link_id = link_id
        self.src_id = src_id

        self.rate = rate
        self.delay = delay
        self.buf_size = buf_size

        # Packet sizes are measured in bytes. Hence the factor 1024. 
        self._packet_buffer = SizedStore(
            self.env, 1024 * self.buf_size, attrgetter('size'))

        self._cable = simpy.Store(env)

        self.io = PipePair(simpy.Store(env), simpy.Store(env))

        self.env.process(self._feed_buffer())
        self.env.process(self._feed_cable())

    def _feed_buffer(self):
        while True:
            packet = yield self.io.pipe_in.get()
            # print('At Packet {0}'.format(packet.packet_no))
            # print('Buffer level: {}'.format(self._packet_buffer._level))

            with self._packet_buffer.put(packet) as req:
                ret = yield req | self.env.event().succeed()
                if req in ret:
                    print('{:06f} buffer_diff {} {}'.format(
                        self.env.now, 
                        self.link_id, 
                        packet.size))
                else:
                    print('{:06f} packet_loss {} {} {}'.format(
                        self.env.now, 
                        self.link_id, 
                        packet.flow_id, 
                        packet.packet_no))

    def _feed_cable(self):
        while True:            
            packet = yield self._packet_buffer.get()

            print('{:06f} buffer_diff {} {}'.format(
                self.env.now, 
                self.link_id, 
                -1 * packet.size))

            yield self.env.timeout(packet.size * 8 / (self.rate * 1.0E6))

            print('{:06f} transmission {} {}'.format(
                self.env.now, 
                self.link_id, 
                packet.size))

            self.env.process(self._latency(packet))

    def _latency(self, packet):
        yield self.env.timeout(self.delay / 1.0E3)
        self.io.pipe_out.put(packet)

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

        self._cables[adj_id] = BufferedCable(
            self.env, self.dev_id, adj_id, 
            self.rate, self.delay, self.buf_size)

        def listener(adj_id):
            while True:
                packet = yield self._cables[adj_id].io.pipe_out.get()
                for to_id in self._ports:
                    if to_id != adj_id:
                        self.send(packet, to_id)

        self.env.process(listener(adj_id))

    def receive(self, packet, from_id):
        self._cables[from_id].io.pipe_in.put(packet)
        
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
        self.env.process(self.init_routing())

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
