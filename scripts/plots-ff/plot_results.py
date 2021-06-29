#!/usr/bin/env python3
#
# Copyright (C) 2019 Freie Universität Berlin
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

import argparse
import copy
import csv
import logging
import matplotlib
import numpy as np
import os
import re

from matplotlib import pyplot as plt
from matplotlib.colors import ListedColormap, rgb_to_hsv, hsv_to_rgb, to_rgba
from matplotlib.patches import Patch

import parse_results

__author__ = "Martine S. Lenders"
__copyright__ = "Copyright 2019 Freie Universität Berlin"
__license__ = "LGPL v2.1"
__email__ = "m.lenders@fu-berlin.de"

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.environ.get("DATA_PATH",
                           os.path.join(SCRIPT_PATH, "..", "..", "results"))

COLORS = {
    "reass": "#2245E0",
    "fwd": "#E0B01F",
    "sfr-win1ifg100arq1200r4dg0": "#A0E00B",
    "sfr-win1ifg100arq1200r4dg1": "#A0E00B",
    "sfr-win1ifg100arq2400r4dg0": "#A0E00B",
    "sfr-win1ifg100arq2400r4dg1": "#A0E00B",
    "sfr-win1ifg200arq1200r4dg0": "#A0E00B",
    "sfr-win1ifg200arq1200r4dg1": "#A0E00B",
    "sfr-win1ifg200arq2400r4dg0": "#A0E00B",
    "sfr-win1ifg200arq2400r4dg1": "#A0E00B",
    "sfr-win1ifg500arq1200r4dg0": "#A0E00B",
    "sfr-win1ifg500arq1200r4dg1": "#A0E00B",
    "sfr-win1ifg500arq2400r4dg0": "#A0E00B",
    "sfr-win1ifg500arq2400r4dg1": "#A0E00B",
    "sfr-win2ifg100arq1200r4dg0": "#A0E00B",
    "sfr-win2ifg100arq1200r4dg1": "#A0E00B",
    "sfr-win2ifg100arq2400r4dg0": "#A0E00B",
    "sfr-win2ifg100arq2400r4dg1": "#A0E00B",
    "sfr-win2ifg200arq1200r4dg0": "#A0E00B",
    "sfr-win2ifg200arq1200r4dg1": "#A0E00B",
    "sfr-win2ifg200arq2400r4dg0": "#A0E00B",
    "sfr-win2ifg200arq2400r4dg1": "#A0E00B",
    "sfr-win2ifg500arq1200r4dg0": "#A0E00B",
    "sfr-win2ifg500arq1200r4dg1": "#A0E00B",
    "sfr-win2ifg500arq2400r4dg0": "#A0E00B",
    "sfr-win2ifg500arq2400r4dg1": "#A0E00B",
    "sfr-win5ifg100arq1200r4dg0": "#A0E00B",
    "sfr-win5ifg100arq1200r4dg1": "#A0E00B",
    "sfr-win5ifg100arq2400r4dg0": "#A0E00B",
    "sfr-win5ifg100arq2400r4dg1": "#A0E00B",
    "sfr-win5ifg200arq1200r4dg0": "#A0E00B",
    "sfr-win5ifg200arq1200r4dg1": "#A0E00B",
    "sfr-win5ifg200arq2400r4dg0": "#A0E00B",
    "sfr-win5ifg200arq2400r4dg1": "#A0E00B",
    "sfr-win5ifg500arq1200r4dg0": "#A0E00B",
    "sfr-win5ifg500arq1200r4dg1": "#A0E00B",
    "sfr-win5ifg500arq2400r4dg0": "#A0E00B",
    "sfr-win5ifg500arq2400r4dg1": "#A0E00B",
    "e2e": "#E05851",
}
MODES_READABLE = {
    "reass": "HWR",
    "fwd": "FF",
    "sfr-win1ifg100arq1200r4dg0": "SFR",    # " (1,100,1200,4,0)",
    "sfr-win1ifg100arq1200r4dg1": "SFR",    # " (1,100,1200,4,1)",
    "sfr-win1ifg100arq2400r4dg0": "SFR",    # " (1,100,2400,4,0)",
    "sfr-win1ifg100arq2400r4dg1": "SFR",    # " (1,100,2400,4,1)",
    "sfr-win1ifg200arq1200r4dg0": "SFR",    # " (1,200,1200,4,0)",
    "sfr-win1ifg200arq1200r4dg1": "SFR",    # " (1,200,1200,4,1)",
    "sfr-win1ifg200arq2400r4dg0": "SFR",    # " (1,200,2400,4,0)",
    "sfr-win1ifg200arq2400r4dg1": "SFR",    # " (1,200,2400,4,1)",
    "sfr-win1ifg500arq1200r4dg0": "SFR",    # " (1,500,1200,4,0)",
    "sfr-win1ifg500arq1200r4dg1": "SFR",    # " (1,500,1200,4,1)",
    "sfr-win1ifg500arq2400r4dg0": "SFR",    # " (1,500,2400,4,0)",
    "sfr-win1ifg500arq2400r4dg1": "SFR",    # " (1,500,2400,4,1)",
    "sfr-win2ifg100arq1200r4dg0": "SFR",    # " (2,100,1200,4,0)",
    "sfr-win2ifg100arq1200r4dg1": "SFR",    # " (2,100,1200,4,1)",
    "sfr-win2ifg100arq2400r4dg0": "SFR",    # " (2,100,2400,4,0)",
    "sfr-win2ifg100arq2400r4dg1": "SFR",    # " (2,100,2400,4,1)",
    "sfr-win2ifg200arq1200r4dg0": "SFR",    # " (2,200,1200,4,0)",
    "sfr-win2ifg200arq1200r4dg1": "SFR",    # " (2,200,1200,4,1)",
    "sfr-win2ifg200arq2400r4dg0": "SFR",    # " (2,200,2400,4,0)",
    "sfr-win2ifg200arq2400r4dg1": "SFR",    # " (2,200,2400,4,1)",
    "sfr-win2ifg500arq1200r4dg0": "SFR",    # " (2,500,1200,4,0)",
    "sfr-win2ifg500arq1200r4dg1": "SFR",    # " (2,500,1200,4,1)",
    "sfr-win2ifg500arq2400r4dg0": "SFR",    # " (2,500,2400,4,0)",
    "sfr-win2ifg500arq2400r4dg1": "SFR",    # " (2,500,2400,4,1)",
    "sfr-win5ifg100arq1200r4dg0": "SFR",    # " (5,100,1200,4,0)",
    "sfr-win5ifg100arq1200r4dg1": "SFR",    # " (5,100,1200,4,1)",
    "sfr-win5ifg100arq2400r4dg0": "SFR",    # " (5,100,2400,4,0)",
    "sfr-win5ifg100arq2400r4dg1": "SFR",    # " (5,100,2400,4,1)",
    "sfr-win5ifg200arq1200r4dg0": "SFR",    # " (5,200,1200,4,0)",
    "sfr-win5ifg200arq1200r4dg1": "SFR",    # " (5,200,1200,4,1)",
    "sfr-win5ifg200arq2400r4dg0": "SFR",    # " (5,200,2400,4,0)",
    "sfr-win5ifg200arq2400r4dg1": "SFR",    # " (5,200,2400,4,1)",
    "sfr-win5ifg500arq1200r4dg0": "SFR",    # " (5,500,1200,4,0)",
    "sfr-win5ifg500arq1200r4dg1": "SFR",    # " (5,500,1200,4,1)",
    "sfr-win5ifg500arq2400r4dg0": "SFR",    # " (5,500,2400,4,0)",
    "sfr-win5ifg500arq2400r4dg1": "SFR",    # " (5,500,2400,4,1)",
    "e2e": "E2E",
}
SAVEFIG_OPTS = {
   "dpi": 150,
    "bbox_inches": "tight"
}

