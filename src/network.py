from __future__ import division, print_function
import simpy
import os
from device import Host, Link, Router
from packet import DataPacket
from flow import Flow

class Network(object):

    """docstring for Network"""

    def parse_network(self,filename):
        curpath = os.path.dirname(__file__)
        filepath = os.path.abspath(os.path.join(curpath, "..", "testcases", filename))
        f = open(filepath,'r')
        sect_idx = 0
        for line in f:
            if line[0] == '-':
                sect_idx += 1
            elif sect_idx == 0:
                h = Host(self.env, line[0:2])
                self.hosts.append(h)
            elif sect_idx == 1:
                r = Router(self.env, line[0:2])
                self.routers.append(r)
            elif sect_idx == 2:
                arr = line.split()
                l = Link(self.env, arr[0], arr[3], arr[4], arr[5])
                # Discuss changing constructor for Links, getting rid of the "attach"
                # method for device. Unless these attachments are dynamic, there's no
                # point in making a method to attach them as we go along...
                self.links.append(l)
            else:
                arr = line.split()
                f = Flow(self.env, arr[0], arr[1], arr[2], arr[3], arr[4])
                self.flows.append(f)
        f.close()
                

    def __init__(self, env, filename):
        super(Network, self).__init__()

        self.hosts = []
        self.routers = []
        self.links = []
        self.flows = []

        if env is None:
            env = simpy.Environment()
        self.env = env

        self.parse_network(filename)


    def run(until=None):
        return self.env.run(until=until)
    

if __name__ == '__main__':
    tc0 = Network(None, 'tc0.txt')
