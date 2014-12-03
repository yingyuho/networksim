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

def main(freq=1):
    stream = read_input(stdin)
    keyfunc = time_binner(freq)

    # Global aggregation
    buffer_level = defaultdict(int)

    for k, g in groupby(stream, keyfunc):
        t = k / freq

        # Per interval aggregation
        link_flow_sum = defaultdict(int)
        
        for val in g:
            kind = val[1]

            # print('{:.6f} {}'.format(t, val))

            if kind == 'transmission':
                link_id = val[2]
                link_flow_sum[link_id] += int(val[3])
            elif kind == 'buffer_diff':
                link_id = val[2]
                buffer_level[link_id] += int(val[3])
            else:
                pass

        for link_id, amount in link_flow_sum.iteritems():
            print('{} link_flow_rate {} {}'.format(t, link_id, 
                amount * 8 / 1.0E6 * freq))

        for link_id, amount in buffer_level.iteritems():
            print('{} buf_level {} {}'.format(t, link_id, 
                amount / 1000))

if __name__ == '__main__':
    main()