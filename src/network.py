#!/usr/bin/env python
from __future__ import division, print_function
import simpy
import os
import sys
from device import Host, Link, Router
from packet import DataPacket
from flow import TCPTahoeFlow, TCPRenoFlow, FastTCPFlow, CubicTCPFlow

class Network(object):

    """The Network Simulator is initialized here.

    Attributes:
        hosts: List of all Host objects in the network.
        routers: List of all Router objects in the network.
        links: List of all Link objects in the network.
        flows: List of all Flow objects in the network.
        _nodes: Contains additional information about each Host/Router.
        _edges: Contains additional information about each Link.
    """

    def __init__(self, env, filename, algorithm=FastTCPFlow, alg_args=None):
        """Constructor for the Network object"""
        super(Network, self).__init__()

        self.algorithm = algorithm

        self.hosts = []
        self.routers = []
        self.links = []
        self.flows = []

        self._nodes = {}
        self._edges = []

        # Initiates new environment to simulate network
        if env is None:
            env = simpy.Environment()
        self.env = env
        
        self.parse_network(filename)

    def parse_network(self, filename):
        """This method parses the network from the provided text file."""
        if filename:
            stream = open(filename, 'r')
        else:
            stream = sys.stdin
        sect_idx = 0
        for line in stream:
            fields = line.strip().split()
            if not fields:
                continue
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
            elif sect_idx == 3:
                fields[3:4] = map(float, fields[3:5])
                f = self.algorithm(
                    self.env, 
                    fields[0], fields[1], fields[2], fields[3], fields[4])
                self.flows.append(f)
            elif sect_idx == 4:
                print('# ' + line.strip())
        print('#')
        stream.close()

        # Establish communication between devices
        for e in self._edges:
            n = (self._nodes[e[0]], self._nodes[e[1]])
            n[0].add_port(e[1], n[1])
            n[1].add_port(e[0], n[0])

        # Add Flows to Hosts
        for f in self.flows:
            self._nodes[f.src].add_flow(f)

    def run(self, until=None):
        """Initiates run of simulation environment."""
        return self.env.run(until=until)
    

if __name__ == '__main__':
    alg_dict = {
        'tahoe': TCPTahoeFlow,
        'reno': TCPRenoFlow,
        'fast': FastTCPFlow,
        'cubic': CubicTCPFlow
    }

    usage = ''.join([
        'Usage: ',
        '{} sim_time [flow_alg=fast]\n'.format(sys.argv[0]),
        'flow_alg = {}.\n\n'.format(', '.join(alg_dict))])

    if len(sys.argv) < 2:
        sys.stderr.write(usage)
        sys.exit(0)

    try:
        sim_time = float(sys.argv[1])

        if len(sys.argv) > 2:
            alg = alg_dict[sys.argv[2]]
        else:
            alg = FastTCPFlow
    except:
        sys.stderr.write(usage)
        sys.exit(0)

    sim = Network(None, None, alg)
    sim.run(sim_time)