NAME_PATTERN = parse_results.NAME_PATTERN.format(
    mode=r"(?P<mode>(reass|fwd|e2e|sfr-\w+))",
    data_len=r"(?P<data_len>\d+)",
    delay=r"\d+"
)
TIMES_CSV_NAME_PATTERN_FMT = "{}.times.csv".format(parse_results.NAME_PATTERN)
STATS_CSV_NAME_PATTERN_FMT = "{}.stats.csv".format(parse_results.NAME_PATTERN)

RUNS = 3
MODES = [
     "reass",
     "fwd",
     "e2e",
     "sfr-win1ifg100arq1200r4dg0",
 ]
DATA_LENS = [x for x in range(16, 1025, 16)]
DELAY = 10000
MAX_HOPS = 7
BAR_WIDTH = (1 / len(MODES)) - .05


def plot_l2_retrans(runs=RUNS):
    plt.clf()
    offset = {
            "reass": -0.30,
            "fwd": -0.15,
            "e2e": 0.15,
            "sfr-win1ifg100arq1200r4dg0": 0.30,
        }
    networks = set()
    mode_marker = {"fwd": "x", "reass": "+", "e2e": ".", "sfr-win1ifg100arq1200r4dg0": "*"}
    for mode in MODES:
        l2_retrans = []
        means = [[] for _ in DATA_LENS]
        for i, data_len in enumerate(DATA_LENS, 1):
            filenames = _get_files(DELAY, mode, data_len, runs,
                                   STATS_CSV_NAME_PATTERN_FMT)
            c = re.compile(NAME_PATTERN)
            for _, filename in filenames[-runs:]:
                filename = os.path.join(DATA_PATH, filename)
                m = c.search(filename)
                assert(m is not None)
                networks.add(m.group("network"))
                with open(filename) as csvfile:
                    reader = csv.DictReader(csvfile, delimiter=";")
                    for row in reader:
                        l2_retrans.append((data_len, int(row["l2_retrans"] or 0)))
            means[i - 1] = np.mean(
                    [l[1] for l in l2_retrans if l[0] == data_len]
                )
        means = np.array(means)
        means_mask = np.isfinite(means)
        index = np.array(DATA_LENS)
        if plt.rcParams["text.usetex"]:
            markeropts = {"markersize": 5}
        else:
            markeropts = {"markersize": 10}
        plt.plot(index[means_mask], means[means_mask],
                 marker=mode_marker[mode],
                 label=MODES_READABLE[mode],
                 **markeropts)
        plt.scatter([l[0] + offset[mode] for l in l2_retrans],
                    [l[1] for l in l2_retrans],
                    marker=mode_marker[mode], alpha=0.2)
    ax = plt.gca()
    ax.set_yscale("symlog")
    _plot_show_and_save(
            networks,
            "l2_retrans",
            "Link-layer retransmissions",
            "Failed transmissions [#]",
            runs,
            (0, 7000)
        )


