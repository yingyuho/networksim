#!/usr/bin/env python
from __future__ import division, print_function
from sys import argv, stdin
from itertools import groupby
from collections import defaultdict

def read_input(f):
    for line in iter(f.readline, ''):
        yield line.rstrip('\n').split(' ')

def time_binner(freq):
    def keyfunc(args):
        return int(freq * float(args[0]))
    return keyfunc

def main(freq=5):
    stream = read_input(stdin)
    keyfunc = time_binner(freq)

    # Global aggregation
    buffer_level = defaultdict(int)

    for k, g in groupby(stream, keyfunc):
        t = k / freq

        # Per interval aggregation
        link_flow_sum = defaultdict(int)
        host_send_sum = defaultdict(int)
        flow_send_sum = defaultdict(int)
        packet_loss_sum = defaultdict(int)
        packet_rtt_sum = defaultdict(float)
        packet_rtt_count = defaultdict(int)
        window_size_sum = defaultdict(int)
        window_size_count = defaultdict(int)
        buffer_level_sum = defaultdict(int)
        buffer_level_count = defaultdict(int)
        
        for val in g:
            kind = val[1]

            # print('{:.6f} {}'.format(t, val))

            if kind == 'send_data':
                flow_id = val[2]
                host_id = val[3]
                amount = int(val[4])
                flow_send_sum[flow_id] += amount
                host_send_sum[host_id] += amount
            elif kind == 'receive_data':
                pass
            elif kind == 'send_ack':
                pass
            elif kind == 'receive_ack':
                pass
            elif kind == 'packet_loss':
                link_id = val[2]
                packet_loss_sum[link_id] += 1
            elif kind == 'packet_rtt':
                flow_id = val[2]
                packet_rtt_sum[flow_id] += float(val[3])
                packet_rtt_count[flow_id] += 1   
            elif kind == 'transmission':
                link_id = val[2]
                link_flow_sum[link_id] += int(val[3])
            elif kind == 'buffer_diff':
                link_id = val[2]
                buffer_level[link_id] += int(val[3])
                buffer_level_sum[link_id] += buffer_level[link_id]
                buffer_level_count[link_id] += 1
            elif kind == 'window_size':
                flow_id = val[2]
                window_size_sum[flow_id] += int(float(val[3]))
                window_size_count[flow_id] += 1
            else:
                pass

        for flow_id, amount in flow_send_sum.iteritems():
            print('{} flow_send_rate {} {}'.format(t, flow_id,
                amount * 8 / 1.0E6 * freq))

        for host_id, amount in host_send_sum.iteritems():
            print('{} host_send_rate {} {}'.format(t, host_id,
                amount * 8 / 1.0E6 * freq))

        for link_id, amount in packet_loss_sum.iteritems():
            print('{} packet_loss_rate {} {}'.format(t, link_id,
                amount * freq))

        for flow_id, amount in packet_rtt_sum.iteritems():
            print('{} packet_rtt {} {}'.format(t, flow_id,
                amount / packet_rtt_count[flow_id]))

        for link_id, amount in link_flow_sum.iteritems():
            print('{} link_flow_rate {} {}'.format(t, link_id, 
                amount * 8 / 1.0E6 * freq))

        for link_id, amount in buffer_level_sum.iteritems():
            print('{} buf_level {} {}'.format(t, link_id, 
                amount / 1000 / buffer_level_count[link_id]))

        for flow_id, amount in window_size_sum.iteritems():
            print('{} window_size_rate {} {}'.format(t, flow_id,
                amount / window_size_count[flow_id]))

if __name__ == '__main__':
    main()