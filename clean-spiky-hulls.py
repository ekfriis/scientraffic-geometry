#!/usr/bin/env python
'''

Orphan objects in spiky communities
whose concave hull area is much less than convex one.

'''


import argparse
import logging

import geojson
from shapely.geometry import asShape

log = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'input', metavar='communities.hulls.json',
        help='GeoJSON input concave hulls')
    parser.add_argument(
        'output', metavar='communities.cleaned.hulls.json',
        help='Cleaned output concave hulls')

    parser.add_argument('--convexity', type=float, metavar='x', default=0.5,
                        help='Minimum on the ratio of '
                        'the concave/convex area.  Default %(default)f')
    args = parser.parse_args()

    log.info("Writing output to %s", args.output)

    with open(args.input, 'r') as inputfd:
        features = geojson.load(inputfd)

    output_features = []
    for feature in features['features']:
        shape = asShape(feature['geometry'])
        concave_area = shape.area
        convex_area = shape.convex_hull.area
        if concave_area < convex_area * args.convexity:
            log.info("Cluster %i is to concave (%g/%g = %g < %0.2f)",
                     feature['properties']['clust'],
                     concave_area, convex_area,
                     concave_area / convex_area, args.convexity)
        else:
            output_features.append(feature)

    with open(args.output, 'w') as outputfd:
        log.info("Writing output to %s", args.output)
        geojson.dump(geojson.FeatureCollection(output_features),
                     outputfd, indent=2)