def plot_pktbuf(runs=RUNS):
    plt.clf()
    networks = set()
    for o, mode in enumerate(MODES):
        pktbuf = {s: [] for s in DATA_LENS}
        for size in DATA_LENS:
            filenames = _get_files(DELAY, mode, size, runs,
                                   STATS_CSV_NAME_PATTERN_FMT)
            c = re.compile(NAME_PATTERN)
            for _, filename in filenames[-runs:]:
                filename = os.path.join(DATA_PATH, filename)
                m = c.search(filename)
                assert(m is not None)
                network = m.group("network")
                networks.add(network)
                sink = network.split("x")[0]
                with open(filename) as csvfile:
                    reader = csv.DictReader(csvfile, delimiter=";")
                    for row in reader:
                        if row["node"] != sink and \
                           row["pktbuf_size"] != "" and \
                           row["pktbuf_usage"] != "":
                            pktbuf[size].append(
                                    int(row["pktbuf_usage"]) /
                                    int(row["pktbuf_size"]) * 100
                                )
                        elif row["pktbuf_size"] == "" or \
                                row["pktbuf_usage"] == "":
                            logging.warn("{}: Incomplete data set, packet "
                                         "buffer data missing for {}"
                                         .format(filename, row["node"]))
        means = np.array([np.mean(pktbuf[s]) for s in DATA_LENS]) \
            .astype(np.double)
        means_mask = np.isfinite(means)
        errs = np.array([np.std(pktbuf[s]) for s in DATA_LENS])
        index = np.array(DATA_LENS)
        style = {}
        style["color"] = COLORS[mode]
        if means_mask.any():
            plt.fill_between(index[means_mask],
                             means[means_mask] - errs[means_mask],
                             means[means_mask] + errs[means_mask],
                             alpha=.25, linewidth=0, **style)
            plt.errorbar(index[means_mask], means[means_mask],
                         label=MODES_READABLE[mode], **style)
    _plot_show_and_save(
            networks,
            "pktbuf",
            "Packet buffer usage",
            "Max. packet buffer usage [%]",
            runs,
            (0, 75)
        )


