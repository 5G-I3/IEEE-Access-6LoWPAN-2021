#! /usr/bin/env python3

# Copyright (C) 2021 Freie Universität Berlin
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

# pylint: disable=missing-module-docstring,missing-function-docstring

import argparse
import gzip
import os

import yaml


SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))

UDP_COUNT = 1200
RUNS = 10
DATA_LENS = range(112, 1232, 96)
DELAY_MS = 500
MODES = ['sfr']
CONGURE_IMPLS = ['congure_sfr', 'congure_reno', 'congure_quic', 'congure_abe']
ECN_FRACS = [(1, 2)]
DG_RETRIES = [0]

NODES = {
    'network': {
        'site': 'grenoble',
        'sink': 'm3-273',
        'edgelist': [
            ['m3-273', 'm3-281'],
            ['m3-281', 'm3-289'],
            ['m3-281', 'm3-288'],
            ['m3-289', 'm3-72'],
            ['m3-72', 'm3-76'],
            ['m3-288', 'm3-3'],
            ['m3-3', 'm3-5'],
        ]
    }
}
GLOBALS = {
    'results_dir': '../../results',
    'env': {
        'DEFAULT_CHANNEL': 16,
        'UDP_COUNT': UDP_COUNT,
    },
    'name': 'sfr-cc',
    'profiles': ['sniffer16'],
    'sink_firmware': {
        'path': '../../apps/sink',
        'board': 'iotlab-m3',
        'name': '6lo-ff-sink',
    },
    'firmwares': [{
        'path': '../../apps/source',
        'board': 'iotlab-m3',
        'name': '6lo-ff-source',
    }],
    'run_name': '{exp.name}-{run.env[MODE]}-{run.env[SFR_DATAGRAM_RETRIES]}-'
                '{run.env[CONGURE_IMPL]}-{run.env[SFR_ECN_NUM]}_'
                '{run.env[SFR_ECN_DEN]}-'
                '%dx{run_args[data_len]}B{run_args[delay_ms]}ms-'
                '{exp.exp_id}-{time}' % UDP_COUNT,
    'nodes': NODES,
    'tmux': {
        'target': '6lo-comp:run.0',
        'cmds': [
            'm3,{non_sink_nodes};'
            'udp send '
            '[{{ctx[nodes][sink][addr]}}]:{{ctx[sink_port]}} '
            '{{run_args[data_len]}} {{run_args[delay_ms]}}',
        ]
    }
}
HWR_NAME = '{exp.name}-{run.env[MODE]}-' \
           '%dx{run_args[data_len]}B{run_args[delay_ms]}ms-' \
           '{exp.exp_id}-{time}' % UDP_COUNT


def _load_edgelist(edgelist_filename):
    edgelist = []
    if edgelist_filename.endswith('.gz'):
        open_function = gzip.open
    else:
        open_function = open
    with open_function(edgelist_filename) as edgelist_file:
        for line in edgelist_file:
            edge = line.decode().split()
            edgelist.append([edge[0], edge[1]])
    return edgelist


def set_sources_in_cmd(descs):
    if 'edgelist' in NODES['network'] or \
       'edgelist_file' in NODES['network']:
        if 'edgelist_file' in NODES['network']:
            edgelist = _load_edgelist(NODES['network']['edgelist_file'])
        else:
            edgelist = NODES['network']['edgelist']
        sink = NODES['network']['sink']
        for i, cmd in enumerate(descs['globals']['tmux'].get('cmds', [])):
            descs['globals']['tmux']['cmds'][i] = cmd \
                .format(non_sink_nodes='+'.join(
                    sorted(
                        set(
                            node.split('-')[1] for edge in edgelist
                            for node in edge
                            if node != sink and
                            [node, sink] not in edgelist and
                            [sink, node] not in edgelist
                        ),
                        key=int
                    )
                ))


def main():                 # pylint: disable=missing-function-docstring
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--rebuild-first', action='store_true',
                        help="Set rebuild=True on first run, regardless of "
                             "firmware or environment")
    parser.add_argument('-i', '--exp-id', type=int, default=None,
                        help="Experiment ID of an already running experiment")
    args = parser.parse_args()

    descs = {'unscheduled': [{'runs': []}], 'globals': GLOBALS}
    descs['globals']['run_wait'] = (UDP_COUNT * DELAY_MS * 1.6) / 1000
    set_sources_in_cmd(descs)
    duration = 0
    for _ in range(RUNS):           # pylint: disable=too-many-nested-blocks
        for mode in MODES:
            for h, dg_retries in enumerate(DG_RETRIES):
                if mode == 'hwr' and h > 0:
                    break
                for i, ecn_frac in enumerate(ECN_FRACS):
                    if mode == 'hwr' and i > 0:
                        break
                    for j, congure_impl in enumerate(CONGURE_IMPLS):
                        if mode == 'hwr' and j > 0:
                            break
                        ecn_env = {'SFR_ECN_NUM': ecn_frac[0],
                                   'SFR_ECN_DEN': ecn_frac[1]}
                        for data_len in DATA_LENS:
                            run = {
                                'env': {'MODE': mode},
                                'args': {
                                    'delay_ms': DELAY_MS,
                                    'data_len': data_len,
                                },
                            }
                            if mode == 'hwr':
                                run['name'] = HWR_NAME
                            elif mode == 'sfr':
                                run['env'].update(ecn_env)
                                run['env']['CONGURE_IMPL'] = congure_impl
                                run['env']['SFR_DATAGRAM_RETRIES'] = dg_retries
                            descs['unscheduled'][0]['runs'].append(run)
                            duration += (descs['globals']['run_wait'] + 120)
    # add first run env to globals so we only build firmware once on start
    # (rebuild is handled with `--rebuild-first` if desired)
    descs['globals']['env'].update(descs['unscheduled'][0]['runs'][0]['env'])
    descs['globals']['duration'] = int((duration / 60) + 20)
    if args.rebuild_first or args.exp_id is not None:
        descs['unscheduled'][0]['runs'][0]['rebuild'] = True
    if args.exp_id is not None:
        descs[args.exp_id] = descs['unscheduled'][0]
        del descs['unscheduled']
    with open(os.path.join(SCRIPT_PATH, 'descs.yaml'), 'w') as output:
        output.write(yaml.dump(descs))


if __name__ == "__main__":
    main()
