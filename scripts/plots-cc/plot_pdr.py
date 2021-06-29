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

import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np

from matplotlib.patches import Patch

import plot_common as pc
from parse_results import DATA_PATH


def process_data(mode, dg_retries, congure_impl, ecn_frac, data_len):
    files = pc.get_files(mode, dg_retries, congure_impl, ecn_frac, data_len)
    res = []
    for i, (match, filename) in enumerate(files['stats'][-pc.RUNS:]):
        filename = os.path.join(DATA_PATH, filename)
        sends = 0
        receives = 0
        with open(files['times'][i][1]) as timesfile:
            reader = csv.DictReader(timesfile, delimiter=";")
            for row in reader:
                sends += 1
                if row["recv_time"]:
                    receives += 1
                if (sends > 0):
                    res.append(100 * receives / sends)
    return pc.FRAGS[data_len], pc.reject_outliers(res)


def plot_pdrs(means, stds):
    frags = sorted(pc.FRAGS.values())
    idx = np.array(frags)
    for dg_retries in pc.DG_RETRIES:
        for ecn_frac in pc.ECN_FRACS:
            plt.clf()
            fig, ax = plt.subplots()
            plt.xlabel(r"6LoWPAN fragments [\#]")
            plt.xlim(frags[0] - 0.5, frags[-1] + 0.5)
            plt.xticks(frags)
            plt.ylabel(r"PDR [\%]")
            plt.ylim((0, 2.5))
            plt.yticks(np.arange(0, 3.0, 0.5))
            for mode in pc.MODES:
                if mode == 'hwr':
                    dg_retries = None
                    ecn_frac = None
                for congure_impl in pc.CONGURE_IMPLS:
                    if mode == 'hwr':
                        congure_impl = None
                    means_mask = np.isfinite(means[mode, dg_retries,
                                                   congure_impl, ecn_frac])
                    styles = dict(pc.MODE_STYLES[mode])
                    styles.update(pc.CONGURE_IMPL_STYLES[congure_impl])
                    # styles.update(pc.ECN_FRAC_STYLES[ecn_frac])
                    plt.bar(idx[means_mask] +
                            pc.OFFSET[mode, congure_impl, ecn_frac],
                            means[mode, dg_retries, congure_impl,
                                  ecn_frac][means_mask],
                            yerr=stds[mode, dg_retries, congure_impl,
                                      ecn_frac][means_mask],
                            width=pc.WIDTH,
                            label=pc.CONGURE_IMPLS_READABLE[congure_impl],
                            **styles)
                    if mode == 'hwr':
                        break
                if mode == 'hwr':
                    break
            plt.savefig(os.path.join(DATA_PATH, f'pdr_{dg_retries}_{ecn_frac}.pdf'),
                        bbox_inches="tight")
            plt.savefig(os.path.join(DATA_PATH, f'pdr_{dg_retries}_{ecn_frac}.pgf'),
                        bbox_inches="tight")
        if mode == 'hwr':
            break


def main():
    pc.set_style()
    mpl.rcParams['figure.figsize'] = (mpl.rcParams['figure.figsize'][0],
                                      mpl.rcParams['figure.figsize'][1] * .6)
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbosity', default='INFO')
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.verbosity))
    means = {}
    stds = {}

    for mode in pc.MODES:
        for dg_retries in pc.DG_RETRIES:
            if mode == 'hwr':
                dg_retries = None
            for congure_impl in pc.CONGURE_IMPLS:
                if mode == 'hwr':
                    congure_impl = None
                for ecn_frac in pc.ECN_FRACS:
                    if mode == 'hwr':
                        ecn_frac = None
                    pdrs = []
                    for data_len in pc.DATA_LENS:
                        pdrs.append(
                            process_data(mode, dg_retries, congure_impl,
                                         ecn_frac, data_len)
                        )
                    pdrs = dict(pdrs)
                    means[mode, dg_retries, congure_impl, ecn_frac] = \
                        np.array([np.mean(pdrs[f] if f in pdrs else np.nan)
                                  for f in pc.FRAGS.values()]) \
                        .astype(np.double)
                    stds[mode, dg_retries, congure_impl, ecn_frac] = \
                        np.array([np.std(pdrs[f] if f in pdrs else np.nan)
                                  for f in pc.FRAGS.values()]) \
                        .astype(np.double)
                    if mode == 'hwr':
                        break
                if mode == 'hwr':
                    break
            if mode == 'hwr':
                break

    plot_pdrs(means, stds)


if __name__ == '__main__':
    main()
