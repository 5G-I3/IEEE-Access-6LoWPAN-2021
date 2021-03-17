# Copyright (C) 2021 Freie Universität Berlin
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

import re
import logging
import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from parse_results import DATA_PATH

CSVNAME_PATTERN = r'sfr-cc-{mode}-({dg_retries}-)?({congure_impl}-)' \
                  r'?({ecn_frac}-)?(?P<count>\d+)x{data_len:d}B{delay}ms-' \
                  r'(?P<exp_id>\d+)-(?P<timestamp>\d+)' \
                  r'(\.(?P<node>m3-\d+))?\.(stats|times|cong)\.csv'
DELAY = 500
RUNS = 10

DATA_LENS = tuple((range(112, 1232, 96)))
FRAGS = {k: ((k - 16) / 96) + 1 for k in DATA_LENS}
MODES = [
    'sfr',
]
MODES_READABLE = {
    'hwr': 'HWR',
    'sfr': 'SFR'
}
DG_RETRIES = [0]
CONGURE_IMPLS = [
    'congure_sfr',
    'congure_reno',
    'congure_abe',
    'congure_quic',
]
CONGURE_IMPLS_READABLE = {
    'congure_sfr': 'SFR App. C',
    'congure_reno': 'TCP Reno',
    'congure_abe': 'TCP ABE',
    'congure_quic': 'QUIC',
}
ECN_FRACS = ['1_2']
ECN_FRACS_READABLE = {
    '1_2': r'50.0\%',
    '3_4': r'75.0\%',
    '7_8': r'87.5\%',
}
MODE_STYLES = {
    'hwr': {},
    'sfr': {},
}
CONGURE_IMPL_STYLES = {
    None: {},
    'congure_sfr': {'color': 'C0'},
    'congure_reno': {'color': 'C1'},
    'congure_abe': {'color': 'C2'},
    'congure_quic': {'color': 'C3'},
}
ECN_FRAC_STYLES = {
    None: {},
    '1_2': {'hatch': r'\\\\'},
    '3_4': {},
    '7_8': {'hatch': r'oooo'},
}
OFFSET = {
    ('hwr', None, None): 0,
    ('sfr', 'congure_sfr', '1_2'): -0.33,
    ('sfr', 'congure_sfr', '3_4'): -0.33,
    ('sfr', 'congure_sfr', '7_8'): -0.33,
    ('sfr', 'congure_reno', '1_2'): -0.11,
    ('sfr', 'congure_reno', '3_4'): -0.11,
    ('sfr', 'congure_reno', '7_8'): -0.11,
    ('sfr', 'congure_abe', '1_2'): 0.11,
    ('sfr', 'congure_abe', '3_4'): 0.11,
    ('sfr', 'congure_abe', '7_8'): 0.11,
    ('sfr', 'congure_quic', '1_2'): 0.33,
    ('sfr', 'congure_quic', '3_4'): 0.33,
    ('sfr', 'congure_quic', '7_8'): 0.33,
}
WIDTH = 0.22


def set_style():
    plt.style.use('miri_ieee.mplstyle')
    matplotlib.rcParams["pgf.preamble"] = "\n".join([
        r'\usepackage{units}',          # load additional packages
        r'\usepackage{metalogo}',
        r'\usepackage{libertine}',
        r'\usepackage{fontspec}',
        r'\usepackage{unicode-math}',
        r'\setmainfont{Linux Libertine O}',
        r'\setmonofont{Linux Libertine Mono O}',
        r'\setmathfont{Linux Libertine O}'
    ])


def get_files(mode, dg_retries, congure_impl, ecn_frac, data_len):
    # pylint: disable=too-many-arguments
    exp_dict = {'delay': DELAY, 'mode': mode, 'dg_retries': dg_retries,
                'data_len': data_len, 'congure_impl': congure_impl or '',
                'ecn_frac': ecn_frac or ''}
    pattern = CSVNAME_PATTERN.format(**exp_dict)
    filenames = filter(lambda x: x[0] is not None,
                       map(lambda f: (re.match(pattern, f),
                                      os.path.join(DATA_PATH, f)),
                           os.listdir(DATA_PATH)))
    filenames = sorted(filenames,
                       key=lambda x: int(x[0].group("timestamp")))
    res = {
        'stats': [f for f in filenames if f[1].endswith('stats.csv')],
        'times': [f for f in filenames if f[1].endswith('times.csv')],
        'cong': {}
    }
    for f in filenames:
        if not f[1].endswith('cong.csv'):
            continue
        node = f[0]['node']
        assert node
        if node not in res['cong']:
            res['cong'][node] = [f]
        else:
            res['cong'][node].append(f)
    if len(res['stats']) < RUNS:
        logging.warning(
            '%s-%s-%s-%s-%sB%sms only has %s of %s expected runs',
            exp_dict['mode'], exp_dict['dg_retries'], exp_dict['congure_impl'],
            exp_dict['ecn_frac'], exp_dict['data_len'], exp_dict['delay'],
            len(res['stats']), RUNS
        )
    if len(res['stats']) > RUNS:
        logging.info(
            '%s-%s-%s-%s-%sB%sms has %s of %s expected runs',
            exp_dict['mode'], exp_dict['dg_retries'], exp_dict['congure_impl'],
            exp_dict['ecn_frac'], exp_dict['data_len'], exp_dict['delay'],
            len(res['stats']), RUNS
        )
    return res


def reject_outliers(data, m=2):
    d = np.abs(data - np.median(data))
    mdev = np.median(d)
    s = d / mdev if mdev else 0.
    data = np.array(data)
    return data[s < m]
