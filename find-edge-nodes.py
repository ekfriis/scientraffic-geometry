#!/usr/bin/env python
'''

Keep only nodes on the edge of the communities.

'''


import argparse
from concurrent import futures
import itertools
import gzip
import logging
import math
import operator
import random

import geojson
from shapely.geometry import Point, asShape

import topotools

log = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('input', metavar='communities.gz',
                        help='Gzipped communities')
    parser.add_argument(
        'hulls', metavar='communities.hulls.json',
        help='GeoJSON with hulls')

    parser.add_argument(
        'output', metavar='communities.edges.gz',
        help='Gzipped output communities')

    parser.add_argument('--bbox', nargs=4, type=float, metavar='x',
                        help='Only consider nodes within bbox')

    parser.add_argument('--within', type=float, metavar='b', default=0.1,
                        help='Buffer value (in % of characteristic size)'
                        ' around the concave hull for keeping points.'
                        ' Default %(default)f')

    parser.add_argument('--keep', type=float, metavar='x', default='0.02',
                        help='Keep a random sampling of interior nodes. '
                        ' Default %(default)f')

    parser.add_argument('--threads', type=int, metavar='N', default=2,
                        help='Number of threads. Default %(default)f')

    args = parser.parse_args()

    logging.basicConfig()
    log.setLevel(logging.INFO)

    with open(args.hulls, 'r') as inputfd:
        features = geojson.load(inputfd)

    cluster_features = {}
    for feature in features['features']:
        cluster_id = feature['properties']['clust']
        cluster_features[cluster_id] = asShape(feature['geometry'])

    log.info("Loaded %i hulls", len(cluster_features))

    # Get generator of clustered nodes
    # We keep these in OSRM units for now.
    clustered_node_iters = itertools.groupby(
        topotools.read_clusters(args.input, args.bbox, scale=False),
        operator.attrgetter('clust')
    )

    # Get the ID, the hull (if it exists), and the nodes for each cluster
    clustered_nodes = (
        (clust, cluster_features.get(clust), list(nodes))
        for clust, nodes in clustered_node_iters
    )

    def find_edge_nodes(fargs):
        """ Find nodes are near the edge of the hull"""
        cluster, cluster_hull, nodes = fargs
        # There is no hull for this community, it's been deleted.
        if cluster_hull is None:
            log.error("Missing hull, keeping all nodes in cluster %i",
                      cluster)
            return len(nodes), nodes

        characteristic_size = math.sqrt(cluster_hull.area)
        allowed_distance = characteristic_size * args.within
        boundary = cluster_hull.boundary

        output = []
        for node in nodes:
            # check if it is an interior node
            point = Point((node.lon, node.lat))
            keep = False
            if random.random() < args.keep:
                keep = True
            elif point.distance(boundary) < allowed_distance:
                keep = True
            if keep:
                output.append(node)
        return len(nodes), output

    log.info("Spawning %i worker threads", args.threads)
    final_nodes = []
    total_nodes = 0
    with futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
        for processed_nodes, edge_nodes in executor.map(
                find_edge_nodes, clustered_nodes):
            total_nodes += processed_nodes
            final_nodes.extend(edge_nodes)
    log.info("Kept %i edge nodes out of %i", len(final_nodes), total_nodes)

    final_nodes.sort(key=operator.attrgetter('clust'))

    log.info("Writing to %s", args.output)
    with gzip.open(args.output, 'wb') as outputfd:
        for node in final_nodes:
            outputfd.write(' '.join(str(x) for x in [
                node.id, node.lat, node.lon, node.clust, '\n'
            ]))
