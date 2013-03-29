#!/usr/bin/env python

'''

Find the voronoi diagram of a set of points.

Author: Evan K. Friis

'''

import argparse
from collections import namedtuple
import gzip
import itertools
import logging
import operator
import random

import numpy as np
from scipy.spatial import Voronoi

from descartes import PolygonPatch
from shapely.geometry import MultiPolygon, MultiLineString
from shapely.ops import cascaded_union, polygonize
from shapely.validation import explain_validity
import matplotlib.pyplot as plt

import topotools

log = logging.getLogger(__name__)

NodeInfo = namedtuple('NodeInfo', ['id', 'lat', 'lon', 'clust'])


def read_clusters(gzipped_file, bbox):
    """Yield node and cluster info from a gzip file"""
    def in_bbox(node):
        if not bbox:
            return True
        # make sure they are ordered correctly
        upper_lat = max(bbox[1], bbox[3])
        lower_lat = min(bbox[1], bbox[3])
        upper_lon = max(bbox[0], bbox[2])
        lower_lon = min(bbox[0], bbox[2])
        if lower_lon < node.lon < upper_lon:
            if lower_lat < node.lat < upper_lat:
                return True
        return False

    with gzip.open(gzipped_file, 'rb') as fd:
        for line in fd:
            fields = [int(x) for x in line.strip().split()]
            node = NodeInfo(*fields)
            if in_bbox(node):
                yield node


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'input', metavar='communities.gz',
        help='Gzipped communities, generated by communities.py')
    parser.add_argument(
        'output', metavar='community_shapes.gz',
        help='Gzipped WKT output polygons')

    parser.add_argument(
        '--draw-prune', dest='drawprune', type=int, nargs='+',
        help='Draw voronoi pruning debug diagram')

    parser.add_argument(
        '--draw', help='Draw voronoi diagram')

    parser.add_argument('--bbox', nargs=4, type=float, metavar='x',
                        help='Only consider nodes within bbox')

    parser.add_argument('--seed', default=1, type=int, help='random seed')

    args = parser.parse_args()

    logging.basicConfig()
    log.setLevel(logging.INFO)
    topotools.log.setLevel(logging.INFO)

    random.seed(args.seed)

    clustered_nodes = itertools.groupby(
        read_clusters(args.input, args.bbox),
        operator.attrgetter('clust')
    )

    pruned_nodes = []

    for clustidx, nodes in clustered_nodes:
        log.info("Pruning interior of cluster %i", clustidx)
        draw = None
        if args.drawprune and clustidx in args.drawprune:
            draw = 'prune_%i.png' % clustidx
        pruned = topotools.voronoi_prune_region(nodes, 25, draw=draw)
        pruned_nodes.extend(pruned)

    pruned_nodes.sort(key=operator.attrgetter('clust'))

    log.info("Generating full Voronoi from %i pruned nodes",
             len(pruned_nodes))

    max_lat = max([x.lat for x in pruned_nodes])
    min_lat = min([x.lat for x in pruned_nodes])
    max_lon = max([x.lon for x in pruned_nodes])
    min_lon = min([x.lon for x in pruned_nodes])

    voronoi = Voronoi(np.array(
        [(x.lon, x.lat) for x in pruned_nodes], dtype=int))

    log.info("Joining polygons")

    output_polygons = []

    # Loop over collections of node indices
    for clusteridx, node_iter in itertools.groupby(
            enumerate(pruned_nodes), lambda x: x[1].clust):

        # keep track of all paths in this cluster's
        # voronoi regions.
        cluster_polygons = []

        for node_idx, node in node_iter:
            #print clusteridx, node_idx, node.clust
            # Get the voronoi region of this point
            voronoi_region = voronoi.point_region[node_idx]
            vertices_idxs = voronoi.regions[voronoi_region]
            # ignore infinite cells
            if -1 in vertices_idxs:
                continue
            # add lines between all interior points
            points = [(tuple(voronoi.vertices[a]), tuple(voronoi.vertices[b]))
                      for a, b in itertools.combinations(vertices_idxs, 2)]
            ring = MultiLineString(points)
            polygons = list(polygonize([ring]))
            if not polygons:
                log.warning("No polygons detected in line with coords: %s",
                            repr(list(ring.coords)))
            else:
                if not polygons[0].is_valid:
                    log.warning("Invalid polygon! %s",
                                explain_validity(polygons[0]))
                    polygons[0] = polygons[0].buffer(0)
                    log.warning("After cleaning validity = %i",
                                polygons[0].is_valid)
                cluster_polygons.append(polygons[0])

        log.info("Merging %i cluster polygons", len(cluster_polygons))
        polygon = cascaded_union(cluster_polygons)
        #import pdb
        #pdb.set_trace()
        log.info("Created polygon for cluster %i with area %0.2f",
                 clusteridx, polygon.area)

        best_polygon = polygon
        original_area = polygon.area
        best_area = polygon.area

        if isinstance(polygon, MultiPolygon):
            best_area = 0
            log.info("Multi polygons detected")
            for ip, subpoly in enumerate(polygon):
                subpoly.cluster = clusteridx
                output_polygons.append(subpoly)
                #log.info("Poly %i - area: %f", ip, subpoly.area)
                if subpoly.area > best_area:
                    best_polygon = subpoly
                    best_area = subpoly.area
        else:
            best_polygon.cluster = clusteridx
            output_polygons.append(best_polygon)

    if args.draw:
        colors = ['red', 'green', 'blue', 'orange', 'PeachPuff',
                  'purple', 'cyan', 'Coral', 'FireBrick']
        figure = plt.figure()
        plt.gca().set_ylim((min_lat, max_lat))
        plt.gca().set_xlim((min_lon, max_lon))
        #for clusteridx, node_iter in itertools.groupby(
                #pruned_nodes, operator.attrgetter('clust')):
            #color_for_clust = colors[clusteridx % len(colors)]
            #xy = np.array([(x.lon, x.lat) for x in node_iter], dtype=int)
            #plt.plot(xy[:, 0], xy[:, 1], 'x', color=color_for_clust, hold=1)
        for polygon in output_polygons:
            color_for_clust = colors[polygon.cluster % len(colors)]
            plt.gca().add_patch(
                PolygonPatch(polygon, alpha=0.2, ec='black',
                             fc=color_for_clust))
        figure.savefig(args.draw)
