#!/usr/bin/env python
'''

Orphan objects in spiky communities
whose concave hull area is much less than convex one.

'''


import argparse
import bisect
from collections import deque
import logging

import geojson
import numpy as np
from shapely.geometry import asShape
from scipy.stats.mstats import mquantiles
from shapely.prepared import prep

log = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'input', metavar='communities.hulls.json',
        help='GeoJSON tesselation')
    parser.add_argument(
        'output', metavar='merged.hulls.json',
        help='Merged output tesselation')

    parser.add_argument('--min-wrt-quantile50', type=float, metavar='F',
                        default=0.5, dest='fraction',
                        help='Merge the F smallest area concave objects.'
                        ' Default %(default)f')
    args = parser.parse_args()

    logging.basicConfig()
    log.setLevel(logging.INFO)
    log.info("Writing output to %s", args.output)

    with open(args.input, 'r') as inputfd:
        input_features = geojson.load(inputfd)

    features = []
    clusters = {}
    for feature in input_features['features']:
        if feature['geometry'] is None:
            log.error("Geometry is null! Skipping: %s", repr(feature))
            continue
        elif feature['geometry']['type'] == 'GeometryCollection':
            if feature['geometry']['geometries']:
                raise ValueError("Don't know what to do!")
            else:
                continue
        shape = asShape(feature['geometry'])
        area = shape.area
        cluster_id = feature['properties']['clust']
        clusters[cluster_id] = shape
        features.append((area, cluster_id))

    # Sort by ascending area, get fast pop access on left
    features = deque(sorted(features))

    areas = np.array([x[0] for x in features])

    q50 = mquantiles(areas, prob=[0.5])[0]

    log.info("Area of 50%% quantile: %f", q50)

    num_shapes_to_merge = bisect.bisect_left(areas, q50 * args.fraction)

    log.info("Found %i/%i communities to merge", num_shapes_to_merge,
             len(areas))

    while num_shapes_to_merge:
        num_shapes_to_merge -= 1
        _, cluster = features.popleft()
        shape = clusters[cluster]
        # Prep for faster compuations
        intersecting = []
        for i, (_, other_clust_id) in enumerate(features):
            if other_clust_id == cluster:
                continue
            other_shape = clusters[other_clust_id]
            intersection = shape.intersection(other_shape)
            if intersection:
                intersecting.append((intersection.length,
                                     other_clust_id, other_shape))
        if not intersecting:
            log.error("Couldn't find any neighbors for %i", cluster)
        else:
            # Merge this into the neighbor shape with the largest
            # shared border.
            maxlength, other_clust_id, other_shape = max(intersecting)
            clusters[other_clust_id] = other_shape.union(shape)
            log.info("Merged %i -> %i", cluster, other_clust_id)

    output_features = []
    for _, clustidx in features:
        feature = geojson.Feature(
            id=clustidx,
            geometry=clusters[clustidx],
            properties={
                'clust': clustidx
            }
        )
        output_features.append(feature)

    with open(args.output, 'w') as outputfd:
        log.info("Writing output to %s", args.output)
        geojson.dump(geojson.FeatureCollection(output_features),
                     outputfd, indent=2)
