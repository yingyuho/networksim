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
    # Global aggregation
    buffer_level = defaultdict(int)

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

    output_sel = defaultdict(frozenset)

    for line in iter(stdin.readline, ''):
        fields = line.strip().split(' ', 2)
        if fields[0] != '#':
            raise Exception('Wrong log format')
        if len(fields) <= 1:
            break
        kind = fields[1]
        ids = fields[2].split()
        output_sel[kind] = frozenset(ids)
        # d = None
        # if kind == 'flow_send_rate':
        #     d = flow_send_sum
        # elif kind == 'host_send_rate':
        #     d = host_send_sum
        # elif kind == 'packet_loss_rate':
        #     d = packet_loss_sum
        # elif kind == 'packet_rtt':
        #     d = packet_rtt_sum
        # elif kind == 'link_flow_rate':
        #     d = link_flow_sum
        # elif kind == 'buf_level':
        #     d = buffer_level_sum
        # elif kind == 'window_size':
        #     d = window_size_sum

        # if d is not None:
        #     for i in ids:
        #         d[i] *= 0

    stream = read_input(stdin)
    keyfunc = time_binner(freq)

    for k, g in groupby(stream, keyfunc):
        t = k / freq

        zero_list = [
            link_flow_sum, host_send_sum, flow_send_sum, packet_loss_sum,
            packet_rtt_sum, packet_rtt_count, window_size_sum, 
            window_size_count, buffer_level_sum, buffer_level_count]

        for d in zero_list:
            for k in d:
                d[k] *= 0
        
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

        for name in output_sel['flow_send_rate']:
            print('{} flow_send_rate {} {}'.format(t, name,
                flow_send_sum[name] * 8 / 1.0E6 * freq))

        for name in output_sel['host_send_rate']:
            print('{} host_send_rate {} {}'.format(t, name,
                host_send_sum[name] * 8 / 1.0E6 * freq))

        for name in output_sel['packet_loss_rate']:
            print('{} packet_loss_rate {} {}'.format(t, name,
                packet_loss_sum[name] * freq))

        for name in output_sel['packet_rtt']:
            if packet_rtt_count[name]:
                print('{} packet_rtt {} {}'.format(t, name,
                    packet_rtt_sum[name] / packet_rtt_count[name]))

        for name in output_sel['link_flow_rate']:
            print('{} link_flow_rate {} {}'.format(t, name, 
                link_flow_sum[name] * 8 / 1.0E6 * freq))

        for name in output_sel['buf_level']:
            if buffer_level_count[name]:
                print('{} buf_level {} {}'.format(t, name, 
                    buffer_level_sum[name] / 1000 / buffer_level_count[name]))

        for name in output_sel['window_size']:
            if window_size_count[name]:
                print('{} window_size {} {}'.format(t, name,
                    window_size_sum[name] / window_size_count[name]))

if __name__ == '__main__':
    main()