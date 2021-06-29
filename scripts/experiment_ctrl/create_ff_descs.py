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

UDP_COUNT = 50
RUNS = 3
DATA_LENS = range(16, 1024 + 1, 16)
DELAY_MS = 10000
MODES = ['hwr', 'ff', 'sfr', 'e2e']
SFR_INIT_WIN_SIZES = [1, 5]
SFR_ARQ_TIMEOUTS = [1200, 2400]
SFR_INTER_FRAME_GAPS = [100, 500]

NODES = {
    'network': {
        'site': 'lille',
        'sink': 'm3-57',
        'edgelist_file': os.path.join(
            SCRIPT_PATH,
            '../../results/m3-57x9938589e.edgelist.gz'
        ),
    }
}
GLOBALS = {
    'results_dir': '../../results',
    'env': {
        'DEFAULT_CHANNEL': 16,
        'UDP_COUNT': UDP_COUNT,
    },
    'name': '6lo_comp',
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
    'run_name': '{exp.name}_n{exp.nodes}_c{run.env[DEFAULT_CHANNEL]}__'
                'm{run.env[MODE]}_r{run_args[data_len]}Bx%dx'
                '{run_args[delay_ms]}ms_'
                '{time}' % UDP_COUNT,
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
SFR_NAME = '{exp.name}_n{exp.nodes}_c{run.env[DEFAULT_CHANNEL]}__' \
           'm{run.env[MODE]}-win{run.env[SFR_INIT_WIN_SIZE]}' \
           'ifg{run.env[SFR_INTER_FRAME_GAP]}arq{run.env[SFR_ARQ_TIMEOUT]}' \
           'dg{run.env[SFR_DATAGRAM_RETRIES]}' \
           '_r{run_args[data_len]}Bx%dx{run_args[delay_ms]}ms_' \
           '{time}' % UDP_COUNT


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
            for w, win_size in enumerate(SFR_INIT_WIN_SIZES):
                if mode != 'sfr' and w > 0:
                    break
                for a, arq_timeout in enumerate(SFR_ARQ_TIMEOUTS):
                    if mode != 'sfr' and a > 0:
                        break
                    for i, ifg in enumerate(SFR_INTER_FRAME_GAPS):
                        if mode != 'sfr' and i > 0:
                            break
                        for data_len in DATA_LENS:
                            run = {
                                'env': {'MODE': mode},
                                'args': {
                                    'delay_ms': DELAY_MS,
                                    'data_len': data_len,
                                },
                            }
                            if mode == 'sfr':
                                run['name'] = SFR_NAME
                                run['env']['SFR_DATAGRAM_RETRIES'] = 0
                                run['env']['SFR_INIT_WIN_SIZE'] = win_size
                                run['env']['SFR_ARQ_TIMEOUT'] = arq_timeout
                                run['env']['SFR_INTER_FRAME_GAP'] = ifg
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
