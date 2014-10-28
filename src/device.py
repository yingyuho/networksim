from __future__ import division, print_function
import simpy

class Device(object):
    """docstring for Device"""

    def __init__(self, env, dev_id):
        super(Device, self).__init__()
        self._env = env
        self._dev_id = dev_id
        self._ports = {}
        
    @property
    def dev_id(self):
        """Unique ID of this device in the network.
        """
        return self._dev_id

    _max_degree = None

    @property
    def max_degree(self):
        """Maximal number of other devices this device can connect to
        or None if there is no upper limit.
        """
        return self._max_degree

    def attach(to_dev):
        """Attach this device to another bidirectionally.
        """
        for d0, d1 in ((self, to_dev), (to_dev, self)):
            if d0.max_degree is None or len(d0._ports) < d0.max_degree:
                d0._ports[d1._dev_id] = d1
            else:
                # TODO: Define our own exception class
                raise Exception('Too many attachments')

    def send(packet, to_id):
        self._ports[to].receive(packet, self._dev_id)

    def receive(packet, from_id):
        raise NotImplementedError()

class Host(Device):
    """docstring for Host"""

    _max_degree = 1

    def __init__(self, env, dev_id):
        super(Host, self).__init__(env, dev_id)

    def receive(packet):
        packet.reach_host(self)

class Link(Device):
    """Full-duplex link"""

    _max_degree = 2

    def __init__(self, env, dev_id, rate_mbps, delay_ms, buffer_kbyte):
        super(Link, self).__init__(env, dev_id)
        self.rate_mbps = rate_mbps
        self.delay_ms = delay_ms
        self.buffer_kbyte = buffer_kbyte

    def receive(packet):
        # TODO
        raise NotImplementedError()
        
class Router(Device):
    """docstring for Router"""

    _max_degree = None

    def __init__(self, env, dev_id):
        super(Router, self).__init__(env, dev_id)
        self._table = {}

    def look_up(dest_id):
        return self._table[dest]

    def receive(packet):
        packet.reach_router(self)
        