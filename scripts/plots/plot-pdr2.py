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
import numpy as np
import matplotlib
matplotlib.use("pgf")
from matplotlib.ticker import MultipleLocator
import matplotlib.pyplot as plt

import parse_results
from plot_results import DATA_PATH, DELAY, NAME_PATTERN, \
                         TIMES_CSV_NAME_PATTERN_FMT, \
                         STATS_CSV_NAME_PATTERN_FMT, \
                         _check_logs, _get_files, _reject_outliers


DATA_LENS = tuple(range(16, 1025, 16))
MODES = [
    "reass",
    "sfr-win1ifg500arq1200r4dg0",
    "sfr-win1ifg100arq1200r4dg0",
    "sfr-win1ifg500arq2400r4dg0",
    "sfr-win1ifg100arq2400r4dg0",
    "sfr-win5ifg100arq1200r4dg0",
    "sfr-win5ifg500arq1200r4dg0",
    "sfr-win5ifg100arq2400r4dg0",
    "sfr-win5ifg500arq2400r4dg0",
    "fwd",
    "e2e",
]
MODES_READABLE = {
    "reass": "HWR",
    "fwd": "FF",
    "sfr-win1ifg100arq1200r4dg0": "SFR",
    "sfr-win1ifg100arq2400r4dg0": "SFR",
    "sfr-win1ifg500arq1200r4dg0": "SFR",
    "sfr-win1ifg500arq2400r4dg0": "SFR",
    "sfr-win5ifg100arq1200r4dg0": "SFR",
    "sfr-win5ifg100arq2400r4dg0": "SFR",
    "sfr-win5ifg500arq1200r4dg0": "SFR",
    "sfr-win5ifg500arq2400r4dg0": "SFR",
    "e2e": "E2E",
}
MODES_STYLES = {
    "reass": {"color": "#2245E0"},
    "fwd": {"color": "#E0B01F"},
    "sfr-win1ifg100arq1200r4dg0": {"color": "#A0E00B",
                                   "linewidth": 1, "dashes": (None, None)},
    "sfr-win1ifg100arq2400r4dg0": {"color": "#A0E00B",
                                   "linewidth": 1, "dashes": (1, 1)},
    "sfr-win1ifg500arq1200r4dg0": {"color": "#A0E00B",
                                   "linewidth": 1, "dashes": (4, 2)},
    "sfr-win1ifg500arq2400r4dg0": {"color": "#A0E00B",
                                   "linewidth": 1, "dashes": (4, 2, 1, 3)},
    "sfr-win5ifg100arq1200r4dg0": {"color": "#A0E00B",
                                   "linewidth": 1.25, "dashes": (None, None)},
    "sfr-win5ifg100arq2400r4dg0": {"color": "#A0E00B",
                                   "linewidth": 1.25, "dashes": (1, 3)},
    "sfr-win5ifg500arq1200r4dg0": {"color": "#A0E00B",
                                   "linewidth": 1.25, "dashes": (4, 2)},
    "sfr-win5ifg500arq2400r4dg0": {"color": "#A0E00B",
                                   "linewidth": 1.25, "dashes": (4, 2, 1, 3)},
    "e2e": {"color": "#E05851"},
}
MODES_PLOTS = {
    "non-sfr": ["reass", "fwd", "e2e"],
    "sfr-win1": [],
    "sfr-win5": [],
}


matplotlib.rcParams["figure.figsize"] = (3, 2)
matplotlib.rcParams["text.usetex"] = True
matplotlib.rcParams["pgf.texsystem"] = "xelatex"
matplotlib.rcParams["pgf.rcfonts"] = False
matplotlib.rcParams["font.family"] = "serif"
matplotlib.rcParams["font.serif"] = "Libertine"
matplotlib.rcParams["pgf.preamble"] = "\n".join([
     r'\usepackage{units}',          # load additional packages
     r'\usepackage{metalogo}',
     r'\usepackage{fontspec}',
     r'\setmainfont{Linux Libertine}',
     r'\setmonofont{Linux Libertine Mono}',
     r'\usepackage{unicode-math}',
     r'\setmathfont{Linux Libertine}'
 ])
runs = 3
_check_logs()
plt.clf()
networks = set()
means = {}
errs = {}
for mode in MODES:
    pdrs = {s: [] for s in DATA_LENS}
    for data_len in DATA_LENS:
        filenames = _get_files(DELAY, mode, data_len, runs,
                               TIMES_CSV_NAME_PATTERN_FMT)
        comp = re.compile(NAME_PATTERN)
        for _, filename in filenames[-runs:]:
            filename = os.path.join(DATA_PATH, filename)
            m = comp.search(filename)
            assert(m is not None)
            networks.add(m.group("network"))
            sends = 0
            receives = 0
            with open(filename) as csvfile:
                reader = csv.DictReader(csvfile, delimiter=";")
                for row in reader:
                    sends += 1
                    if row["recv_time"]:
                        receives += 1
                if (sends > 0):
                    pdrs[data_len].append(100 * receives / sends)
        pdrs[data_len] = _reject_outliers(pdrs[data_len])
    means[mode] = np.array([np.mean(pdrs[s]) for s in DATA_LENS]) \
                  .astype(np.double)

SFR_PATTERN = "sfr-win(\d+)ifg(\d+)arq(\d+)r(\d+)dg(\d+)"
c = re.compile(SFR_PATTERN)
idx = np.array(DATA_LENS)

for mode_plot in MODES_PLOTS:
    plt.clf()
    for mode in [m for m in sorted(MODES)
                 if m.startswith(mode_plot) or m in MODES_PLOTS[mode_plot]]:
        plt.xlabel("UDP payload length [bytes]")
        plt.xlim((0, 1024))
        plt.ylabel("Packet delivery ratio [%]")
        plt.ylim((0, 100))
        label = "{}".format(MODES_READABLE[mode])
        if mode_plot.startswith("sfr"):
            m = c.search(mode)
            assert m
            label += " (IFG: {:.1f}ms, ARQ: {:.1f}s)" \
                     .format(float(m.group(2)) / 1000, float(m.group(3)) / 1000)
        means_mask = np.isfinite(means[mode])
        plt.plot(idx[means_mask], means[mode][means_mask], label=label,
                 **MODES_STYLES[mode])
        plt.legend(loc="upper right")
    plt.savefig(os.path.join(DATA_PATH,
                "{}.{}.pdr.pdf".format(
                    ",".join(sorted(networks)),
                    mode_plot
                )), bbox_inches="tight")
    plt.savefig(os.path.join(DATA_PATH,
                "{}.{}.pdr.pgf".format(
                    ",".join(sorted(networks)),
                    mode_plot
                )), bbox_inches="tight")
