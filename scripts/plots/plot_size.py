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
import logging
import os

import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np

from matplotlib.patches import Patch

import plot_common as pc
from parse_results import DATA_PATH


SIZES = {
    'SFR': {
        'CongURE': {
            'ROM': 4022 + 8,    # text: 4022 + data: 8
            'RAM': 2108 + 8,    # data: 8 + bss: 2108
        },
        'SFR App. C': {
            'ROM': 3812 + 8,    # text: 3812 + data: 8
            'RAM': 2108 + 8,    # data: 8 + bss: 2108
        },
        'TCP Reno': {
            'ROM': 4162 + 8,    # text: 4162 + data: 8
            'RAM': 2108 + 8,    # data: 8 + bss: 2108
        },
        'TCP ABE': {
            'ROM': 4174 + 8,    # text: 4174 + data: 8
            'RAM': 2108 + 8,    # data: 8 + bss: 2108
        },
        'QUIC': {
            'ROM': 4414 + 8,    # text: 4174 + data: 8
            'RAM': 2108 + 8,    # data: 8 + bss: 2108
        },
    },
    'FB': {
        'CongURE': {
            'ROM': 104,         # text: 104
            'RAM': 176,         # bss: 176
        },
        'SFR App. C': {
            'ROM': 104,         # text: 104
            'RAM': 178,         # bss: 178
        },
        'TCP Reno': {
            'ROM': 104,         # text: 104
            'RAM': 226,         # bss: 226
        },
        'TCP ABE': {
            'ROM': 104,         # text: 104
            'RAM': 226,         # bss: 226
        },
        'QUIC': {
            'ROM': 104,         # text: 104
            'RAM': 274,         # bss: 274
        },
    },
    'w/ CongURE': {
        'SFR App. C': {
            'ROM': 124,
            'RAM': 48,
        },
        'TCP Reno': {
            'ROM': 482 + 130,   # congure_reno_methods: 482 + cognure_reno: 130
            'RAM': 112,
        },
        'TCP ABE': {
            'ROM': 466 + 80 + 90,   # congure_reno_methods: 466 + cognure_abe: 80 + congure_reno: 90
            'RAM': 112,
        },
        'QUIC': {
            'ROM': 640,
            'RAM': 160,
        },
    },
}
WIDTH = 0.4
COLORS = {
    'w/ CongURE': 'C0',
    'unrolled': 'C1',
}
HATCH = {
    'SFR': '//',
    'FB': '||',
    'CongURE': None,
}


def plot_sizes():
    x = np.array(range(len(pc.CONGURE_IMPLS)))
    congure_sizes = {}
    sfr_sizes = {}
    fb_sizes = {}
    for group in ['w/ CongURE', 'unrolled']:
        congure_sizes[group] = {'ROM': [0 for _ in x], 'RAM': [0 for _ in x]}
        sfr_sizes[group] = {'ROM': [0 for _ in x], 'RAM': [0 for _ in x]}
        fb_sizes[group] = {'ROM': [0 for _ in x], 'RAM': [0 for _ in x]}

        for c, congure_impl in enumerate(pc.CONGURE_IMPLS):
            key = pc.CONGURE_IMPLS_READABLE[congure_impl]
            if group == 'w/ CongURE':
                subkey = 'CongURE'
                for mem in ['ROM', 'RAM']:
                    congure_sizes[group][mem][c] = SIZES[group][key][mem]
            elif group == 'unrolled':
                subkey = key
            else:
                logging.error('Unexpected group %s', group)
                return
            for mem in ['ROM', 'RAM']:
                sfr_sizes[group][mem][c] = SIZES['SFR'][subkey][mem]
                fb_sizes[group][mem][c] = SIZES['FB'][subkey][mem]
    for mem in ['ROM', 'RAM']:
        plt.clf()
        fig, ax = plt.subplots()
        for x_offset, group in zip([-(WIDTH / 2), (WIDTH / 2)],
                                   ['w/ CongURE', 'unrolled']):
            ax.bar(x + x_offset, sfr_sizes[group][mem], WIDTH,
                   color=COLORS[group], hatch=HATCH['SFR'])
            bottom = np.array(sfr_sizes[group][mem])
            ax.bar(x + x_offset, fb_sizes[group][mem], WIDTH,
                   bottom=bottom, color=COLORS[group],
                   hatch=HATCH['FB'])
            bottom += np.array(fb_sizes[group][mem])
            ax.bar(x + x_offset, congure_sizes[group][mem], WIDTH,
                   bottom=bottom, color=COLORS[group],
                   hatch=HATCH['CongURE'])
        ax.set_xticks(x)
        ax.set_xticklabels(
            [pc.CONGURE_IMPLS_READABLE[k] for k in pc.CONGURE_IMPLS]
        )
        ax.set_ylim(0, 5000)
        ax.set_yticks(np.arange(0, 6) * 1e3)
        ax.set_ylabel('Module size [bytes]')
        ax.ticklabel_format(axis='y', style='sci', scilimits=(0, 0))
        if mem == 'RAM':
            group_elements = [Patch(label=group, facecolor=COLORS[group])
                              for group in ['w/ CongURE', 'unrolled']]
            group_legend = plt.legend(handles=group_elements, loc='upper right',
                                      fontsize='small')
            ax.add_artist(group_legend)
            module_elements = [Patch(label=module, facecolor='gray',
                                    hatch=HATCH[module])
                               for module in ['SFR', 'FB', 'CongURE']]
            module_legend = plt.legend(handles=module_elements, loc='upper left',
                                       ncol=2, columnspacing=.5,
                                       fontsize='small')
            ax.add_artist(module_legend)
        plt.savefig(os.path.join(pc.DATA_PATH,
                                 'sizes_{}.pdf'.format(mem.lower())),
                                 bbox_inches='tight')
        plt.savefig(os.path.join(pc.DATA_PATH,
                                 'sizes_{}.pgf'.format(mem.lower())),
                                 bbox_inches='tight')


def main():
    pc.set_style()
    mpl.rcParams['figure.figsize'] = (mpl.rcParams['figure.figsize'][0],
                                      mpl.rcParams['figure.figsize'][1] * .6)
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbosity', default='INFO')
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.verbosity))

    plot_sizes()


if __name__ == '__main__':
    main()
