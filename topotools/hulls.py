"""

Tools for finding convex and concave hulls

Author: Evan K. Friis

"""

import logging
import math

import numpy as np
from scipy.spatial import Delaunay, ConvexHull
from shapely.geometry import MultiLineString, MultiPolygon
from shapely.ops import cascaded_union, polygonize
import shapely.speedups
shapely.speedups.enable()

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
    if not edge_points:
        log.warning("No edges remain, concave hull is not defined!")
        return None
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


def get_convex_hull(points):
    """ Find the convex hull of points, return as Shapely polygon """
    log.info("Finding convex hull of %i points", len(points))
    hull = ConvexHull(points)
    log.info("Found convex hull with %i facets", len(hull.simplices))
    hull_edges = []
    for simplex in hull.simplices:
        hull_edges.append(
            zip(points[simplex, 0], points[simplex, 1]))
    polygon = list(polygonize(hull_edges))
    assert(len(polygon) == 1)
    return polygon[0]
