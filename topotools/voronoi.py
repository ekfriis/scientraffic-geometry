import itertools
import logging
import math
import random

from descartes import PolygonPatch
import numpy as np
from scipy.spatial import Voronoi, voronoi_plot_2d
from shapely.prepared import prep
from shapely.geometry import Point
import matplotlib.pyplot as plt

from .hulls import get_concave_hull, get_convex_hull

log = logging.getLogger(__name__)


def voronoi_prune_region(nodes, alpha_cut, keep=0.05, draw=None):
    """ Takes as input a list of points

    First computes the concave hull and removes
    all points outside it.

    Then remove all those points completely contained.
    In other words, only return those which are on
    the boundary of the hull.
    """

    nodes_list = list(nodes)

    log.info("Pruning %i nodes", len(nodes_list))

    points = np.array([(x.lon, x.lat) for x in nodes_list], dtype=float)

    # get the concave hull around these points
    hull = get_concave_hull(points, alpha_cut)
    if not hull:
        log.warning("Concave hull is null, using convex!")
        hull = get_convex_hull(points)
    # buffer hull by about 5% for determining membership
    hull_distance_scale = math.sqrt(hull.area)
    buffered_hull = prep(hull.buffer(hull_distance_scale * 0.05))
    hull_boundary = hull.boundary

    # Remove any outlier points around these nodes.
    # Mark the good nodes.
    nodes_in_hull = []
    nodes_outside_hull = []
    for point, node in itertools.izip(points, nodes_list):
        if buffered_hull.contains(Point(point)):
            nodes_in_hull.append(node)
        else:
            nodes_outside_hull.append(node)

    # We only care about interior points now.
    del nodes_list
    points = np.array([(x.lon, x.lat) for x in nodes_in_hull], dtype=float)

    log.info("After hull cleaning, %i nodes remain",
             len(points))

    voronoi = Voronoi(points)

    edge_regions = set([])

    # find all regions which have a vertex outside the hull
    prepped_hull = prep(hull)
    for region_idx, region in enumerate(voronoi.regions):
        exterior_region = False
        # keep a random collection of interior points
        if random.random() < keep:
            exterior_region = True
        else:
            for vtx_idx in region:
                # indicates an exterior region, we always keep these
                if vtx_idx == -1:
                    exterior_region = True
                    break
                else:
                    point = Point(voronoi.vertices[vtx_idx])
                    if not prepped_hull.contains(point):
                        exterior_region = True
                        break
                    # Keep 20% of points very close to the border
                    if random.random() < 0.2 and (
                            point.distance(hull_boundary)
                            < hull_distance_scale * 0.03):
                        exterior_region = True
                        break
        if exterior_region:
            edge_regions.add(region_idx)

    output = []

    point_region_map = voronoi.point_region
    for node_idx, node in enumerate(nodes_in_hull):
        region_idx = point_region_map[node_idx]
        if region_idx in edge_regions:
            output.append(node)

    log.info("There are %i nodes after pruning", len(output))

    if draw is not None:
        log.info("Drawing prune plot")
        fig = plt.figure(figsize=(20, 20))
        voronoi_plot_2d(voronoi)
        plt.plot(
            [x.lon for x in output],
            [x.lat for x in output],
            'x', color='red', hold=1)
        plt.plot(
            [x.lon for x in nodes_outside_hull],
            [x.lat for x in nodes_outside_hull],
            'D', color='orange', hold=1)
        plt.gca().add_patch(PolygonPatch(hull, alpha=0.2))
        plt.savefig(draw)
        del fig

    return output
