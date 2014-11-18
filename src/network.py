#!/usr/bin/env python
from __future__ import division, print_function
import simpy
import os
from simpy_ext import SizedStore
from device import Host, Link, Router, PipePair
from packet import DataPacket
from flow import Flow

class Network(object):

    """docstring for Network"""

    def parse_network(self, filename):
        curpath = os.path.dirname(__file__)
        filepath = os.path.abspath(os.path.join(curpath, "..", "testcases", filename))
        stream = open(filepath,'r')
        sect_idx = 0
        for line in stream:
            fields = line.strip().split()
            if line[0] == '-':
                sect_idx += 1
            elif sect_idx == 0:
                h = Host(self.env, fields[0])
                self.hosts.append(h)
                self._nodes[fields[0]] = h
            elif sect_idx == 1:
                r = Router(self.env, fields[0])
                self.routers.append(r)
                self._nodes[fields[0]] = r
            elif sect_idx == 2:
                fields[3:6] = map(float, fields[3:6])
                l = Link(self.env, fields[0], fields[3], fields[4], fields[5])
                self.links.append(l)
                self._nodes[fields[0]] = l
                self._edges.append((fields[0], fields[1]))
                self._edges.append((fields[0], fields[2]))
            else:
                fields[3:4] = map(float, fields[3:5])
                f = Flow(self.env, fields[0], fields[1], fields[2], fields[3], fields[4])
                self.flows.append(f)
        stream.close()

        # Establish communication between devices
        for e in self._edges:
            pipe01 = simpy.Store(self.env)
            pipe10 = simpy.Store(self.env)
            port0 = PipePair(pipe10, pipe01)
            port1 = PipePair(pipe01, pipe10)
            self._nodes[e[0]].add_port(e[1], port0)
            self._nodes[e[1]].add_port(e[0], port1)

        for f in self.flows:
            self._nodes[f.src].add_flow(f)

    def __init__(self, env, filename):
        super(Network, self).__init__()

        self.hosts = []
        self.routers = []
        self.links = []
        self.flows = []

        self._nodes = {}
        self._edges = []

        if env is None:
            env = simpy.Environment()
        self.env = env

        self.parse_network(filename)


    def run(self, until=None):
        return self.env.run(until=until)
    

if __name__ == '__main__':
    tc0 = Network(None, 'tc1.txt')
    tc0.run(0.5 + 0.15)
