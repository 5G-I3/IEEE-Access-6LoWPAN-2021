#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (C) 2019 Freie Universität Berlin
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

import csv
import numpy as np
import matplotlib.pyplot as plt
import os
import sys

__author__ = "Martine S. Lenders"
__copyright__ = "Copyright 2019 Freie Universität Berlin"
__license__ = "LGPL v2.1"
__email__ = "m.lenders@fu-berlin.de"

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.environ.get("DATA_PATH",
                           os.path.join(SCRIPT_PATH, "..", "..", "results"))
DISTANCES_CSV = os.path.join(DATA_PATH, "distance_test.csv")

YMAX = 110


def plot(filename=DISTANCES_CSV, *args):
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    data = {}
    with open(filename, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            dist = row["d"]
            if dist not in data:
                data[dist] = []
            data[dist].append(row["packet loss"])
    ds = sorted(data.keys())
    x = np.array(ds).astype(np.float)
    x_max = int(max(x))
    bins = np.arange(0.5, x_max + .5)
    inds = np.digitize(x, bins, right=False)
    bin_data = [[] for _ in range(len(bins))]
    y_m = np.array([np.mean(np.array(data[d]).astype(np.float))
                    for d in sorted(data.keys())])
    y_s = np.array([np.std(np.array(data[d]).astype(np.float))
                    for d in sorted(data.keys())])
    for i, ind in enumerate(inds):
        bin_data[ind - 1].extend(data[ds[i]])
    binned_data = np.array([np.array(d).astype(np.float)
                            for d in bin_data])
    ax.clear()
    for i, b in enumerate(bins):
        ax.axvline(x=b, color="orange")
    ax.errorbar(x, y_m, y_s, fmt="o", alpha=.2, color="gray")
    bplot = ax.boxplot(binned_data, labels=bins+.5, whis=0.75,
                       showfliers=False, notch=False, showmeans=True,
                       patch_artist=True,
                       medianprops={"color": "firebrick"},
                       meanprops={"marker": "D",
                                  "markerfacecolor": "purple",
                                  "markeredgecolor": "none"})
    for i, b in enumerate(bins):
        mean = np.mean(binned_data[i])
        ax.text(b+.5, mean+1.5, "μ=%.1f%%" % mean, rotation="vertical",
                horizontalalignment="center", verticalalignment="bottom",
                color="purple")
    for box in bplot["boxes"]:
        box.set_facecolor("pink")
        box.set_alpha(0.75)
    plt.xlim((0, x_max + .5))
    plt.ylim((0, YMAX))
    plt.ylabel("packet loss [%]")
    plt.xlabel("distance [m]")
    plt.title("Ping packet loss over distance")
    ax.text(-0.5, -8, "Dataset size", horizontalalignment="right")
    for i, y in enumerate(binned_data):
        ax.text(i+1, -8, "%s" % len(y), horizontalalignment="center")

    fig.set_size_inches(18.5, 10.5)
    plt.savefig(os.path.join(DATA_PATH, "ping-stats.svg"), dpi=150)
    plt.show()


if __name__ == "__main__":
    plot(*sys.argv[1:])
