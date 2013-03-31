#!/usr/bin/env python

"""

Remove 'islands', and spiky or 'taily' communities, by identifying problem
nodes and moving them to other communities.

Islands are removed by an alpha shape cut.

Spiky shapes are removed by a requirement on the
concave/convex hull area ratio.

Orphaned nodes are assigned to their nearest neighbors.

"""

import argparse
import itertools
import gzip
import logging
import math
import operator

import numpy as np
from shapely.geometry import Point
from scipy.spatial import KDTree

import topotools

log = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('input', metavar='communities.gz',
                        help='Gzipped communities')
    parser.add_argument(
        'output', metavar='communities.cleaned.gz',
        help='Gzipped output communities')

    parser.add_argument('--bbox', nargs=4, type=float, metavar='x',
                        help='Only consider nodes within bbox')

    parser.add_argument('--alphacut', type=float, metavar='x', default=10,
                        help='Concave hull alpha cut. Default %(default)f')

    parser.add_argument('--buffer', type=float, metavar='b', default=0.03,
                        help='Buffer value (in % of characteristic size)'
                        ' around the concave hull for keeping points.'
                        ' Default %(default)f')

    parser.add_argument('--convexity', type=float, metavar='x', default=0.5,
                        help='Minimum on the ratio of '
                        'the concave/convex area.  Default %(default)f')

    args = parser.parse_args()

    logging.basicConfig()
    log.setLevel(logging.INFO)
    topotools.log.setLevel(logging.INFO)

    # Get generator of clustered nodes
    # We keep these in OSRM units for now.
    clustered_nodes = itertools.groupby(
        topotools.read_clusters(args.input, args.bbox, scale=False),
        operator.attrgetter('clust')
    )

    # keep a list of nodes we orphan
    orphans = []
    good_nodes = []

    for clustidx, nodes in clustered_nodes:
        node_list = list(nodes)
        points = np.array([(x.lon, x.lat) for x in node_list], dtype=float)
        log.info("Cleaning community %i with %i points",
                 clustidx, len(points))
        concave_hull = topotools.get_concave_hull(points, args.alphacut)
        # So tiny it doesn't even have a hull
        if concave_hull is None:
            log.info("No concave hull, orphaning judicously")
            orphans.extend(node_list)
            continue

        concave_area = concave_hull.area
        log.info("Found concave hull with area %g", concave_area)
        convex_hull = topotools.get_convex_hull(points)
        convex_area = convex_hull.area
        log.info("Found convex hull with area %g", convex_area)

        if not convex_area:
            log.warning("Community has no area! Discarding all nodes")
            orphans.extend(node_list)
            continue

        if concave_area < convex_area * args.convexity:
            log.info("Shape is to concave (%g/%g = %g < %0.2f)",
                     concave_area, convex_area,
                     concave_area / convex_area, args.convexity)
            orphans.extend(node_list)
            continue

        # Trim tails on the concave hulls.  Tails are long, thin,
        # features which are created when the community goes
        # down a road away from the main group.
        # TODO

        buffered = concave_hull.buffer(
            math.sqrt(concave_hull.area) * args.buffer)

        log.info("Pruning %i nodes using concave hull", len(points))
        # Exclude points outside the hull.
        bad = 0
        for node, point in itertools.izip(node_list, points):
            if Point(point).within(buffered):
                good_nodes.append(node)
            else:
                bad += 1
                orphans.append(node)
        log.info("After pruning, %i bad nodes are orphaned", bad)

    log.info("Constructing KDtree for good nodes to adopt %i total orphans",
             len(orphans))
    good_points = np.array([(x.lon, x.lat) for x in good_nodes], dtype=float)
    kdtree = KDTree(good_points)

    adopted_orphans = []
    for orphan in orphans:
        # Find 10 nearest neighbors (5% error is allowed)
        distances, neighbors = kdtree.query(
            (orphan.lon, orphan.lat), k=15, eps=0.05)
        neighbor_cluster_membership = np.array(
            [good_nodes[i].clust for i in neighbors])
        # http://stackoverflow.com/questions/12297016/
        # how-to-find-most-frequent-values-in-numpy-ndarray
        clusters, indices = np.unique(neighbor_cluster_membership,
                                      return_inverse=True)
        dominant_neighbor_cluster = clusters[np.argmax(np.bincount(indices))]
        # Make a new node w/ the updated cluster
        adopted_orphans.append(
            topotools.NodeInfo(
                orphan.id,
                orphan.lat,
                orphan.lon,
                dominant_neighbor_cluster
            )
        )

    log.info("Done adopting orphans")
    all_nodes = good_nodes + adopted_orphans
    all_nodes.sort(key=operator.attrgetter('clust'))

    log.info("Writing to %s", args.output)
    with gzip.open(args.output, 'wb') as outputfd:
        for node in all_nodes:
            outputfd.write(' '.join(str(x) for x in [
                node.id, node.lat, node.lon, node.clust, '\n'
            ]))
