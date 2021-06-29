#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2020 Martine Lenders <m.lenders@fu-berlin.de>
#
# Distributed under terms of the MIT license.

import argparse
import csv
import matplotlib.lines as mlines
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import os
import re

PATTERN = r"_m(?P<mode>[a-z0-9]+)(-win(?P<win>\d+)ifg(?P<ifg>\d+)" \
          r"arq(?P<arq>\d+)r(?P<frag_retries>\d+)" \
          r"dg(?P<dg_retries>\d+))?_r(?P<data_len>\d+)Bx(?P<count>\d+)x" \
          r"(?P<delay>\d+)ms_\d+(?P<nc_conflict> \(conflicted[^\)]+\))?.*\.log"
OUT_PATTERN = r";(> )?out;"
DATA_PATH = os.path.join(os.environ["HOME"],
                         "Nextcloud/FUBox/6lo-comp-results")
CSV_NAME = os.path.join(DATA_PATH, "done.csv")
CSV_HEADER = ("data_len", "mode", "done", "count", "nc_conflict")
EXP_RUNS = 3
NODES = 47
WIN_SIZES = [1, 5]
IFGS = [100, 500]
DG_RETRIES = [0]
FONT_SIZE_SQUARE = 1.6


def transform_dict(log_dict):
    for int_value in ["win", "ifg", "arq", "frag_retries", "dg_retries",
                      "data_len", "count", "delay"]:
        if (int_value in log_dict) and \
           (log_dict[int_value] is not None):
            log_dict[int_value] = int(log_dict[int_value])
    for bool_value in ["nc_conflict"]:
        log_dict = (bool_value in log_dict) and \
                   (log_dict[bool_value] is not None)


def mode_tuple(log_dict):
    if "win" in log_dict and log_dict["win"] is not None:
        return log_dict["mode"], \
               (log_dict.get("win"), log_dict.get("ifg"), log_dict.get("arq"),
                log_dict.get("frag_retries"), log_dict.get("dg_retries"))
    else:
        return log_dict["mode"], None


def add_to_dict(d, data_len, mode, done, count, conflict):
    if data_len not in d:
        d[data_len] = {mode: [(done, count, conflict)]}
    elif mode not in d[data_len]:
        d[data_len][mode] = [(done, count, conflict)]
    else:
        d[data_len][mode].append((done, count, conflict))



def printProgressBar(iteration, total, prefix='', suffix='', decimals=1,
                     length=39, fill='X', printEnd="\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent
                                  complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}") \
              .format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end=printEnd)
    # Print New Line on Complete
    if iteration >= total:
        print()


def build_csv():
    logs = {}
    with open(CSV_NAME, "w") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(CSV_HEADER)
        listdir = os.listdir(DATA_PATH)
        listdir_len = len(listdir)
        prefix = "{:>20s}".format("Building CSV")
        printProgressBar(0, listdir_len, prefix=prefix)
        for progress, filename in enumerate(listdir, 1):
            if filename == csvfile:
                printProgressBar(progress, listdir_len, prefix=prefix)
                continue
            m = re.search(PATTERN, filename)
            if m is None:
                printProgressBar(progress, listdir_len, prefix=prefix)
                continue
            log = m.groupdict()
            transform_dict(log)
            data_len = log["data_len"]
            if data_len > 1024 or data_len < 2:
                continue
            mode = mode_tuple(log)
            if mode[0] == "sfr":
                if mode[1][0] not in WIN_SIZES:
                    printProgressBar(progress, listdir_len, prefix=prefix)
                    continue
                if mode[1][1] not in IFGS:
                    printProgressBar(progress, listdir_len, prefix=prefix)
                    continue
                if mode[1][4] not in DG_RETRIES:
                    printProgressBar(progress, listdir_len, prefix=prefix)
                    continue
            log["sent"] = 0
            with open(os.path.join(DATA_PATH, filename)) as f:
                for line in f:
                    m = re.search(OUT_PATTERN, line)
                    if m is not None:
                        log["sent"] += 1
            count = log["count"]
            done = log["sent"] / count
            conflict = log["nc_conflict"] is not None
            add_to_dict(logs, data_len, mode, done, count, conflict)
            writer.writerow((data_len, mode, done, count, conflict))
            printProgressBar(progress, listdir_len, prefix=prefix)
    return logs


