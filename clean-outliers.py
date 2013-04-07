#!/usr/bin/env python
'''

Remove objects which lie outside the concave hulls.

'''


import argparse
from concurrent import futures
import itertools
import gzip
import logging
import math
import operator

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
        'output', metavar='communities.cleaned.gz',
        help='Gzipped output communities')

    parser.add_argument('--bbox', nargs=4, type=float, metavar='x',
                        help='Only consider nodes within bbox')

    parser.add_argument('--buffer', type=float, metavar='b', default=0.05,
                        help='Buffer value (in % of characteristic size)'
                        ' around the concave hull for keeping points.'
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

    log.info("Loaded %i hulls", len(features))

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

    def associate_nodes(fargs):
        """ Find nodes which are within the hull """
        cluster, cluster_hull, nodes = fargs
        # There is no hull for this community, it's been deleted.
        # Orphan all nodes.
        if cluster_hull is None:
            log.info("Missing hull, orphaning all nodes in cluster %i",
                     cluster)
            output = [topotools.NodeInfo(
                orphan.id, orphan.lat, orphan.lon, -1)
                for orphan in nodes]
            return len(output), output

        characteristic_size = math.sqrt(cluster_hull.area)
        allowed_distance = characteristic_size * args.buffer
        buffered = cluster_hull.buffer(allowed_distance)

        output = []
        num_orphans = 0
        for node in nodes:
            # check if it is an interior node
            point = Point((node.lon, node.lat))
            orphan = point.within(buffered)
            if orphan:
                num_orphans += 1
            output.append(topotools.NodeInfo(
                node.id, node.lat, node.lon,
                -1 if orphan else node.clust))
        return num_orphans, output

    log.info("Spawning %i worker threads", args.threads)
    final_nodes = []
    total_orphans = 0
    with futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
        for num_orphans, new_cluster in executor.map(
                associate_nodes, clustered_nodes):
            total_orphans += num_orphans
            final_nodes.extend(new_cluster)
    log.info("Orphaned %i nodes out of %i", total_orphans, len(final_nodes))

    final_nodes.sort(key=operator.attrgetter('clust'))

    log.info("Writing to %s", args.output)
    with gzip.open(args.output, 'wb') as outputfd:
        for node in final_nodes:
            outputfd.write(' '.join(str(x) for x in [
                node.id, node.lat, node.lon, node.clust, '\n'
            ]))
