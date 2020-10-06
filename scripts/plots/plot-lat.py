#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2020 Martine Lenders <m.lenders@fu-berlin.de>
#
# Distributed under terms of the MIT license.

import csv
import re
import os
import math
from matplotlib.colors import hsv_to_rgb
from matplotlib.lines import Line2D
import matplotlib.figure
import matplotlib.patches
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

from plot_results import DATA_PATH, DELAY, NAME_PATTERN, MAX_HOPS, \
                         TIMES_CSV_NAME_PATTERN_FMT, \
                         STATS_CSV_NAME_PATTERN_FMT, \
                         _check_logs, _get_files, _reject_outliers


DATA_LENS = tuple(range(16, 1025, 16))
MODES = [
    "reass",
    "fwd",
    "e2e",
    "sfr-win1ifg500arq1200r4dg0",
    "sfr-win1ifg100arq1200r4dg0",
    "sfr-win1ifg500arq2400r4dg0",
    "sfr-win1ifg100arq2400r4dg0",
    "sfr-win5ifg100arq1200r4dg0",
    "sfr-win5ifg500arq1200r4dg0",
    "sfr-win5ifg100arq2400r4dg0",
    "sfr-win5ifg500arq2400r4dg0",
]
MODES_READABLE = {
    "reass": "HWR",
    "fwd": "FF",
    "e2e": "E2E",
    "sfr-win1ifg100arq1200r4dg0": "SFR (W:1,G:0.1ms,A:1.2s)",
    "sfr-win1ifg100arq2400r4dg0": "SFR (W:1,G:0.1ms,A:2.4s)",
    "sfr-win1ifg500arq1200r4dg0": "SFR (W:1,G:0.5ms,A:1.2s)",
    "sfr-win1ifg500arq2400r4dg0": "SFR (W:1,G:0.5ms,A:2.4s)",
    "sfr-win5ifg100arq1200r4dg0": "SFR (W:5,G:0.1ms,A:1.2s)",
    "sfr-win5ifg100arq2400r4dg0": "SFR (W:5,G:0.1ms,A:2.4s)",
    "sfr-win5ifg500arq1200r4dg0": "SFR (W:5,G:0.5ms,A:1.2s)",
    "sfr-win5ifg500arq2400r4dg0": "SFR (W:5,G:0.5ms,A:2.4s)",
}
MODES_BINS = {
    'reass': [0],
    "fwd": [0],
    "e2e": [0, 96] + [
            # round up to nearest multiple of 16 if not multiple of 16
            ((((i * 72) // 16) + 1) * 16) if ((i * 72) % 16) > 0
            else i * 72 for i in range(2, 15)],
    "sfr-win1ifg100arq1200r4dg0": [0],
    "sfr-win1ifg100arq2400r4dg0": [0],
    "sfr-win1ifg500arq1200r4dg0": [0],
    "sfr-win1ifg500arq2400r4dg0": [0],
    "sfr-win5ifg100arq1200r4dg0": [0],
    "sfr-win5ifg100arq2400r4dg0": [0],
    "sfr-win5ifg500arq1200r4dg0": [0],
    "sfr-win5ifg500arq2400r4dg0": [0],
}


def data_len_to_bin(mode, data_len):
    frag_num = 0
    while (frag_num < len(MODES_BINS[mode])) and \
            (data_len >= MODES_BINS[mode][frag_num]):
        frag_num += 1
    return frag_num - 1


BYTE_LATENCY = .06


def reass_exp_latency(data_len, hops, hop_latencies):
    bin = data_len_to_bin("reass", data_len)
    frag_start_len = MODES_BINS[mode][bin]
    frag_num = bin + 1
    res = (frag_num * np.sum(hop_latencies[:(hops + 1)])) + \
        (hops + 1) * np.sum([BYTE_LATENCY *
                             (MODES_BINS[mode][b] - MODES_BINS[mode][b - 1]
                              if b > 0 else MODES_BINS[mode][b])
                             for b in range(bin)]) + \
        (hops + 1) * (BYTE_LATENCY * (data_len - frag_start_len))
    return res


MODES_EXP = {
    "reass": reass_exp_latency,
}


def hop_lat(num):
    return [6 for _ in range(num)]


runs = 3
_check_logs()
plt.clf()
networks = set()
matrix = []
last = 100
hops_legend_elements = []
plt.rcParams.update({"figure.figsize": (8, 4)})
c = re.compile(NAME_PATTERN)
# get fragment numbers
for o, mode in enumerate(MODES):
    for data_len in DATA_LENS:
        filenames = _get_files(DELAY, mode, data_len, runs,
                               STATS_CSV_NAME_PATTERN_FMT)
        fragment_num = []
        for _, filename in filenames[-runs:]:
            filename = os.path.join(DATA_PATH, filename)
            m = c.search(filename)
            assert(m is not None)
            with open(filename) as csvfile:
                reader = csv.DictReader(csvfile, delimiter=";")
                for row in reader:
                    if not len(row["dg_comp"]) or row["dg_comp"] == "0":
                        continue
                    fragment_num.append(
                        int(math.ceil(
                            int(row["frag_comp"]) / int(row["dg_comp"])
                        ))
                    )
        if not len(fragment_num):
            continue
        idx = max(fragment_num) - 1
        try:
            if MODES_BINS[mode][idx] > data_len:
                for i, _ in enumerate(MODES_BINS[mode][idx:]):
                    if MODES_BINS[mode][idx + i] > data_len:
                        break
                    else:
                        MODES_BINS[mode][idx + i] = data_len
        except IndexError:
            MODES_BINS[mode].extend(
                ((idx + 1) - len(MODES_BINS[mode])) * [data_len]
            )
for o, mode in enumerate(MODES):
    plt.clf()
    fig = plt.figure()
    subplot = fig.add_subplot(111, projection="3d")
    latencies = [[[] for _ in range(MAX_HOPS - 2)] for _ in MODES_BINS[mode]]
    exp = [[[] for _ in range(MAX_HOPS - 2)] for _ in MODES_BINS[mode]]
    for data_len in DATA_LENS:
        filenames = _get_files(DELAY, mode, data_len, runs,
                               TIMES_CSV_NAME_PATTERN_FMT)
        frag_num = data_len_to_bin(mode, data_len)
        if not filenames:
            for h in range(MAX_HOPS - 2):
                latencies[frag_num][h].append(float("nan"))
            continue
        for h in range(MAX_HOPS - 2):
            exp[frag_num][h].extend([
                MODES_EXP.get(mode, lambda a, b, c: np.nan)(
                    data_len, h, [lat] * MAX_HOPS
                ) for lat in hop_lat(1000)]
            )
        for _, filename in filenames[-runs:]:
            filename = os.path.join(DATA_PATH, filename)
            m = c.search(filename)
            assert(m is not None)
            networks.add(m.group("network"))
            with open(filename) as csvfile:
                reader = csv.DictReader(csvfile, delimiter=";")
                for row in reader:
                    if not len(row["recv_time"]):
                        continue
                    hops = int(row["hops_to_sink"]) - 2
                    latencies[frag_num][hops].append(
                            1000 * (float(row["recv_time"]) -
                                    float(row["send_time"]))
                        )
    style = {"linewidth": .75}
    alphas = [0.9, 0.8, 0.7, 0.6, 0.5]
    assert len(alphas) == (MAX_HOPS - 2)
    frags_legend_elements = [None for _ in MODES_BINS[mode]]
    for h in range(MAX_HOPS - 2):
        if o == 0:
            hops_legend_style = {}
            hops_legend_style.update(style)
            hops_legend_style["color"] = hsv_to_rgb((0, 0, 1 - alphas[h]))
            hops_legend_style["ls"] = "-"
            hops_legend_elements.append(
                Line2D([0], [0], label="{} hops".format(h + 2),
                       **hops_legend_style)
            )
        max_frag = 15
        for frag_num in range(max_frag):
            if frag_num >= len(MODES_BINS[mode]):
                break
            if (frag_num + 1) < len(MODES_BINS[mode]):
                limits = (MODES_BINS[mode][frag_num],
                          MODES_BINS[mode][frag_num + 1])
            elif len(MODES_BINS[mode]) < 11:
                limits = (MODES_BINS[mode][frag_num],
                          "?")
            else:
                limits = (MODES_BINS[mode][frag_num],
                          1024)
            dataset = np.array(
                latencies[frag_num][h]
            )
            dataset_exp = np.array(
                exp[frag_num][h]
            )
            dataset = dataset[~np.isnan(dataset)]
            dataset_exp = dataset_exp[~np.isnan(dataset_exp)]
            style["color"] = hsv_to_rgb(
                ((frag_num / (max_frag - 1)) * 5/6, 1.0, alphas[h])
            )
            if h == 0:
                frags_legend_elements[frag_num] = \
                    Line2D([0], [0], label="{} ({}{} bytes)"
                           .format(frag_num + 1, "≤"
                                   if (limits == "?" or limits[1] == 1024)
                                   else "<", limits[1]),
                           **style)
            if len(dataset) == 0:
                continue
            style["alpha"] = alphas[h]
            exp_style = {}
            exp_style.update(style)
            exp_style["linestyle"] = ":"
            bins = np.arange(
                np.floor(dataset.min() * 10),
                np.ceil(dataset.max() * 10)
            ) / 10
            if len(dataset_exp):
                bins_exp = np.arange(
                    np.floor(dataset_exp.min() * 10),
                    np.ceil(dataset_exp.max() * 10)
                ) / 10
            else:
                bins_exp = np.array([0,1])
            hist, x = np.histogram(dataset, bins=bins, density=1)
            hist_exp, x_exp = np.histogram(dataset_exp, bins=bins_exp, density=1)
            if (x.shape[0] < 2):
                continue
            dx = x[1] - x[0]
            cumsum = np.cumsum(hist) * dx
            subplot.plot(x[1:], [h + 2 for _ in range(len(x) - 1)], cumsum, **style)
            if (x_exp.shape[0] >= 2):
                dx_exp = x_exp[1] - x_exp[0]
                cumsum_exp = np.cumsum(hist_exp) * dx_exp
                subplot.plot(x_exp[1:], [h + 2 for _ in range(len(x_exp) - 1)],
                             cumsum_exp, **exp_style)
    plt.setp(subplot.get_xticklabels(), fontsize=8)
    plt.setp(subplot.get_yticklabels(), fontsize=8)
    plt.setp(subplot.get_zticklabels(), fontsize=8)
    if mode.startswith("sfr"):
        subplot.set_xlim((0, 35000))
        subplot.set_xticks(list(subplot.get_xticks()) + [700])
        xlabels = ["{:.1f}".format(x) for x in subplot.get_xticks() / 1000]
        subplot.set_xticklabels([""] + xlabels[1:])
        subplot.set_xlabel("Latency [s]", fontsize=8)
    else:
        subplot.set_xlim((0, 700))
        subplot.set_xlabel("Latency [ms]", fontsize=8)
    subplot.xaxis.pane.fill = False
    subplot.yaxis.pane.fill = False
    subplot.zaxis.pane.fill = False
    subplot.xaxis.pane.set_edgecolor("lightgray")
    subplot.yaxis.pane.set_edgecolor("lightgray")
    subplot.zaxis.pane.set_edgecolor("lightgray")
    subplot.grid(True, color="lightgray")
    subplot.set_zlim((0, 1))
    subplot.set_zlabel("CDF", fontsize=8)
    subplot.set_ylim((2, MAX_HOPS))
    subplot.set_ylabel("Source-to-sink distance [hops]", fontsize=8)
    anchor = (1.01, 1.3)
    subplot.add_artist(
        subplot.legend(frags_legend_elements,
                       [e.get_label() for e in frags_legend_elements],
                       title="Number of Fragments",
                       loc="upper center", ncol=6,# bbox_to_anchor=anchor,
                       fontsize=8, title_fontsize=8, bbox_to_anchor=(.5,-.1))
    )
    plt.tight_layout()
    plt.savefig(os.path.join(DATA_PATH,
                             "{}.{}.lat_cdf.svg"
                             .format(",".join(networks), mode)),
                bbox_inches="tight")
    plt.show()
anchor = (.5, 1.2)
# fig.tight_layout()
# plt.show()
