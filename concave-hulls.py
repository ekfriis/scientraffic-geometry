#!/usr/bin/env python

'''

Find the concave hulls of the communities.  Write them out
as GeoJSON files.

'''

import argparse
from concurrent import futures
import itertools
import logging
import operator
import topotools

import geojson
import numpy as np
from scipy.spatial.qhull import QhullError

log = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('input', metavar='communities.gz',
                        help='Gzipped communities')
    parser.add_argument(
        'output', metavar='communities.hulls.json',
        help='Output hulls')

    parser.add_argument('--bbox', nargs=4, type=float, metavar='x',
                        help='Only consider nodes within bbox')

    parser.add_argument('--alphacut', type=float, metavar='x', default=10,
                        help='Concave hull alpha cut. Default %(default)f')

    parser.add_argument('--threads', type=int, metavar='N', default=2,
                        help='Number of threads. Default %(default)f')

    args = parser.parse_args()

    logging.basicConfig()
    log.setLevel(logging.INFO)
    #topotools.hulls.log.setLevel(logging.INFO)

    # Get generator of clustered nodes
    # We keep these in OSRM units for now.
    clustered_node_iters = itertools.groupby(
        topotools.read_clusters(args.input, args.bbox, scale=False),
        operator.attrgetter('clust')
    )

    clustered_nodes = (
        (clust, list(nodes)) for clust, nodes in clustered_node_iters)

    def compute_hull(fargs):
        '''Compute the convex hull for a set of nodes

        Returns a geojson object.
        '''
        clustidx, nodes = fargs
        points = np.array([(x.lon, x.lat) for x in nodes], dtype=int)
        try:
            hull = topotools.get_concave_hull(points, args.alphacut)
            feature = geojson.Feature(
                id=clustidx,
                geometry=hull,
                properties={
                    'clust': clustidx
                }
            )
        except QhullError:
            log.exception("Error in Qhull, returning null for cluster"
                          " %i with %i nodes" % (clustidx, len(points)))
            feature = None
        return feature

    log.info("Spawning %i compute threads", args.threads)
    with futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
        features = list(executor.map(compute_hull, clustered_nodes))

    feature_collection = geojson.FeatureCollection(
        [feature for feature in features
         if feature is not None and feature.geometry])

    with open(args.output, 'w') as outputfd:
        geojson.dump(feature_collection, outputfd, indent=2)