def plot_rbuf_full(runs=RUNS):
    plt.clf()
    offset = {
            "reass": -0.3,
            "fwd": -0.2,
            "fwd_vrb": 0.1,
            "e2e": 0.1,
            "sfr-win1ifg100arq1200r4dg0": 0.2,
            "sfr-win1ifg100arq1200r4dg0_vrb": 0.3,
        }
    networks = set()
    mode_marker = {"fwd": "x", "reass": "+", "e2e": ".", "sfr-win1ifg100arq1200r4dg0": "*",
                   "fwd_vrb": "v", "sfr-win1ifg100arq1200r4dg0_vrb": "^"}
    for mode in MODES:
        rbuf_full = []
        vrb_full = []
        rbuf_full_m = [[] for _ in DATA_LENS]
        vrb_full_m = [[] for _ in DATA_LENS]
        for i, size in enumerate(DATA_LENS, 1):
            filenames = _get_files(DELAY, mode, size, runs,
                                   STATS_CSV_NAME_PATTERN_FMT)
            c = re.compile(NAME_PATTERN)
            for _, filename in filenames[-runs:]:
                filename = os.path.join(DATA_PATH, filename)
                m = c.search(filename)
                assert(m is not None)
                network = m.group("network")
                networks.add(network)
                sink = network.split("x")[0]
                with open(filename) as csvfile:
                    reader = csv.DictReader(csvfile, delimiter=";")
                    for row in reader:
                        if row["node"] != sink:
                            if row["rbuf_full"] != "":
                                rbuf_full.append(
                                        (size, int(row["rbuf_full"]))
                                    )
                            else:
                                logging.warn("{}: Incomplete data set, "
                                             "reassembly buffer data "
                                             "missing for {}"
                                             .format(filename,
                                                     row["node"]))
                            if mode not in ["reass", "e2e"] and \
                               row["vrb_full"] != "":
                                vrb_full.append(
                                        (size, int(row["vrb_full"]))
                                    )
                            elif mode not in ["reass", "e2e"] and \
                                 row["vrb_full"] == "":
                                logging.warn("{}: Incomplete data set, "
                                             "VRB data missing for {}"
                                             .format(filename,
                                                     row["node"]))
            rbuf_full_m[i - 1] = np.mean(
                    [e[1] for e in rbuf_full if e[0] == size]
                )
            vrb_full_m[i - 1] = np.mean(
                    [e[1] for e in vrb_full if e[0] == size]
                )
        means = np.array(rbuf_full_m)
        means_mask = np.isfinite(means)
        index = np.array(DATA_LENS)
        if plt.rcParams["text.usetex"]:
            markeropts = {"markersize": 5}
        else:
            markeropts = {"markersize": 10}
        plt.plot(index[means_mask], means[means_mask],
                 marker=mode_marker[mode], label=MODES_READABLE[mode],
                 **markeropts)
        plt.scatter([e[0] + offset[mode] for e in rbuf_full],
                    [e[1] for e in rbuf_full],
                    marker=mode_marker[mode], alpha=0.2)
        if mode not in ["reass", "e2e"]:
            means = np.array(vrb_full_m)
            means_mask = np.isfinite(means)
            tmp = "{}_vrb".format(mode)
            plt.plot(index[means_mask], means[means_mask],
                     marker=mode_marker[tmp],
                     label="{} (VRB)".format(MODES_READABLE[mode]),
                     **markeropts)
            plt.scatter([e[0] + offset[tmp] for e in vrb_full],
                        [e[1] for e in vrb_full],
                        marker=mode_marker[tmp], alpha=0.1)
    ax = plt.gca()
    ax.set_yscale("symlog")
    _plot_show_and_save(
        networks,
        "rbuf_full",
        "Reassembly buffer",
        "Filled reassembly buffer events [#]",
        runs,
        (0, 7000)
    )


