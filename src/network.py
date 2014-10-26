import simpy
from device import Host, Link, Router
from packet import DataPacket

class Network(object):
    """docstring for Network"""
    def __init__(self, env=None):
        super(Network, self).__init__()

        if env is None:
            env = simpy.Environment()
        self.env = env

    def run(until=None):
        return self.env.run(until=until)

def main():
    pass

if __name__ == '__main__':
    main()