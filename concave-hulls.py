#!/usr/bin/env

'''

Find the concave hulls of the communities.  Write them out
as GeoJSON files.

'''

import argparse
import itertools
import logging
import operator
import topotools

import geojson
import numpy as np

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

    args = parser.parse_args()

    logging.basicConfig()
    log.setLevel(logging.INFO)

    # Get generator of clustered nodes
    # We keep these in OSRM units for now.
    clustered_nodes = itertools.groupby(
        topotools.read_clusters(args.input, args.bbox, scale=False),
        operator.attrgetter('clust')
    )

    features = []
    for clustidx, nodes in clustered_nodes:
        points = np.array([(x.lon, x.lat) for x in nodes], dtype=int)
        hull = topotools.get_convex_hull(points, args.alphacut)
        feature = geojson.Feature(
            id=clustidx,
            geometry=hull,
            properties={
                'clust': clustidx
            }
        )
        features.apend(feature)
    feature_collection = geojson.FeatureCollection(features)

    with open(args.output, 'w') as outputfd:
        geojson.dump(feature_collection, outputfd, indent=2)
