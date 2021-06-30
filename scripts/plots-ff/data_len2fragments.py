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
import collections
import csv
import io
import os
import matplotlib.pyplot as plt
import matplotlib.ticker as plticker
import numpy as np
import pandas
import re

from matplotlib.lines import Line2D
from matplotlib.patches import Circle


def _parse_log(sink, logfile, csvfile):
    writer = csv.writer(csvfile, delimiter=";", quotechar="\"")
    data_len, mode, fragments, dgs = None, None, None, None
    nodes = {}
    times = collections.defaultdict(int)
    for line in logfile:
        line = line.decode()
        if data_len and mode and fragments is not None and dgs is not None:
            match = re.search(r"reboot", line)
            if not match:
                continue
            if fragments == 0 and dgs == 0:
                frags_per_dg = 1.0
            else:
                frags_per_dg = fragments / dgs
            latency = np.array(list(times.values()))
            latency = latency[latency > -(24 * 60 * 60)] * 1000
            writer.writerow((data_len, mode, frags_per_dg,
                             np.mean(latency), np.std(latency)))
            data_len, mode, fragments, dgs = None, None, None, None
            times = collections.defaultdict(int)
        match = re.search(r"m3-(\d+);.*ifconfig \d+ add ([0-9a-fA-F:]+)", line)
        if match and match.group(2) not in nodes:
            nodes[match.group(2)] = int(match.group(1))
            continue
        match = re.search(r"(\d+.\d+);m3-(\d+);.*out;([0-9a-f]{4})", line)
        if match:
            node = int(match.group(2))
            id = int(match.group(3), base=16)
            times[(node, id)] -= float(match.group(1))
        match = re.search(r"(\d+.\d+);m3-\d+;.*in;([0-9a-f]{4});"
                          r"([0-9a-fA-F:]+);", line)
        if match:
            node = nodes[match.group(3)]
            id = int(match.group(2), base=16)
            times[(node, id)] += float(match.group(1))
        if mode is None:
            match = re.search(r"m3-{};.*====(\w+)====".format(sink), line)
            if match:
                mode = match.group(1)
                continue
        if data_len is None:
            match = re.search(r"start sending:\s+data_len:\s+(\d+)"
                              .format(sink), line)
            if match:
                data_len = match.group(1)
                continue
        if fragments is None:
            match = re.search(r"m3-{};.*\bfrags complete:\s+(\d+)"
                              .format(sink), line)
            if match:
                fragments = int(match.group(1))
                continue
        if dgs is None:
            match = re.search(r"m3-{};.*\bdgs complete:\s+(\d+)".format(sink),
                              line)
            if match:
                dgs = int(match.group(1))
                continue


def _existing_file(filename):
    if not os.path.exists(filename):
        raise ValueError("{} does not exist".format(filename))
    return filename

COLS = ["hwr", "ff", "e2e", "sfr"]
TRANSLATE_MODE = {
    "hwr": "HWR",
    "ff": "FF",
    "e2e": "E2E",
    "sfr": "SFR",
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("sink", type=int)
    parser.add_argument("logfile", type=argparse.FileType("rb"))
    args = parser.parse_args()
    csvfile = io.StringIO()
    csvfile.write("data_len;mode;fragments;lat_mean;lat_std\n")
    _parse_log(args.sink, args.logfile, csvfile)
    csvfile.seek(0)
    df = pandas.read_csv(csvfile, sep=";")
    cols = [col for col in COLS if col in list(df["mode"])]
    frag_num = df.pivot(index="data_len", columns="mode",
                        values="fragments")[cols]
    latency = df.pivot(index="data_len", columns="mode",
                       values="lat_mean")[cols]
    latency_errs = df.pivot(index="data_len", columns="mode",
                            values="lat_std")[cols]
    fig0, ax0 = plt.subplots()
    frag_num_plt = frag_num.plot(drawstyle="steps-post", ax=ax0, style="-")
    ax0.legend(frag_num_plt.get_legend_handles_labels()[0],
               [TRANSLATE_MODE[mode] for mode in frag_num.columns],
               loc="upper left")
    plt.xlabel("Data length [bytes]")
    plt.ylabel("Fragments [#]")
    ax1 = ax0.twinx()
    print(latency.iloc[list(range(0, 15))])
    latency.plot(ax=ax1, yerr=latency_errs, capsize=2, secondary_y=True,
                 legend=False, elinewidth=1, linewidth=0, marker=".")
    ax1.legend(loc="lower right", handles=[
        Line2D(label="Fragments", color="k", linestyle="-", xdata=[0, 1],
               ydata=[0, 0]),
        Line2D(label="Latency", color="k", linestyle="dotted", xdata=[0, 1],
               ydata=[0, 0], marker='.', linewidth=0),
    ])
    plt.ylabel("End-to-end datagram latency [ms]")
    loc = plticker.MultipleLocator(base=48.0)
    ax0.xaxis.set_major_locator(loc)
    loc = plticker.MultipleLocator(base=1.0)
    ax0.yaxis.set_major_locator(loc)
    ax0.set_xlim(xmin=0)
    ax0.set_ylim(ymin=0)
    ax1.set_ylim(ymin=0)
    plt.show()
