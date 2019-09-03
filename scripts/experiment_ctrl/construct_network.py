#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (C) 2019 Freie Universität Berlin
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

import argparse
import logging
import matplotlib as mpl
import networkx as nx
import os
from queue import Queue
import random
from iotlab_controller.common import get_default_api, get_uri
from iotlab_controller.nodes import SinkNetworkedNodes

mpl.use('svg')
import matplotlib.pyplot as plt

__author__ = "Martine S. Lenders"
__copyright__ = "Copyright 2019 Freie Universität Berlin"
__license__ = "LGPL v2.1"
__email__ = "m.lenders@fu-berlin.de"

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.environ.get("DATA_PATH",
                           os.path.join(SCRIPT_PATH, "..", "..", "results"))

DEFAULT_IOTLAB_SITE = "lille"

ARCHI_SHORT = "m3"
ARCHI_FULL = "m3:at86rf231"

# Network construction parameters
MIN_DISTANCE = 2.2
MAX_DISTANCE = 6.5
MIN_NEIGHBORS = 1
MAX_NEIGHBORS = 3
MAX_NODES = 50

SINK_COLOR = "#330099"
SINK_NEIGHBORS_COLOR = "#d3d3d3"
SOURCE_COLOR = "#b5a3da"


class NetworkConstructionError(Exception):
    pass


def draw_network(network, true_pos=True, *args, **kwargs):
    if true_pos:
        pos = {k: (network.network.nodes[k]["info"].x,
                   network.network.nodes[k]["info"].y)
               for k in network.network}
    else:
        pos = nx.kamada_kawai_layout(network.network)
    color_map = []
    sink = network.network.nodes[network.sink]
    for n in network.network:
        if network.network.nodes[n] == sink:
            color_map.append(SINK_COLOR)
        elif n in network.neighbors(network.sink):
            color_map.append(SINK_NEIGHBORS_COLOR)
        else:
            color_map.append(SOURCE_COLOR)
    kwargs["node_size"] = 50
    kwargs["font_size"] = 2
    kwargs["font_color"] = "white"
    kwargs["with_labels"] = True
    kwargs["node_color"] = color_map
    kwargs["pos"] = pos
    nx.draw(network.network, *args, **kwargs)


def construct_network(sink, iotlab_site=DEFAULT_IOTLAB_SITE,
                      min_distance=MIN_DISTANCE, max_distance=MAX_DISTANCE,
                      min_neighbors=MIN_NEIGHBORS, max_neighbors=MAX_NEIGHBORS,
                      max_nodes=MAX_NODES, api=None):
    def _restrict_potential_neighbors(node_set, node, network):
        potential_neighbors = set(node_set.values())
        potential_neighbors.remove(node)
        # select nodes where
        # neigh is is within max_distance of node and
        # neigh is not already in network
        # neigh is further away than min_distance from all other nodes and
        # and there is no node in network that is within min_distance of neigh
        return [
            neigh for neigh in potential_neighbors if
            (node.distance(neigh) < max_distance) and
            (neigh not in network) and
            ((neigh.distance(w) >= min_distance)
             for w in potential_neighbors - {neigh}) and
            not any((neigh.distance(x) < min_distance) for x in network)
        ]

    sink = "{}-{}".format(ARCHI_SHORT, sink)
    if api is None:
        api = get_default_api()
    # get all nodes that are alive and not booked from iotlab_site
    node_selection = SinkNetworkedNodes.all_nodes(iotlab_site, "Alive",
                                                  ARCHI_FULL, api, sink=sink)
    if get_uri(iotlab_site, sink) not in node_selection:
        raise NetworkConstructionError("Sink {} is not 'Alive' (maybe booked "
                                       "by other experiment?)".format(sink))
    result = SinkNetworkedNodes(iotlab_site, sink)
    sink = result[sink]
    # BFS from sink
    queue = Queue()
    visited = set([sink])
    queue.put(sink)

    def _save_result():
        draw_network(result, False)
        plt.savefig(os.path.join(DATA_PATH, "{}_logic.svg".format(result)),
                    dpi=150)
        plt.clf()
        draw_network(result, True)
        plt.savefig(os.path.join(DATA_PATH, "{}_geo.svg".format(result)),
                    dpi=150)
        result.save_edgelist(
            os.path.join(DATA_PATH, "{}.edgelist.gz".format(result))
        )
        plt.clf()

    while not queue.empty() and len(result) < max_nodes:
        node = queue.get()
        candidates = _restrict_potential_neighbors(
            node_selection.nodes, node_selection[node.uri], result
        )
        if not candidates:
            continue
        if node == sink:
            # sink always has two neighbors
            num_neigh = 2
        else:
            num_neigh = random.randint(
                min(min_neighbors, len(candidates)),
                min(max_neighbors, len(candidates))
            )
        neighbor_sample = random.sample(candidates, num_neigh)
        for neigh in neighbor_sample:
            if neigh not in visited:
                result.add_edge(node, neigh)
                if len(result) == max_nodes:
                    _save_result()
                    return result
                visited.add(neigh)
                queue.put(neigh)
    _save_result()
    return result


def main():
    logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s',
                        level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("-S", "--iotlab-site", default=DEFAULT_IOTLAB_SITE,
                        help="IoT-LAB site to pick nodes from (default: {})"
                        .format(DEFAULT_IOTLAB_SITE))
    parser.add_argument("-mind", "--min-distance", default=MIN_DISTANCE,
                        help="Minimum distance between nodes (default: {})"
                        .format(MIN_DISTANCE), type=float)
    parser.add_argument("-maxd", "--max-distance", default=MAX_DISTANCE,
                        help="Maximum distance between nodes (default: {})"
                        .format(MAX_DISTANCE), type=float)
    parser.add_argument("-minn", "--min-neighbors", default=MIN_NEIGHBORS,
                        help="Minimum down-stream neighbors per node "
                        "(default: {})".format(MIN_NEIGHBORS), type=int)
    parser.add_argument("-maxn", "--max-neighbors", default=MAX_NEIGHBORS,
                        help="Maximum down-stream neighbors per node "
                        "(default: {})".format(MAX_NEIGHBORS), type=int)
    parser.add_argument("-N", "--max-nodes", default=MAX_NODES,
                        help="Maximum number of nodes in network",
                        type=int)
    parser.add_argument("sink", type=int,
                        help="Number of the M3 sink node within the network")
    args = parser.parse_args()
    construct_network(args.sink, args.iotlab_site,
                      args.min_distance, args.max_distance,
                      args.min_neighbors, args.max_neighbors,
                      args.max_nodes)


if __name__ == "__main__":
    main()
