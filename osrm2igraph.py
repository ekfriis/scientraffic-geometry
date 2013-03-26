#!/usr/bin/env python
'''

Convert the OSRM binary format to igraph
----------------------------------------

Author: Evan K. Friis

'''

import argparse
import logging

import osrm

log = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('input', metavar='input.osrm',
                        help='OSRM binary file')
    parser.add_argument('output', metavar='output.pkl.gz',
                        help='Output file name')

    args = parser.parse_args()

    logging.basicConfig()
    log.setLevel(logging.INFO)
    osrm.log.setLevel(logging.INFO)

    graph = osrm.construct_igraph(
        args.input, simplify=True, remove_disconnected=True)

    log.info("Saving graph to %s", args.output)
    graph.write(args.output, format='picklez')
