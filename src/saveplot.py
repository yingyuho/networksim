#!/usr/bin/env python
import sys
from collections import namedtuple, OrderedDict, defaultdict

import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

PlotSpec = namedtuple('PlotSpec', 'title xlabel ylabel scale')

class PlotData(object):
    def __init__(self):
        self.t = []
        self.v = []

def data_stream(f=sys.stdin):
    while True:
        args = f.readline().split()
        if not args:
            break
        t = float(args[0])
        k = args[1]
        i = args[2]
        v = float(args[3])
        yield (t, k, i, v)

def main():
    figname = sys.argv[1]

    time_label = 'Time (s)'

    plot_specs = {
        'packet_loss_rate':
            PlotSpec('Packet Loss', time_label, 'pkts/s', 1),
        'buf_level':
            PlotSpec('Buffer Occupany', time_label, 'KB', 1), 
        'link_flow_rate':
            PlotSpec('Link Flow Rate', time_label, 'Mbps', 1),
        'packet_rtt':
            PlotSpec('Round-trip Delay', time_label, 'ms', 1000),
        'flow_send_rate':
            PlotSpec('Flow Send Rate', time_label, 'Mbps', 1),
        'host_send_rate':
            PlotSpec('Host Send Rate', time_label, 'Mbps', 1),
        'window_size':
            PlotSpec('Window Size', time_label, 'pkts', 1)
    }

    plot_sel = [
        'packet_loss_rate',
        'buf_level',
        'link_flow_rate',
        'packet_rtt',
        'flow_send_rate',
        'window_size'
    ]

    plot_data_dict = {}

    inf = float('inf')

    if len(sys.argv) > 2:
        t_max = float(sys.argv[2])
    else:
        t_max = None

    t_auto_max = 0

    for k in plot_specs:
        plot_data_dict[k] = defaultdict(PlotData)

    for t, k, i, v in data_stream():
        data = plot_data_dict[k][i]
        data.t.append(t)
        data.v.append(v)

    num_subplots = len(plot_sel)

    fig = plt.figure(figsize=(10, 10))
    ax = []

    for j, k in enumerate(plot_sel):
        subp = plt.subplot(num_subplots, 1, j + 1)
        ax.append(subp)
        scale = plot_specs[k].scale
        for i, data in plot_data_dict[k].iteritems():
            plt.plot(data.t, np.array(data.v) * scale, label=i)
            t_auto_max = max(t_auto_max, data.t[-1])
        plt.title(plot_specs[k].title)
        plt.ylabel(plot_specs[k].ylabel)
        if j == num_subplots - 1:
            plt.xlabel(plot_specs[k].xlabel)
        else:
            subp.axes.xaxis.set_ticklabels([])
        plt.legend(loc='lower right', numpoints=1)

    if t_max is None:
        t_max = t_auto_max

    for j in range(num_subplots):
        ax[j].set_xlim((0, t_max))
        ax[j].set_ylim(bottom=0)

    plt.tight_layout()
    if figname == '-':
        plt.show()
    else:
        plt.savefig(figname)

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        sys.stderr.writelines([
            'Usage: ',
            '{} output [maxtime]\n'.format(sys.argv[0]),
            'Set output = \'-\' to display plots on screen instead.\n\n'])
    else:
        main()