def plot_rbuf_full_vs_pktbuf(runs=RUNS):
    plt.clf()
    mode = "fwd"
    networks = set()
    rbuf_full = []
    pktbuf = []
    for i, data_len in enumerate(DATA_LENS, 1):
        filenames = _get_files(DELAY, mode, data_len, runs,
                               STATS_CSV_NAME_PATTERN_FMT)
        c = re.compile(NAME_PATTERN)
        for _, filename in filenames[-runs:]:
            filename = os.path.join(DATA_PATH, filename)
            m = c.search(filename)
            assert(m is not None)
            network = m.group("network")
            networks.add(network)
            sink = network.split("x")[0]
            with open(filename) as csvfile:
                reader = csv.DictReader(csvfile, delimiter=";")
                for row in reader:
                    if row["node"] != sink:
                        rbuf_full.append(int(row["rbuf_full"] or 0))
                        if all(row[col] != "" for col
                                in ["pktbuf_usage", "pktbuf_size"]):
                            pktbuf.append(100 * int(row["pktbuf_usage"]) /
                                          int(row["pktbuf_size"]))
                        else:
                            pktbuf.append(np.nan)
    rbuf_full = np.array(rbuf_full)
    pktbuf = np.array(pktbuf)
    base = rgb_to_hsv(to_rgba("#ff9800")[:3])
    colors = np.array(
            [hsv_to_rgb([base[0], base[1] * (i / 255), base[2]])
             for i in range(256)]
        )
    cmap = ListedColormap(colors)
    hb = plt.hexbin(rbuf_full, pktbuf, cmap=cmap,
                    bins="log", gridsize=25, label=MODES_READABLE[mode])
    rbuf_full = np.sort(rbuf_full)
    plt.ylim((0, 100))
    plt.xlim(left=0)
    xlabel = "Filled reassembly buffer events [#]"
    ylabel = "Max. packet buffer usage [%]"
    if plt.rcParams["text.usetex"]:
        xlabel = xlabel.replace("#", r"\#")
        ylabel = ylabel.replace("%", r"\%")
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    ax = plt.gca()
    fig = plt.gcf()
    cb = fig.colorbar(hb, ax=ax)
    cb.set_label('Multiplicity of coinciding events')
    filename = "{}.{}.{}".format(
            os.path.join(DATA_PATH, ",".join(networks)),
            "rbuf_full_vs_pktbuf",
            "pgf" if plt.rcParams["text.usetex"] else "svg"
        )
    _savefig(filename)
    plt.show()


def _exp_dict(delay, mode, data_len):
    return locals()


def _get_files(delay, mode, data_len, runs, pattern):
    exp_dict = _exp_dict(delay, mode, data_len)
    pattern = pattern.format(**exp_dict)
    filenames = filter(lambda x: x[0] is not None,
                       map(lambda f: (re.match(pattern, f), f),
                           os.listdir(DATA_PATH)))
    filenames = sorted(filenames,
                       key=lambda x: int(x[0].group("timestamp")))
    if (len(filenames) < runs) and (len(filenames) > 0):
        logging.warning(
            "m{mode}__r{data_len}Bx{delay}ms only has {runs} of "
            "{total_runs} expected runs"
            .format(runs=len(filenames), total_runs=runs, **exp_dict)
        )
    return filenames


def _reject_outliers(data, m=2):
    d = np.abs(data - np.median(data))
    mdev = np.median(d)
    s = d / mdev if mdev else 0.
    data = np.array(data)
    return data[s < m]


def _plot_show_and_save(networks, plotname, title, ylabel, runs,
                        ylim=None, legends=None):
    plt.xlim(16, DATA_LENS[-1])
    if ylim is not None:
        if issubclass(type(ylim), dict):
            plt.ylim(**ylim)
        else:
            plt.ylim(*ylim)
    plt.xticks(DATA_LENS[0:len(DATA_LENS):8] + [1024])
    if plt.rcParams["text.usetex"]:
        plt.xlabel(r"UDP payload length [bytes]")
        plt.ylabel(ylabel.replace("%", r"\%"))
        plt.ylabel(ylabel.replace("#", r"\#"))
    else:
        plt.title(title)
        plt.xlabel("UDP payload length [bytes]")
        plt.ylabel(ylabel)
    if legends:
        legs = []
        for l in legends:
            legs.append(plt.legend(**l))
        for l in legs[:-1]:
            plt.gca().add_artist(l)
    else:
        legend_params = {}
        if plotname == "pdr":
            legend_params["loc"] = "upper right"
        elif plotname in ["rbuf_full", "l2_retrans"]:
            legend_params["loc"] = "lower right"
        else:
            legend_params["loc"] = "upper left"
        if plotname == "lat":
            legend_params["ncol"] = 2
        plt.legend(**legend_params)
    filename = "{}.{}.{}".format(
            os.path.join(DATA_PATH, ",".join(sorted(networks))),
            plotname, "pgf" if plt.rcParams["text.usetex"] else "svg"
        )
    _savefig(filename)
    plt.show()


