#! /usr/bin/env python3

# Copyright (C) 2021 Freie Universität Berlin
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

# pylint: disable=missing-module-docstring,missing-function-docstring
# pylint: disable=missing-class-docstring

import argparse
import csv
import logging
import os
import subprocess
import sys
import time

import coloredlogs
import libtmux
import riotctrl.ctrl

from iotlab_controller.constants import IOTLAB_DOMAIN
from iotlab_controller.experiment.descs import tmux_runner


__author__ = "Martine S. Lenders"
__copyright__ = "Copyright 2021 Freie Universität Berlin"
__license__ = "LGPL v2.1"
__email__ = "m.lenders@fu-berlin.de"

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
SINK_PORT = 61616
PREFIX = '2001:db8:1::'
NODES_CSV_NAME = 'nodes.csv'

sys.path.append(os.path.join(
    SCRIPT_PATH, '..', '..', 'RIOT', 'dist', 'pythonlibs')
)

# pylint: disable=wrong-import-position
import riotctrl_shell.netif     # noqa: E402

logger = logging.getLogger(__name__)


class Dispatcher(tmux_runner.TmuxExperimentDispatcher):
    # pylint: disable=unused-argument,no-self-use
    def pre_experiment(self, runner, ctx, *args, **kwargs):
        runner.nodes.save_edgelist(os.path.join(runner.results_dir,
                                                f'{runner.nodes}.edgelist.gz'))
        nodes_filename = os.path.join(runner.results_dir, NODES_CSV_NAME)
        nodes = self.load_nodes_metadata(nodes_filename)
        for i, node in enumerate(runner.nodes.network.nodes()):
            if node not in nodes:
                nodes[node] = self.parse_node_metadata(runner, i, node)
            if node == runner.nodes.sink:
                nodes['sink'] = {
                    'iface': nodes[node]['iface'],
                    'addr': nodes[node]['addr'].replace('fe80::', PREFIX),
                    'l2pdu': nodes[node]['l2pdu'],
                }
        self.store_nodes_metadata(nodes_filename, nodes)
        return {'nodes': nodes}

    def post_experiment(self, runner, ctx, *args, **kwargs):
        if not runner.runs:     # no more runs for the experiment
            runner.experiment.stop()

    def pre_run(self, runner, run, ctx, *args, **kwargs):
        exp = runner.experiment
        self.set_ssh_agent_env(exp.tmux_session)
        run_log = os.path.join(
            runner.results_dir,
            f'{exp.tmux_session.session.name}.'
            f'{exp.tmux_session.window.name}.log'
        )
        exp.cmd(f"ps -o comm= -p $PPID | grep -q '^script$' || "
                f"script -fa '{run_log}'")
        sniffer, pcap_file_name = self.start_sniffer(runner, ctx)
        logname = ctx['logname']
        exp.cmd(f'cd {SCRIPT_PATH}', wait_after=.2)
        with exp.serial_aggregator(exp.nodes.site, logname=logname):
            self.construct_routes(runner, run, ctx['nodes'])
            exp.cmd('nib route', wait_after=.2)
            exp.cmd('ifconfig', wait_after=.2)
            exp.cmd(f'{exp.nodes.sink};udp server start {SINK_PORT}',
                    wait_after=.2)
        return {'sink_port': SINK_PORT, 'sniffer': sniffer, 'logname': logname,
                'pcap_file_name': pcap_file_name}

    def post_run(self, runner, run, ctx, *args, **kwargs):
        exp = runner.experiment
        logname = ctx['logname']
        with exp.serial_aggregator(exp.nodes.site, logname=logname):
            exp.cmd('ifconfig', wait_after=3)
            if run.env['MODE'] == 'e2e':
                exp.cmd('ip6_frag', wait_after=60)
            else:
                exp.cmd('6lo_frag', wait_after=60)
            exp.cmd('pktbuf', wait_after=3)
        for _ in range(3):
            ctx['sniffer'].send_keys('C-c', suppress_history=False)
        ctx['sniffer'].send_keys(
            f'ssh lenders@{runner.nodes.site}.{IOTLAB_DOMAIN} '
            f'pkill -f sniffer_aggregator', enter=True, suppress_history=False
        )
        subprocess.run(['gzip', '-v', '-9', ctx['pcap_file_name']],
                       check=False)
        # set TMUX session to 0 to reinitialize it in case `run` window closes
        exp.tmux_session = None

    @staticmethod
    def load_nodes_metadata(nodes_filename):
        res = {}
        if not os.path.exists(nodes_filename):
            return res
        with open(nodes_filename) as l2addr_file:
            l2addr_csv = csv.DictReader(l2addr_file)
            for row in l2addr_csv:
                try:
                    node_name = row['name']
                    res[node_name] = {'addr': row['addr'],
                                      'iface': row['iface'],
                                      'l2pdu': int(row['l2pdu'])}
                except KeyError:
                    break
        return res

    @staticmethod
    def store_nodes_metadata(nodes_filename, nodes_metadata):
        with open(nodes_filename, "w") as nodes_file:
            nodes_csv = csv.DictWriter(nodes_file,
                                       ['name', 'iface', 'addr', 'l2pdu'])
            nodes_csv.writeheader()
            for node in nodes_metadata:
                row = dict(nodes_metadata[node])
                row['name'] = node
                nodes_csv.writerow(row)

    @staticmethod
    def parse_node_metadata(runner, i, node):
        firmware = runner.experiment.firmwares[i]
        ctrl_env = {
            'BOARD': firmware.board,
            'IOTLAB_NODE': runner.nodes[node].uri,
        }
        ctrl = riotctrl.ctrl.RIOTCtrl(firmware.application_path,
                                      ctrl_env)
        ctrl.TERM_STARTED_DELAY = .1
        shell = riotctrl_shell.netif.Ifconfig(ctrl)
        with ctrl.run_term(reset=False):
            ctrl.term.logfile = sys.stdout
            netifs = riotctrl_shell.netif.IfconfigListParser().parse(
                shell.ifconfig_list()
            )
        ifname = list(netifs)[0]
        return {
            'iface': ifname,
            'addr': [a['addr'] for a in netifs[ifname]['ipv6_addrs']
                     if a['scope'] == 'link'][0],
            'l2pdu': netifs[ifname]['l2_pdu'],
        }

    @staticmethod
    def set_ssh_agent_env(tmux_pane):
        if ("SSH_AUTH_SOCK" in os.environ) and ("SSH_AGENT_PID" in os.environ):
            tmux_pane.send_keys("export SSH_AUTH_SOCK='{}'"
                                .format(os.environ["SSH_AUTH_SOCK"]),
                                enter=True, suppress_history=False)
            tmux_pane.send_keys("export SSH_AGENT_PID='{}'"
                                .format(os.environ["SSH_AGENT_PID"]),
                                enter=True, suppress_history=False)

    def start_sniffer(self, runner, ctx):
        sniffer = runner.experiment.tmux_session.session
        try:
            window = sniffer.find_where({'window_name': 'sniffer'})
        except libtmux.exc.LibTmuxException:
            window = sniffer.new_window('sniffer', attach=False)
        if window is None:
            window = sniffer.new_window('sniffer', attach=False)
        sniffer = window.select_pane(0)
        self.set_ssh_agent_env(sniffer)
        time.sleep(.2)
        for _ in range(3):
            sniffer.send_keys("C-c", suppress_history=False)
        sniffer.send_keys(f'cd {SCRIPT_PATH}', enter=True,
                          suppress_history=False)
        pcap_file_name = ctx['logname'].replace('.log', '.pcap')
        sniffer.send_keys(f'ssh lenders@{runner.nodes.site}.{IOTLAB_DOMAIN} '
                          f'sniffer_aggregator -i {runner.exp_id} -o - '
                          f'> {pcap_file_name}', enter=True,
                          suppress_history=False)
        return sniffer, pcap_file_name

    @staticmethod
    def _set_e2e_mtu(exp, run, node, iface, l2pdu):
        if run.env['MODE'] == 'e2e':
            mtu = l2pdu
            # UDP header compression: length field (2 byte) elided but 1 byte
            # for NHC dispatch => 1 bytes less than normal UDP header
            comp = 1
            # No compression advantage for fragmentation header
            # IPv6 header compression: version, traffic class, flowlabel elided
            # (4 bytes); next header elided due to NHC (1 byte); no CID as
            # context is 0; 64-bit prefix elided by stateful compression
            # (16 byte) >= 21 bytes less than normal IPv6 header
            comp += 21
            mtu += comp
            exp.cmd(f'{node};ifconfig {iface} set mtu {mtu}',
                    wait_after=.1)

    def construct_routes(self, runner, run, nodes_metadata):
        """
        Constructs network using depth-first search
        """
        stack = []
        stack.append(runner.nodes.sink)
        visited = set()
        exp = runner.experiment
        while stack:
            node = stack.pop()
            if node not in visited:
                iface = nodes_metadata[node]['iface']
                ll_addr = nodes_metadata[node]['addr']
                glb_addr = ll_addr.replace('fe80::', PREFIX)
                # add global unicast address to interface
                exp.cmd(f'{node};ifconfig {iface} add {glb_addr}',
                        wait_after=.1)
                self._set_e2e_mtu(exp, run, node, iface,
                                  nodes_metadata[node]['l2pdu'])
                # set compression context for global unicast address prefix
                ltime = 0xffff
                exp.cmd(f'{node};6ctx add 0 {PREFIX}/64 {ltime}',
                        wait_after=.1)
                for neigh in exp.nodes.neighbors(node):
                    # setting default route from neighbors to node
                    if neigh not in visited:
                        neigh_iface = nodes_metadata[neigh]['iface']
                        exp.cmd(f'{neigh};nib route add {neigh_iface} '
                                f'default {ll_addr}', wait_after=.3)
                    stack.append(neigh)
                visited.add(node)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("descs", nargs="?",
                        default=os.path.join(SCRIPT_PATH, "descs.yaml"),
                        help="Experiment descriptions file")
    parser.add_argument('-v', '--verbosity', default='INFO',
                        help='Verbosity as log level')
    args = parser.parse_args()
    coloredlogs.install(level=getattr(logging, args.verbosity),
                        milliseconds=True)
    logger.debug('Running %s', args.descs)
    dispatcher = Dispatcher(args.descs)
    dispatcher.load_experiment_descriptions()


if __name__ == '__main__':
    main()
