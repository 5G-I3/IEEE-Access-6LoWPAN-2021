#! /usr/bin/env python3

# Copyright (C) 2021 Freie Universität Berlin
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

import argparse
import csv
import logging
import os

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from matplotlib import lines, patches

import plot_common as pc
from parse_results import DATA_PATH

CONGS = ['cs', 'ct', 'cl', 'ca', 'ce', 'cx']
CONGS_HUMAN_READABLE = {
    'cs': 'Fragment sent',
    'ct': 'Fragments timed out',
    'cl': 'Fragments lost',
    'ca': 'Fragment acked',
    'ce': 'ECN',
    'cx': 'Fragment buffer destroyed'
}
CONG_STYLES = {
    'cs': {'color': 'black', 'marker': '|', 'markersize': 5},
    'ct': {'color': 'black', 'marker': '.', 'markersize': 6, 'markeredgewidth': 0},
    'ca': {'color': 'black', 'marker': 'v', 'markersize': 5, 'markeredgewidth': 0},
    'cl': {'color': 'black', 'marker': 'x', 'markersize': 4},
    'ce': {'color': 'black', 'marker': '*', 'markersize': 5, 'markeredgewidth': 0},
    'cx': {'color': 'black', 'marker': 'd', 'markersize': 5, 'markeredgewidth': 0},
}
CWND_STYLE = {
    'color': 'black',
}
IFG_STYLE = {
    'color': 'black',
    'linestyle': 'dashed',
}


def process_data(mode, dg_retries, congure_impl, ecn_frac, data_len, node):
    files = pc.get_files(mode, dg_retries, congure_impl, ecn_frac, data_len)
    if node not in files['cong']:
        raise ValueError(
            f'{node} not available. Available nodes: ' + ', '.join(sorted(
                files["cong"].keys(),
                key=lambda node: int(node.split('-')[1])
            ))
        )
    congs = {}
    ifgs = []
    for i, (match, filename) in enumerate(files['cong'][node][-pc.RUNS:]):
        fullname = os.path.join(DATA_PATH, filename)
        with open(fullname) as congfile:
            reader = csv.DictReader(congfile, delimiter=";")
            for row in reader:
                row['time'] = float(row['time'])
                tag = int(row['tag'])

                row['tag'] = tag
                if row['cwnd'] != '':
                    row['cwnd'] = int(row['cwnd'])
                else:
                    row['cwnd'] = None
                if row['resource_usage'] != '':
                    row['resource_usage'] = float(row['resource_usage'])
                else:
                    row['resource_usage'] = None
                if row['ifg'] != '':
                    row['ifg'] = int(row['ifg']) / 1000
                else:
                    row['ifg'] = None
                timestamp = int(match['timestamp'])
                if (timestamp, tag) in congs:
                    congs[timestamp, tag].append(row)
                else:
                    congs[timestamp, tag] = [row]
                ifgs.append(row)

    for timestamp, tag in list(congs):
        cxs = 0
        last_cx = None
        congs[timestamp, tag].sort(key=lambda c: c['time'])
        for i, c in enumerate(congs[timestamp, tag]):
            if c['type'] == 'cx':
                cxs += 1
                if cxs > 1 and congs[timestamp, tag][last_cx + 1:]:
                    new_tag = tag + (0xff * (cxs - 1))
                    if new_tag in congs:
                        congs[timestamp, new_tag].extend(
                            congs[timestamp, tag][last_cx + 1:]
                        )
                    else:
                        congs[timestamp, new_tag] = \
                            congs[timestamp, tag][last_cx + 1:]
                    congs[timestamp, tag][last_cx + 1:] = []
                last_cx = i
    ifgs.sort(key=lambda i: i['time'])
    return congs, ifgs


