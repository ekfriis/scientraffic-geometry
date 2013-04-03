#!/usr/bin/env python

"""

Smear/clean community association by associated nodes
to their k-nearest neighbors.

Any nodes belonging to communtiny# -1 will be consisered
orphans and reasigned.

"""

import argparse
import gzip
import logging
import operator

import numpy as np
from scipy.spatial import cKDTree as KDTree

import topotools

log = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('input', metavar='communities.gz',
                        help='Gzipped communities')
    parser.add_argument(
        'output', metavar='communities.smeared.gz',
        help='Gzipped output communities')

    parser.add_argument('-k', default=30, type=int, metavar='K',
                        help='k neigherest neighbors for the association')

    parser.add_argument('--bbox', nargs=4, type=float, metavar='x',
                        help='Only consider nodes within bbox')

    parser.add_argument('--only-orphans', default=False, action='store_true',
                        dest='only_orphans',
                        help='If specified, only reassign orphans.')

    args = parser.parse_args()

    logging.basicConfig()
    log.setLevel(logging.INFO)

    # Get generator of clustered nodes
    # We keep these in OSRM units for now.
    good_nodes = []
    orphans = []
    for node in topotools.read_clusters(args.input, args.bbox, scale=False):
        if node.clust != -1:
            good_nodes.append(node)
        else:
            orphans.append(node)
    log.info("Read %i good nodes and  %i orphans.", len(good_nodes),
             len(orphans))

    points = np.array([(x.lon, x.lat) for x in good_nodes], dtype=int)
    current_clusters = np.array([x.clust for x in good_nodes], dtype=int)

    log.info("Constructing KD-tree")
    tree = KDTree(points)

    new_good_nodes = good_nodes
    if not args.only_orphans:
        log.info("Reassigning all nodes...")
        new_good_nodes, reassigned = topotools.reassign_clusters(
            good_nodes, tree, current_clusters, args.k)
        log.info("%i nodes changed clusters", reassigned)
    log.info("Reassigning orphans")
    adopted_orphans, reassigned = topotools.reassign_clusters(
        orphans, tree, current_clusters, args.k)
    log.info("%i orphans were adopted", reassigned)

    log.info("Done adopting orphans")
    all_nodes = new_good_nodes + adopted_orphans
    all_nodes.sort(key=operator.attrgetter('clust'))

    log.info("Writing to %s", args.output)
    with gzip.open(args.output, 'wb') as outputfd:
        for node in all_nodes:
            outputfd.write(' '.join(str(x) for x in [
                node.id, node.lat, node.lon, node.clust, '\n'
            ]))
