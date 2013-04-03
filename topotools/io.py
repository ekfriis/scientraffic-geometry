"""

Info for reading & writing geo data

"""

from collections import namedtuple
import gzip
import logging

from osgeo import ogr
from shapely.wkb import loads

log = logging.getLogger(__name__)

NodeInfo = namedtuple('NodeInfo', ['id', 'lat', 'lon', 'clust'])


def read_clusters(gzipped_file, bbox, scale=True):
    """Yield node and cluster info from a gzip file

    Uses the format defined in find-communities.py

    """
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
            # Scale lat/lon to normal degrees
            if scale:
                fields[1] /= 100000.
                fields[2] /= 100000.
            node = NodeInfo(*fields)
            if in_bbox(node):
                yield node


def shp_to_multipolygon(shp_file, overlapping=None):
    """Yields features from a .shp in Shapely format

    If overlapping is not None, only polygons which overlap it
    are yielded.
    """
    log.info("Converting %s to shapely format", shp_file)
    source = ogr.Open(shp_file)
    layer = source.GetLayer()
    for fidx in range(layer.GetFeatureCount()):
        feature = layer.GetFeature(fidx)
        polygon = loads(feature.GetGeometryRef().ExportToWkb())
        if not overlapping or polygon.intersects(overlapping):
            yield polygon
