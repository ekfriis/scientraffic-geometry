'''

Functions to smooth communities using k nearest neighbors

'''

from concurrent import futures
from collections import Counter
import functools
import logging

import numpy as np

from . import NodeInfo

log = logging.getLogger(__name__)


def reassign_cluster(node, kdtree=None, current_clusters=None, k=None):
    """Determine the reassigned cluster for a single node"""
    distances, indices = kdtree.query([node], k=k)
    # NB only good nodes, not orphans are used for this.
    neighbor_clusters = current_clusters[indices[0]]
    new_cluster = Counter(neighbor_clusters).most_common(1)[0][0]
    return new_cluster


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
    new_clusters = []
    report_every = int(len(nodecollection) / 100)
    for idx, node in enumerate(nodecollection):
        if idx % report_every == 0:
            log.info("Reassigned %i nodes", idx)
        new_cluster = reassign_cluster(node, kdtree, current_clusters, k)
        new_clusters.append(new_cluster)
    return new_clusters


def reassign_clusters_threaded(nodecollection, kdtree, current_clusters,
                               k, worker_threads):
    """Threaded version of reassign_clusters

    Nodes are reassigned in place.

    """
    log.info("Spawning %i threads to reassign %i nodes",
             worker_threads, len(nodecollection))
    reassigner = functools.partial(
        reassign_cluster,
        kdtree=kdtree, current_clusters=current_clusters, k=k)
    output = np.zeros(len(nodecollection), dtype=int)
    report_every = int(len(nodecollection) / 100)
    with futures.ThreadPoolExecutor(max_workers=worker_threads) as executor:
        i = 0
        log.info("Beginning execution")
        for new_cluster in executor.map(reassigner, nodecollection):
            output[i] = new_cluster
            i += 1
            if True or i % report_every == 0:
                log.info("Reassigned %i nodes", i)
    return output
