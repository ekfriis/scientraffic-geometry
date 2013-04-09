#!/usr/bin/env python
'''

Trim long pokey tails

'''


import argparse
import logging
import math

import geojson
from shapely.geometry import asShape
from shapely.geometry import Point, Polygon, LineString
from scipy.spatial import KDTree

log = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'input', metavar='communities.cleaned.hulls.json',
        help='GeoJSON input concave hulls')
    parser.add_argument(
        'output', metavar='communities.notails.hulls.json',
        help='Cleaned output concave hulls')

    parser.add_argument('--min-tail-pinch', type=float, metavar='x',
                        default=0.05, dest='tail_pinch',
                        help='Minimum size of the pinch point'
                        ' for tail ID.  Default %(default)f')

    parser.add_argument('--max-tail-length', type=float, metavar='x',
                        default=10, dest='tail_length',
                        help='Maximum length/width for '
                        'tails Default %(default)f')

    args = parser.parse_args()

    logging.basicConfig()
    log.setLevel(logging.INFO)

    with open(args.input, 'r') as inputfd:
        features = geojson.load(inputfd)

    output_features = []
    for feature in features['features']:
        shape = asShape(feature['geometry'])

        # Trim tails on the concave hulls.  Tails are long, thin,
        # features which are created when the community goes
        # down a road away from the main group.
        has_tail = True  # guilty until proven innocent
        while has_tail:
            hull_outline = LineString(shape.exterior)
            characteristic_size = math.sqrt(shape.area)
            outline_pts = hull_outline.coords[:]
            # find the projections along the line lenght for each point
            projections = [hull_outline.project(Point(x)) for x in outline_pts]
            # so we can find neighbors close to each other
            outline_kdtree = KDTree(outline_pts)
            biggest_tail = None
            for idx, point in enumerate(outline_pts):
                proj = projections[idx]
                # find nearest neighbors, within 5% of total size
                neighbors = outline_kdtree.query_ball_point(
                    point, r=characteristic_size * args.tail_pinch)
                for neighbor in neighbors:
                    neighbor_point = outline_pts[neighbor]
                    if neighbor_point == point:
                        continue
                    neighbor_proj = projections[neighbor]
                    # Find distance along edge in both directions.
                    # Must wrap around at proj = 0.
                    # The smaller of the two is the relevant one.
                    distance_along_edge = abs(neighbor_proj - proj)
                    distance_along_edge = min(
                        distance_along_edge,
                        hull_outline.length - distance_along_edge
                    )
                    distance_as_crow_flies = math.hypot(
                        point[0] - neighbor_point[0],
                        point[1] - neighbor_point[1])
                    tailiness = distance_along_edge / distance_as_crow_flies
                    if tailiness > args.tail_length:
                        #if not biggest_tail or tailiness > biggest_tail[0]:
                        metric = tailiness * distance_along_edge
                        if not biggest_tail or metric > biggest_tail[0]:
                            log.info("Found tail with length^2/width %f, "
                                     "from idx %i -> %i",
                                     metric, idx, neighbor)
                            biggest_tail = (metric, (idx, neighbor))
            if biggest_tail:
                log.info("Clipping from %i -> %i, out of %i edges",
                         biggest_tail[1][0], biggest_tail[1][1],
                         len(outline_pts))
                tail_idx_1 = biggest_tail[1][0]
                tail_idx_2 = biggest_tail[1][1]
                min_idx = min(tail_idx_1, tail_idx_2)
                max_idx = max(tail_idx_1, tail_idx_2)

                # Now create two hypotheses for what to delete.
                hypo_1 = Polygon(outline_pts[min_idx:max_idx + 1])
                hypo_2 = Polygon(
                    outline_pts[:min_idx + 1] + outline_pts[max_idx:])
                split_hull = [hypo_1, hypo_2]

                assert(len(split_hull) == 2)
                biggest = max(split_hull, key=lambda x: x.area)
                log.info("Found new hull with %0.2f of the original area "
                         "and %0.2f of the original length",
                         biggest.area / shape.area,
                         biggest.exterior.length / hull_outline.length)
                shape = biggest
            else:
                has_tail = False
        feature['geometry'] = shape
        output_features.append(feature)

    with open(args.output, 'w') as outputfd:
        log.info("Writing output to %s", args.output)
        geojson.dump(geojson.FeatureCollection(output_features),
                     outputfd, indent=2)
