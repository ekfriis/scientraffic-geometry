#!/usr/bin/env python

"""

Smear/clean community association by associated nodes
to their k-nearest neighbors.

Any nodes belonging to communtiny# -1 will be consisered
orphans and reasigned.

"""

import argparse
import itertools
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

    parser.add_argument('--threads', type=int, metavar='N', default=2,
                        help='Number of threads. Default %(default)f')

    args = parser.parse_args()

    logging.basicConfig()
    log.setLevel(logging.INFO)
    topotools.neighbors.log.setLevel(logging.DEBUG)
    #topotools.neighbors.log.setLevel(logging.INFO)

    # Get generator of clustered nodes
    # We keep these in OSRM units for now.
    good_nodes = []
    orphans = []
    log.info("Reading %s", args.input)
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

    if not args.only_orphans:
        log.info("Reassigning all nodes...")
        new_clusters = topotools.reassign_clusters_threaded(
            good_nodes, tree, current_clusters, args.k, args.threads)

        log.info("Upating cluster membership")
        changed = 0
        for i, (current, new_cluster) in enumerate(
                itertools.izip(current_clusters, new_clusters)):
            if current != new_cluster:
                changed += 1
                current_node = good_nodes[i]
                good_nodes[i] = topotools.NodeInfo(
                    current_node.id,
                    current_node.lat,
                    current_node.lon,
                    new_cluster)
        log.info("%i nodes changed clusters", changed)

    good_nodes.sort(key=operator.attrgetter('clust'))

    log.info("Reassigning orphans")
    new_orphan_clusters = topotools.reassign_clusters_threaded(
        orphans, tree, current_clusters, args.k, args.threads)

    for i in range(len(orphans)):
        current_node = orphans[i]
        orphans[i] = topotools.NodeInfo(
            current_node.id,
            current_node.lat,
            current_node.lon,
            new_orphan_clusters[i])

    log.info("Done adopting orphans")

    log.info("Writing to %s", args.output)
    with gzip.open(args.output, 'wb') as outputfd:
        for node in itertools.chain(orphans, good_nodes):
            outputfd.write(' '.join(str(x) for x in [
                node.id, node.lat, node.lon, node.clust, '\n'
            ]))
