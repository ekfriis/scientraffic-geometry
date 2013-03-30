#!/usr/bin/env python
'''

Find communities in an graph
----------------------------

Uses the fast-greedy algorithm.

The output format is a picke of a list of
tuples, with the form:

[
    (osrm_nodeid, lat, lon, clusterId),
    (osrm_nodeid, lat, lon, clusterId),
    ...
]

Author: Evan K. Friis

'''

import argparse
import cPickle as pickle
import gzip
import logging

import igraph

log = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('input', metavar='input.igraph.pkl.gz',
                        help='Gzipped igraph cornichon.')
    parser.add_argument('output', metavar='communities.gz',
                        help='Output communities')
    parser.add_argument('--clusters', default=1000,
                        help='Number of clusters to form')

    args = parser.parse_args()

    logging.basicConfig()
    log.setLevel(logging.INFO)

    log.info("Loading graph from %s", args.input)
    graph = igraph.read(args.input, format='picklez')
    log.info("=> %i nodes, %i edges", len(graph.vs), len(graph.es))

    log.info("Finding communities via fastgreedy")
    communities = graph.community_fastgreedy(weights='weight')

    log.info("Partitioning dendrogram into %i clusters", args.clusters)
    clusters = communities.as_clustering(args.clusters)

    log.info("Mini-fying data")
    log.info("Writing to %s", args.output)
    with gzip.open(args.output, 'wb') as outputfd:
        for clust_idx, cluster in enumerate(clusters):
            for vertex_idx in cluster:
                vertex = graph.vs[vertex_idx]
                outputfd.write(' '.join(str(x) for x in [
                    vertex['name'], vertex['lat'],
                    vertex['lon'], clust_idx, '\n'
                ]))
