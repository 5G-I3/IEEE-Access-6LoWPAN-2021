#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Martine Lenders <m.lenders@fu-berlin.de>
#
# Distributed under terms of the MIT license.

import argparse
import csv
import json
import matplotlib.pyplot as plt
import networkx as nx
import os
import re

from matplotlib.colors import hsv_to_rgb


SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.environ.get("DATA_PATH",
                           os.path.join(SCRIPT_PATH, "..", "..", "results"))
NETWORK_PATTERN = "n(?P<network_id>m3-\d+x[a-f\d]+)"
SINK_COLOR = "#330099"
SOURCE_COLOR = "#b5a3da"


def in_addr(logfile):
    res = {}
    with open(logfile, "rb") as log:
        c = re.compile(";in;")
        for line in log:
            line = line.decode(errors="ignore")
            if c.search(line) is not None:
                addr = line.split(";")[4]
                if addr in res:
                    res[addr] += 1
                else:
                    res[addr] = 1
    return res


def nodes_dict(link_local_csv):
    nodes = {}
    with open(link_local_csv) as csvfile:
        reader = csv.DictReader(csvfile)
        for line in reader:
            nodes[line["lla"]] = line["node"]
    return nodes


def mark_in_nodes(svgfile_prefix, edgelist, sink, prefix, addrs, node_dict,
                  monochrome=False):
    g = nx.read_edgelist(edgelist, data=[("weight", float)])
    assert(sink in g)
    max_value = max(addrs.values())
    assert(max_value > 0)
    nodes = {node_dict[addr.replace(prefix, "fe80::")]: value \
             for addr, value in addrs.items()}
    print(svgfile_prefix, len(nodes))
    if monochrome:
        color_map = []
        outline_map = []
        with_labels = False
    else:
        color_map = []
        outline_map = "face"
        with_labels = True
    for n in g.nodes:
        if n == sink:
            if monochrome:
                color_map.append("black")
                outline_map.append("black")
            else:
                color_map.append(SINK_COLOR)
        elif n in g.neighbors(sink):
            if monochrome:
                color_map.append("lightgray")
                outline_map.append("black")
            else:
                color_map.append(SOURCE_COLOR)
        elif n in nodes:
            if monochrome:
                color_map.append("gray")
                outline_map.append("black")
            else:
                print(n, nodes[n] / max_value * 100)
                color_map.append(
                    hsv_to_rgb((1 - ((1 / 3) * (nodes[n] / max_value)), .75, 1))
                )
        else:
            if monochrome:
                color_map.append("gray")
                outline_map.append("gray")
            else:
                color_map.append("black")
    paths = nx.shortest_path(g, sink)
    longest_path = []
    for path in paths:
        if len(paths[path]) > len(longest_path):
            longest_path = paths[path]
    pos = nx.kamada_kawai_layout(g)
    nx.draw(g, pos=pos, node_color=color_map, with_labels=with_labels,
            node_size=50, font_size=2, font_color="white",
            edgecolor=outline_map)
    if not monochrome:
        plt.title("Longest path: {} ({} hops)".format(longest_path,
                                                      len(longest_path) - 1))

    plt.savefig("{}.svg".format(svgfile_prefix), bbox_inches="tight")


def main(prefix, log, monochrome=False):
    if prefix[-1] != ':':
        prefix += ":"

    m = re.search(NETWORK_PATTERN, log)
    assert(m is not None)
    network_id = m.group("network_id")
    edgelist = os.path.join(DATA_PATH,
                            "{}.edgelist.gz".format(network_id))
    link_local_csv = os.path.join(DATA_PATH,
                                  "{}.link_local.csv".format(network_id))
    sink = re.sub("(m3-\d+)x[a-f\d]+", r"\1", network_id)
    addrs = in_addr(log)
    nodes = nodes_dict(link_local_csv)
    svgfile_prefix = log.replace(".log", "")
    mark_in_nodes(svgfile_prefix, edgelist, sink, prefix, addrs, nodes,
                  monochrome)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("-m", "--monochrome", action="store_true",
                   help="Stores plot in monochrome rather than colored")
    p.add_argument("log", help="Log to analyze")
    p.add_argument("prefix", default="2001:db8:0:1:", nargs="?",
                   help="The IPv6 prefix of the network")
    args = p.parse_args()
    main(**vars(args))
