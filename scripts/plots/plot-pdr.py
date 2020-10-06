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
    "sfr-win1ifg100arq1200r4dg0": "SFR (W:1,G:0.1ms,A:1.2s)",
    "sfr-win1ifg100arq2400r4dg0": "SFR (W:1,G:0.1ms,A:2.4s)",
    "sfr-win1ifg500arq1200r4dg0": "SFR (W:1,G:0.5ms,A:1.2s)",
    "sfr-win1ifg500arq2400r4dg0": "SFR (W:1,G:0.5ms,A:2.4s)",
    "sfr-win5ifg100arq1200r4dg0": "SFR (W:5,G:0.1ms,A:1.2s)",
    "sfr-win5ifg100arq2400r4dg0": "SFR (W:5,G:0.1ms,A:2.4s)",
    "sfr-win5ifg500arq1200r4dg0": "SFR (W:5,G:0.5ms,A:1.2s)",
    "sfr-win5ifg500arq2400r4dg0": "SFR (W:5,G:0.5ms,A:2.4s)",
    "e2e": "E2E",
}


def heatmap(data, row_labels, col_labels, ax=None,
            cbar_kw={}, cbarlabel="", **kwargs):
    """
    Create a heatmap from a numpy array and two lists of labels.

    Parameters
    ----------
    data
        A 2D numpy array of shape (N, M).
    row_labels
        A list or array of length N with the labels for the rows.
    col_labels
        A list or array of length M with the labels for the columns.
    ax
        A `matplotlib.axes.Axes` instance to which the heatmap is plotted.  If
        not provided, use current axes or create a new one.  Optional.
    cbar_kw
        A dictionary with arguments to `matplotlib.Figure.colorbar`.  Optional.
    cbarlabel
        The label for the colorbar.  Optional.
    **kwargs
        All other arguments are forwarded to `imshow`.
    """

    if not ax:
        ax = plt.gca()

    if np.isnan(data).any():
        styles = {}
        styles.update(kwargs)
        if styles["cmap"] == "cool_r":
            styles["cmap"] = "bwr"
        else:
            styles["cmap"] = "cool_r"
        ax.imshow(np.where(np.isnan(data), 1, float("nan")), **styles)
    # Plot the heatmap
    im = ax.imshow(data, **kwargs)

    # Create colorbar
    cbar_kw["orientation"] = "vertical"
    cbar_kw["shrink"] = .27
    cbar_kw["aspect"] = 15
    cbar_kw["pad"] = 0
    cbar_kw["ticks"] = [0, 25, 50, 100]
    cbar_kw["panchor"] = (-1.0, 1.1)
    cbar = ax.figure.colorbar(im, ax=ax, **cbar_kw)
    cbar.ax.set_ylabel(cbarlabel, fontsize=4)
    cbar.ax.tick_params(labelsize=6)

    ax.xaxis.set_major_locator(MultipleLocator(1))
    # We want to show all ticks...
    ax.set_xticks(np.arange(data.shape[1]), minor=True)
    ax.set_yticks(np.arange(data.shape[0]))
    # ... and label them with the respective list entries.
    ax.set_xticklabels([0] + list(col_labels), fontsize=5)
    ax.set_yticklabels(row_labels, fontsize=6)

    # Let the horizontal axes labeling appear on top.
    ax.tick_params(top=True, bottom=False,
                   labeltop=True, labelbottom=False)

    # Rotate the tick labels and set their alignment.
    plt.setp(ax.get_xticklabels(), rotation=-90, va="bottom")

    ax.tick_params(axis='x', which='major', pad=0)

    ax.set_xticks(np.arange(data.shape[1]+1)-.5, minor=True)
    ax.set_yticks(np.arange(data.shape[0]+1)-.5, minor=True)
    ax.tick_params(which="minor", bottom=False, left=False)

    return im, cbar


def annotate_heatmap(im, data=None, valfmt="{x:.2f}",
                     textcolors=("white", "black"),
                     threshold=None, **textkw):
    """
    A function to annotate a heatmap.

    Parameters
    ----------
    im
        The AxesImage to be labeled.
    data
        Data used to annotate.  If None, the image's data is used.  Optional.
    valfmt
        The format of the annotations inside the heatmap.  This should either
        use the string format method, e.g. "$ {x:.2f}", or be a
        `matplotlib.ticker.Formatter`.  Optional.
    textcolors
        A pair of colors.  The first is used for values below a threshold,
        the second for those above.  Optional.
    threshold
        Value in data units according to which the colors from textcolors are
        applied.  If None (the default) uses the middle of the colormap as
        separation.  Optional.
    **kwargs
        All other arguments are forwarded to each call to `text` used to create
        the text labels.
    """

    if not isinstance(data, (list, np.ndarray)):
        data = im.get_array()

    # Normalize the threshold to the images color range.
    if threshold is not None:
        threshold = im.norm(threshold)
    else:
        threshold = im.norm(data.max())/2.

    # Set default alignment to center, but allow it to be
    # overwritten by textkw.
    kw = dict(horizontalalignment="center",
              verticalalignment="center")
    kw.update(textkw)

    # Get the formatter in case a string is supplied
    if isinstance(valfmt, str):
        valfmt = matplotlib.ticker.StrMethodFormatter(valfmt)

    # Loop over the data and create a `Text` for each "pixel".
    # Change the text's color depending on the data.
    texts = []
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            kw.update(color=textcolors[int(im.norm(data[i, j]) > threshold)])
            text = im.axes.text(j, i, valfmt(data[i, j], None), **kw)
            texts.append(text)

    return texts


matplotlib.rcParams["axes.labelsize"] = 8
runs = 3
_check_logs()
plt.clf()
networks = set()
matrix = []
last = 100
for o, mode in enumerate(MODES):
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
    means = np.array([np.mean(pdrs[s]) for s in DATA_LENS]) \
        .astype(np.double)
    matrix.append(means)
SFR_PATTERN = "sfr-win(\d+)ifg(\d+)arq(\d+)r(\d+)dg(\d+)"
c = re.compile(SFR_PATTERN)
modes_tuple = []
for i, mode in enumerate(MODES):
    m = c.match(mode)
    if m:
        modes_tuple.append(
            ((int(m.group(1)),int(m.group(3)),int(m.group(2)),not int(m.group(5))), i)
        )
    elif mode == "reass":
        modes_tuple.append((tuple(4 * [0]), i))
    else:
        modes_tuple.append((tuple(4 * [float("inf")]), i))
idx = [i for _, i in sorted(modes_tuple)]
matrix = np.array(matrix) #.transpose()
fig, ax = plt.subplots()

modes = np.array(MODES)[idx]
im, cbar = heatmap(matrix[idx, :], [MODES_READABLE[m]
                   for i, m in enumerate(modes)], DATA_LENS, ax=ax,
                   cmap="pink", cbarlabel="Mean packet delivery rate [%]",
                   aspect=1.6,
                   interpolation=None,
                   cbar_kw={"ticks": [0, 25, 50, 75, 100],
                            "pad": 0.1})
plt.xlabel("UDP payload length [bytes]")
ax.xaxis.set_label_position('top')
plt.ylabel("Mode")

fig.tight_layout()
plt.savefig(os.path.join(DATA_PATH, "{}.pdr_hm.svg".format(",".join(networks))), bbox_inches="tight")
plt.show()
