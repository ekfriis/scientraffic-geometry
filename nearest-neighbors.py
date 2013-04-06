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
    topotools.neighbors.log.setLevel(logging.DEBUG)
    #topotools.neighbors.log.setLevel(logging.INFO)

    nodes = topotools.io.read_clusters_as_recarray(
        args.input, args.bbox).view(np.recarray)

    # Order by cluster
    nodes.sort(order='clust')

    # Orphans have clustid = -1.  Find the first non orphan node.
    first_non_orphan_idx = None
    for idx, cluster in enumerate(nodes.clust):
        if cluster != -1:
            first_non_orphan_idx = idx
            break

    # Seperate good nodes and orphans
    good_nodes = nodes[first_non_orphan_idx:]
    orphans = nodes[0:first_non_orphan_idx]

    log.info("Read %i good nodes and  %i orphans.",
             len(good_nodes), len(orphans))

    # Make a ND-array view of the x-y points
    good_points = good_nodes[['lon', 'lat']].view('<i8').reshape(
        (good_nodes.size, 2))

    current_clusters = good_nodes.clust

    log.info("Constructing KD-tree")
    tree = KDTree(good_points)

    if not args.only_orphans:
        log.info("Reassigning all nodes...")
        new_clusters = topotools.reassign_clusters(
            good_points, tree, current_clusters, args.k)

        log.info("Upating cluster membership")
        changed = new_clusters != current_clusters
        nodes.clust = new_clusters
        log.info("Changed %i clusters", np.count_nonzero(changed))

    log.info("Reassigning orphans")
    orphan_points = orphans[['lon', 'lat']].view('<i8').reshape(
        (orphans.size, 2))
    new_orphan_clusters = topotools.reassign_clusters(
        orphan_points, tree, current_clusters, args.k)
    orphans.clust = new_orphan_clusters

    log.info("Done adopting orphans")

    sorted_indices = np.argsort(nodes.clust)

    log.info("Writing to %s", args.output)
    with gzip.open(args.output, 'wb') as outputfd:
        for id, lat, lon, clust in nodes[sorted_indices][
                ['id', 'lat', 'lon', 'clust']]:
            outputfd.write(' '.join(str(x) for x in [
                id, lat, lon, clust, '\n'
            ]))
