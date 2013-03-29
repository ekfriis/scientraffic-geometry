"""

Helper functions for filtering point collections.

"""

import itertools
import logging
import math
import random

from descartes import PolygonPatch
import numpy as np
from scipy.spatial import Delaunay, Voronoi, voronoi_plot_2d
from shapely.geometry import MultiPolygon, Point
from shapely.geometry import MultiLineString
from shapely.ops import cascaded_union, polygonize
import matplotlib.pyplot as plt

log = logging.getLogger(__name__)


def get_concave_hull(points, cut):
    """ Find the concave hull for a set of points
    """
    max_x, max_y = np.max(points, axis=0)
    min_x, min_y = np.min(points, axis=0)
    log.info("Found %i nodes, bounded in x by (%i, %i)"
             " and y by (%i, %i)",
             len(points), min_x, max_x, min_y, max_y)
    size = max(max_x - min_x, max_y - min_y)
    tri = Delaunay(points)
    log.info("Found %i Delaunay triangles", len(tri.vertices))

    edge_points = []
    edges = set()

    def add_edge(i, j):
        """Add a line between the i-th and j-th points

        If not in the list already
        """
        if (i, j) in edges or (j, i) in edges:
            # already added
            return
        edges.add((i, j))
        edge_points.append(points[[i, j]])
    # loop over triangles:
    # ia, ib, ic = indices of corner points of the triangle
    for ia, ib, ic in tri.vertices:

        pa = points[ia]
        pb = points[ib]
        pc = points[ic]

        # Lengths of sides of triangle
        a = math.sqrt((pa[0]-pb[0])**2 + (pa[1]-pb[1])**2)
        b = math.sqrt((pb[0]-pc[0])**2 + (pb[1]-pc[1])**2)
        c = math.sqrt((pc[0]-pa[0])**2 + (pc[1]-pa[1])**2)

        # Semiperimeter of triangle
        s = (a + b + c)/2.0

        argument = s*(s-a)*(s-b)*(s-c)
        if argument < 0:
            continue

        # Area of triangle by Heron's formula
        area = math.sqrt(argument)

        if area <= 0:
            continue

        circum_r = a*b*c/(4.0*area)

        # Here's the radius filter.
        if circum_r / size < 1.0 / cut:
            add_edge(ia, ib)
            add_edge(ib, ic)
            add_edge(ic, ia)

    log.info("After filter, %i edges remain", len(edge_points))
    m = MultiLineString(edge_points)
    log.info("Polygonizing")
    triangles = list(polygonize(m))
    log.info("Unionizing")
    polygon = cascaded_union(triangles)

    best_polygon = polygon
    best_area = polygon.area

    if isinstance(polygon, MultiPolygon):
        best_area = 0
        log.info("Multi polygons detected")
        for ip, subpoly in enumerate(polygon):
            #log.info("Poly %i - area: %f", ip, subpoly.area)
            if subpoly.area > best_area:
                best_polygon = subpoly
                best_area = subpoly.area
    log.info("Found main polygon with area: %f", best_area)
    return best_polygon


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

    points = np.array([(x.lon, x.lat) for x in nodes_list], dtype=int)

    # get the concave hull around these points
    hull = get_concave_hull(points, alpha_cut)
    # buffer hull by about 5% for determining membership
    hull_distance_scale = math.sqrt(hull.area)
    buffered_hull = hull.buffer(hull_distance_scale * 0.05)
    hull_boundary = hull.boundary

    # Remove any outlier points around these nodes.
    # Mark the good nodes.
    nodes_in_hull = []
    nodes_outside_hull = []
    for point, node in itertools.izip(points, nodes_list):
        if Point(point).within(buffered_hull):
            nodes_in_hull.append(node)
        else:
            nodes_outside_hull.append(node)

    # We only care about interior points now.
    del nodes_list
    points = np.array([(x.lon, x.lat) for x in nodes_in_hull], dtype=int)

    log.info("After hull cleaning, %i nodes remain",
             len(points))

    voronoi = Voronoi(points)

    edge_regions = set([])

    # find all regions which have a vertex outside the hull
    for region_idx, region in enumerate(voronoi.regions):
        exterior_region = False
        # keep a random collection of interior points
        if random.random() < keep:
            exterior_region = True
        for vtx_idx in region:
            # indicates an exterior region, we always keep these
            if vtx_idx == -1:
                exterior_region = True
                break
            else:
                point = Point(voronoi.vertices[vtx_idx])
                if not point.within(hull) or (
                        point.distance(hull_boundary)
                        < hull_distance_scale * 0.05):
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
