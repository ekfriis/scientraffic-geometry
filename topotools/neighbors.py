'''

Functions to smooth communities using k nearest neighbors

'''

from collections import Counter
import logging

from . import NodeInfo

log = logging.getLogger(__name__)


def reassign_clusters(nodecollection, kdtree, current_clusters, k):
    """Return a new copy of node collection with reassigned clusters

    The mode of the cluster distribution of the k nearest neighbors
    is the new cluster value.

    @param nodecollection: nodes to reassign
    @param current_clusters: array of cluster values corresponding
        to the points used to build kdtree
    @param kdtree: a k-nearest neighbor tree
    @param k: how many neighbors to use.
    """
    new_nodes = []
    reassigned = 0
    report_every = int(len(nodecollection) / 100)
    for idx, node in enumerate(nodecollection):
        if idx % report_every == 0:
            log.info("Reassigned %i nodes", idx)
        distances, indices = kdtree.query([(node.lon, node.lat)], k=k)
        # NB only good nodes, not orphans are used for this.
        neighbor_clusters = current_clusters[indices[0]]
        new_cluster = Counter(neighbor_clusters).most_common(1)[0][0]
        if new_cluster != node.clust:
            reassigned += 1
        new_nodes.append(NodeInfo(node.id, node.lat, node.lon, new_cluster))
    return new_nodes, reassigned
