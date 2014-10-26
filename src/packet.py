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

class DataPacket(object):
    """docstring for DataPacket"""
    def __init__(self, src, dest, message):
        super(DataPacket, self).__init__()
        self.src = src
        self.dest = dest
        self.message = message
        