def read_csv():
    logs = {}
    with open(CSV_NAME) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            mode_tuple = row["mode"]
            m = re.match(r"\('(\w+)',\s*((None)|(\((\d+,?\s*)+\)))",
                         row["mode"])
            if m.group(2) == "None":
                mode_tuple = (m.group(1), None)
            else:
                config = tuple(
                    int(e) for e in re.split(r",\s*", m.group(2).strip("()"))
                )
                mode_tuple = (m.group(1), config)
                if config[0] not in WIN_SIZES:
                    continue
                if config[1] not in IFGS:
                    continue
                if config[4] not in DG_RETRIES:
                    continue
            add_to_dict(logs, int(row["data_len"]), mode_tuple,
                        float(row["done"]), int(row["count"]),
                        row["nc_conflict"] == "True")
    return logs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--rebuild-csv", action="store_true")
    args = parser.parse_args()
    if not os.path.exists(CSV_NAME) or args.rebuild_csv:
        logs = build_csv()
    else:
        logs = read_csv()
    data_lens = sorted(logs.keys())
    modes = set()
    for data_len in data_lens:
        modes |= set(logs[data_len].keys())
    modes = sorted(modes)
    array = []
    runs = []
    total = len(data_lens) * len(modes)
    progress = 0
    prefix = "{:>20s}".format("Tallying results")
    printProgressBar(progress, total, prefix=prefix)
    for mode in modes:
        array.append([])
        runs.append([])
        for data_len in data_lens:
            if data_len in logs and mode in logs[data_len]:
                array[-1].append(100 * np.mean([l[0] / NODES
                                          for l in logs[data_len][mode]]))
                runs[-1].append(100 * min([1.0, len(logs[data_len][mode]) / EXP_RUNS]))
            else:
                array[-1].append(0.0)
                runs[-1].append(0.0)
            progress += 1
            printProgressBar(progress, total, prefix=prefix)
    array = np.array(array)
    runs = np.array(runs)
    plt.rcParams.update({"font.size": 6, "figure.figsize": (8, 6)})
    ax = plt.gca()
    im = ax.imshow(array, cmap="cool_r")
    cbar = ax.figure.colorbar(im, ax=ax, orientation="horizontal",
                              aspect=60, pad=0.00)
    cbar.ax.set_xlabel("Actual packets sent vs expected (=exp) [%] (=comp)",
                       fontsize=8)
    im = ax.imshow(runs, alpha=0.5, cmap="Greys_r")
    cbar = ax.figure.colorbar(im, ax=ax, orientation="horizontal",
                              aspect=60, pad=.16)
    cbar.ax.set_xlabel("Runs completed / {} Runs [%]".format(EXP_RUNS),
                       fontsize=8)
    plt.xticks(range(len(data_lens)), data_lens,
               rotation=90, ha="center", va="top")
    plt.xlabel("UDP payload length [bytes]", fontsize=8)
    plt.yticks(range(len(modes)), [str(m[0].upper()) if m[1] is None else
                                   "{} {}".format(m[0].upper(), m[1])
                                   for m in modes])
    plt.ylabel("Mode", fontsize=8)
    progress = 0
    prefix = "{:>20s}".format("Marking squares")
    printProgressBar(progress, total, prefix=prefix)
    for (i, mode) in enumerate(modes):
        for j, data_len in enumerate(data_lens):
            if any(l[2] for l in logs[data_len].get(mode, [[False] * 3])):
                ax.text(j, i, "x",
                        ha="center", va="center", color="red", fontsize=10)
            if any(l[1] for l in logs[data_len].get(mode, [[False] * 2])) and \
               min(l[1] for l in logs[data_len][mode]) != \
               max(l[1] for l in logs[data_len][mode]):

                ax.text(j, i, "o",
                        ha="center", va="center", color="orange", fontsize=10)
            ax.text(j, i, "{:d}\n{:d}\n{:.0f}".format(
                        int(array[i, j]),
                        len(logs[data_len].get(mode, [])),
                        max(l[1] for l in logs[data_len].get(mode, [[float("-inf")] * 2]))
                    ), ha="center", va="center", fontsize=FONT_SIZE_SQUARE,
                    color="black" if (array[i, j] == 100)
                          else "lightcoral" if (array[i, j] > 0) else "magenta"
            )
            progress += 1
            printProgressBar(progress, total, prefix=prefix)
    legend_elems = [mlines.Line2D([], [], color="white", marker="o",
                    markersize=5, linewidth=0, markeredgewidth=1,
                    markeredgecolor="orange", markerfacecolor="#ffffff00",
                    label="Packets expected inconsistency"),
                    mlines.Line2D([], [], color="white", marker="x",
                    markersize=5, linewidth=0, markeredgewidth=1,
                    markeredgecolor="red", markerfacecolor="#ffffff00",
                    label="Contains Nextcloud conflict")]
    plt.legend(handles=legend_elems, ncol=2,
               bbox_to_anchor=(0., 1.02, 1., .102), loc='lower left')
    plt.tight_layout()
    SQUARE_KEY_POS = (-13, len(modes) + 7)
    SQUARE_KEY_SIZE = 8
    ax.add_patch(patches.Rectangle(SQUARE_KEY_POS, SQUARE_KEY_SIZE,
                                   SQUARE_KEY_SIZE, clip_on=False,
                                   facecolor="cyan"))
    ax.add_patch(patches.Rectangle(SQUARE_KEY_POS, SQUARE_KEY_SIZE,
                                   SQUARE_KEY_SIZE, clip_on=False, alpha=.5,
                                   facecolor="white"))
    ax.text(SQUARE_KEY_POS[0] + (SQUARE_KEY_SIZE / 2),
            SQUARE_KEY_POS[1] + (SQUARE_KEY_SIZE / 2),
            "comp\nruns\nmax(exp)", ha="center", va="center",
            fontsize=FONT_SIZE_SQUARE * SQUARE_KEY_SIZE)
    plt.savefig(os.path.join(DATA_PATH, "done.svg"), figsize=(60, 40),
                bbox_inches="tight")
    plt.show()