def _savefig(filename):
    if "figsize" in SAVEFIG_OPTS:
        fig = plt.gcf()
        fig.set_size_inches(*SAVEFIG_OPTS["figsize"])
    plt.margins(0)
    plt.savefig(filename, **SAVEFIG_OPTS)


def _configure_plot(pgf=False, figsize=100):
    plt.rc("errorbar", capsize=3)
    SAVEFIG_OPTS["figsize"] = (100, 80)
    if pgf:
        normalsize = 10 * (figsize / 100)
        scriptsize = 7 * (figsize / 100)
        SAVEFIG_OPTS["figsize"] = (3.27835 * (figsize / 100),
                                   1.84409 * (figsize / 100))
        matplotlib.use("pgf")
        plt.subplots_adjust(0, 0)
        plt.rc("text", usetex=True)
        plt.rc("errorbar", capsize=2)
        plt.rc("font", family="serif", size=normalsize)
        plt.rc("axes", labelsize=scriptsize, linewidth=.5)
        plt.rc("grid", linewidth=.5)
        plt.rc("lines", linewidth=.5, markersize=3, markeredgewidth=.5)
        plt.rc("patch", linewidth=.5)
        plt.rc("xtick", labelsize=scriptsize)
        plt.rc("xtick.major", width=.5)
        plt.rc("xtick.minor", width=.3)
        plt.rc("ytick", labelsize=scriptsize)
        plt.rc("ytick.major", width=.5)
        plt.rc("ytick.minor", width=.3)
        plt.rc("legend", fontsize=scriptsize, columnspacing=0.4,
               borderpad=.2, handlelength=1, handletextpad=.4)
        plt.rc("pgf", preamble=[
            r"\usepackage{units}",
            r"\usepackage{metalogo}",
            r"\usepackage{unicode-math}",
        ])


def _check_logs():
    comp = re.compile(parse_results.LOG_NAME_PATTERN)
    for logname in os.listdir(DATA_PATH):
        match = comp.match(logname)
        if match is not None:
            logname = os.path.join(DATA_PATH, logname)
            if os.path.exists(parse_results.times_csvname(logname)) and \
               os.path.exists(parse_results.stats_csvname(logname)):
                # don't redo existing logs
                continue
            parse_results.log_to_csvs(logname, data_path=DATA_PATH,
                                      **parse_results.match_to_dict(match))


PLOT_FUNCTIONS = {
    "l2_retrans": plot_l2_retrans,
    "pktbuf": plot_pktbuf,
    "rbuf_full": plot_rbuf_full,
    "rbuf_full_vs_pktbuf": plot_rbuf_full_vs_pktbuf,
}


def main():
    logging.basicConfig(format='%(levelname)s: %(message)s',
                        level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("-R", "--runs", type=int, default=RUNS,
                        help="Number of runs to plot (default: 10)")
    parser.add_argument("-p", "--pgf", action="store_true",
                        help="Output as PGF file instead of SVG")
    parser.add_argument("-f", "--figsize", nargs="?", default=100, type=int,
                        help="With --pgf: size of the figure in percent, "
                             "ignored without --pgf (default: 100%%)")
    parser.add_argument("result", nargs="*", help="Results to plot "
                        "(default: {})".format(
                            ' '.join(sorted(PLOT_FUNCTIONS.keys()))
                        ), choices=list(PLOT_FUNCTIONS.keys()).append([]))
    args = parser.parse_args()
    if not args.result:
        args.result = sorted(PLOT_FUNCTIONS.keys())
    _configure_plot(args.pgf, args.figsize)
    _check_logs()
    for result in args.result:
        PLOT_FUNCTIONS[result](runs=args.runs)


if __name__ == "__main__":
    main()