def main():
    pc.set_style()
    mpl.rcParams['figure.figsize'] = (3.42, 1.37)
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbosity', default='INFO')
    parser.add_argument('node')
    parser.add_argument('data_len', type=int)
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.verbosity))
    cong_ev_handles = [
        lines.Line2D([], [], label=CONGS_HUMAN_READABLE[typ], alpha=.5,
                     linewidth=0, **CONG_STYLES[typ])
        for typ in CONGS
    ]
    line_handles = [
        lines.Line2D([], [], label="IFG", **IFG_STYLE),
        lines.Line2D([], [], label="CWND", **CWND_STYLE),
    ]

    if args.data_len not in pc.DATA_LENS:
        raise ValueError(f'{args.data_len} not available. Available nodes: ' +
                         ', '.join(str(len) for len in pc.DATA_LENS))
    for dg_retries in [0]:
        for mode in pc.MODES:
            if mode == 'hwr':
                dg_retries = None
            for e, ecn_frac in enumerate(['1_2']):
                if mode == 'hwr':
                    ecn_frac = None
                for c, congure_impl in enumerate(pc.CONGURE_IMPLS,
                                                 start=1 if 'hwr' in pc.MODES
                                                 else 0):
                    if mode == 'hwr':
                        c = 0
                        congure_impl = None
                    congs, ifgs = process_data(mode, dg_retries, congure_impl,
                                               ecn_frac, args.data_len,
                                               args.node)
                    for timestamp, tag in sorted(congs):
                        if len(congs[timestamp, tag]) < 2:
                            continue
                        if not any([c['type'] == 'ca'
                                   for c in congs[timestamp, tag]]) > 0:
                            continue
                        plt.clf()
                        fig, ax1 = plt.subplots(1, 1)
                        ax2 = ax1.twinx()
                        ax3 = ax1.twiny()
                        min_times = min(c['time']
                                        for c in congs[timestamp, tag])
                        max_times = max(c['time']
                                        for c in congs[timestamp, tag])
                        times = [c['time'] - min_times
                                 for c in congs[timestamp, tag]]
                        if mode == 'hwr':
                            mode_str = 'hwr'
                        else:
                            mode_str = f'{mode}_{dg_retries}_{congure_impl}_' \
                                       f'{ecn_frac}'
                        logname = f'cong_{mode_str}.{tag}.{timestamp}.' \
                                  f'{args.node}.{args.data_len}B.pdf'
                        for i, typ in enumerate(CONGS):
                            x = [c['time'] - min_times
                                      for c in congs[timestamp, tag]
                                      if c['type'] == typ]
                            if x and typ == 'cx' and max(x) > 3 and max(x) < 20:
                                print("file://" + os.path.join(DATA_PATH,
                                      logname))
                            if x and typ == 'ce':
                                print("X")
                            if typ == 'cs':
                                ax1.vlines([c['time'] - min_times
                                            for c in congs[timestamp, tag]
                                            if c['type'] == typ],
                                            ymin=16, ymax=22, alpha=.5,
                                            linewidth=.5)
                            else:
                                ax1.plot([c['time'] - min_times
                                          for c in congs[timestamp, tag]
                                          if c['type'] == typ],
                                         [21.5 - ((i - 1) * 1.1)
                                          for c in congs[timestamp, tag]
                                          if c['type'] == typ], alpha=.5,
                                         linewidth=0, **CONG_STYLES[typ])
                        ax1.step(
                            times, [c['cwnd'] for c in congs[timestamp, tag]],
                            where='post', **CWND_STYLE,
                        )
                        ax2.step(
                            times, [i['ifg'] for i in congs[timestamp, tag]],
                            where='post', **IFG_STYLE,
                        )
                        ax1.set_xlabel('Duration [s]')
                        ax1.set_ylabel('CWND [\#frags]')
                        ax2.set_ylabel('IFG [ms]')
                        if (max_times - min_times) < 0.4:
                            ax1.plot([-0.01, 0.41], [16, 16], linewidth=.9,
                                     color='black')
                            ax2.set_xlim(-0.01, 0.41)
                            ax3.set_xlim(-0.01, 0.41)
                            ax2.set_xticks(np.arange(0, 0.5, 0.1))
                            ax3.set_xticks(np.arange(0, 0.5, 0.1))
                        elif (max_times - min_times) < 8.1:
                            ax1.plot([-0.1, 8.1], [16, 16], linewidth=.9,
                                     color='black')
                            ax2.set_xlim(-0.1, 8.1)
                            ax3.set_xlim(-0.1, 8.1)
                            ax2.set_xticks(np.arange(0, 9, 1))
                            ax3.set_xticks(np.arange(0, 9, 1))
                        else:
                            ax2.set_xlim(0, max_times - min_times + .1)
                            ax3.set_xlim(0, max_times - min_times + .1)
                        ax2.set_ylim(0, 600)
                        ax2.set_yticks(range(0, 401, 100))
                        ax3.set_ylim(0, 600)
                        ax1.set_ylim(0, 22)
                        ax1.set_yticks(range(0, 17, 4))
                        fig.legend(loc='upper left', bbox_to_anchor=(0, 1.5),
                                   handles=cong_ev_handles, ncol=3)
                        fig.legend(loc='upper right', bbox_to_anchor=(2.2, 1.5),
                                   handles=line_handles)

                        plt.savefig(os.path.join(DATA_PATH, logname),
                                    bbox_inches="tight")
                        plt.savefig(os.path.join(DATA_PATH,
                                                 logname.replace('.pdf', '.pgf')),
                                    bbox_inches="tight")
                        plt.close()
                    if mode == 'hwr':
                        break
                if mode == 'hwr':
                    break
            if mode == 'hwr':
                break


if __name__ == '__main__':
    main()
