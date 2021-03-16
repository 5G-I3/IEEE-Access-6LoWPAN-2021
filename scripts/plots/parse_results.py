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
import datetime
import ipaddress
import logging
import re
import os
import multiprocessing
import random
import threading

import networkx as nx

__author__ = 'Martine S. Lenders'
__copyright__ = 'Copyright 2021 Freie Universität Berlin'
__license__ = 'LGPL v2.1'
__email__ = 'm.lenders@fu-berlin.de'

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.environ.get('DATA_PATH',
                           os.path.join(SCRIPT_PATH, '..', '..', 'results'))


class LogError(Exception):
    pass


class LogParser:
    # pylint: disable=too-many-instance-attributes
    GLOBAL_PREFIX = ipaddress.IPv6Network('2001:db8:1::/64')
    LINK_LOCAL_PREFIX_STR = 'fe80::'
    LOGNAME_PATTERN = r'sfr-cc-(?P<mode>sfr|hwr)-' \
                      r'((?P<dg_retries>\d+)-' \
                      r'(?P<congure_impl>congure_[^-]+)-' \
                      r'(?P<ecn_frac>\d+_\d+)-)?' \
                      r'(?P<count>\d+)x(?P<data_len>\d+)B(?P<delay>\d+)ms-' \
                      r'(?P<exp_id>\d+)-(?P<timestamp>\d+)'

    LOG_EXP_STARTED_PATTERN = r'Sending (?P<count>\d+) packets'
    LOG_DATA_PATTERN = r'(?P<time>\d+.\d+);(?P<node>m3-\d+);' \
                       r'(> ?)?(?P<dir>(recv|send));(?P<addr>[0-9a-f]{4});' \
                       r'(?P<data_len>\d+);(?P<pkt_id>[0-9a-f]+)$'
    LOG_CONG_PATTERN = r'(?P<time>\d+.\d+);(?P<node>m3-\d+);' \
                       r'(> ?)?(?P<type>[ce].);' \
                       r'((?P<fbuf_usage>\d+);(?P<fbuf_size>\d+);)?' \
                       r'(?P<tag>\d+);' \
                       r'(?P<param1>\d+);' \
                       r'(?P<param2>\d+)'
    LOG_PKTBUF_SIZE_PATTERN = r'(?P<node>m3-\d+);packet buffer: ' \
                              r'first byte: 0x[0-9a-f]+, ' \
                              r'last byte: 0x[0-9a-f]+ ' \
                              r'\(size: (?P<pktbuf_size>\d+)\)'
    LOG_PKTBUF_USAGE_PATTERN = r'(?P<node>m3-\d+);\s+position of last byte ' \
                               r'used: (?P<pktbuf_usage>\d+)'
    LOG_RB_PATTERN = r'(?P<node>m3-\d+);rbuf full: (?P<rb_full>\d+)'
    LOG_VRB_PATTERN = r'(?P<node>m3-\d+);VRB full: (?P<vrb_full>\d+)'
    LOG_FRAGS_COMP_PATTERN = r'(?P<node>m3-\d+);frags complete: ' \
                             r'(?P<frags_comp>\d+)'
    LOG_DGS_COMP_PATTERN = r'(?P<node>m3-\d+);dgs complete: ' \
                           r'(?P<dgs_comp>\d+)'
    _LOG_NAME_C = re.compile(f'{LOGNAME_PATTERN}.log')

    def __init__(self, logname, networks=None, mode=None, dg_retries=None,
                 congure_impl=None, ecn_frac=None, count=None, data_len=None,
                 exp_id=None, timestamp=None, delay=None, data_path=DATA_PATH):
        # pylint: disable=too-many-arguments
        self.data_path = data_path
        self._logname = logname
        self._init_network(networks)
        self.mode = mode
        if congure_impl:
            self.congure_impl = congure_impl
        else:
            self.congure_impl = None
        if ecn_frac:
            ecn_frac = ecn_frac.split('_')
            self.ecn_frac = int(ecn_frac[0]) / int(ecn_frac[1])
        else:
            self.ecn_frac = None
        self.count = int(count) if count is not None else count
        self.data_len = int(data_len) if data_len is not None else data_len
        self.delay = int(delay) if delay is not None else delay
        self.exp_id = int(exp_id) if exp_id is not None else exp_id
        if timestamp:
            self.timestamp = datetime.datetime.fromtimestamp(int(timestamp))
        else:
            self.timestamp = None
        self._experiment_started = False
        self._nodes_info = None
        self._times = {}
        if self._graph is None:
            self._stats = {}
            self._congs = {}
            self._first_cong = {}
        else:
            self._stats = {n: {'node': n} for n in self._graph.nodes}
            self._congs = {n: [] for n in self._graph.nodes}
            self._first_cong = {n: None for n in self._graph.nodes}
        self._c_started = re.compile(self.LOG_EXP_STARTED_PATTERN)
        self._c_data = re.compile(self.LOG_DATA_PATTERN)
        self._c_cong = re.compile(self.LOG_CONG_PATTERN)
        self._c_pktbuf_size = re.compile(self.LOG_PKTBUF_SIZE_PATTERN)
        self._c_pktbuf_usage = re.compile(self.LOG_PKTBUF_USAGE_PATTERN)
        self._c_rb_full = re.compile(self.LOG_RB_PATTERN)
        self._c_vrb_full = re.compile(self.LOG_VRB_PATTERN)
        self._c_frags_comp = re.compile(self.LOG_FRAGS_COMP_PATTERN)
        self._c_dgs_comp = re.compile(self.LOG_DGS_COMP_PATTERN)

    def _get_nodes_from_log(self):
        nodes = set()
        with open(self.logname) as logfile:
            csvfile = csv.reader(logfile, delimiter=';')
            try:
                for row in csvfile:
                    if len(row) < 2:
                        continue
                    nodes.add(row[1])
            except csv.Error as exc:
                logging.error("Error parsing %s:%d: %s", self.logname,
                              csvfile.line_num, exc)
                raise
        return nodes

    def _init_network(self, networks):
        self._graph = None
        for network in networks:
            nodes = self._get_nodes_from_log()
            network_edgelist = os.path.join(
                self.data_path,
                "{}.edgelist.gz".format(network)
            )
            assert os.path.exists(network_edgelist)
            graph = nx.read_edgelist(
                network_edgelist,
                data=[("weight", float)],
            )
            if all(node in graph.nodes() for node in nodes):
                self.network = network
                self._graph = graph
                break
        if self._graph is None:
            logging.error("No network found for %s in %s", self._logname,
                          networks)

    def __repr__(self):
        return "<{} '{}'>".format(
            type(self).__name__, self.logname
        )

    @classmethod
    def match(cls, filename, networks=None, data_path=None):
        """
        >>> LogParser.match('sfr-cc-sfr-congure_sfr-7_8-200x968B500ms-'
        ...                 '253471-1615839862.log', data_path='./')
        <LogParser './sfr-cc-sfr-congure_sfr-7_8-200x968B500ms-253471-1615839862.log'>
        >>> LogParser.match('sfr-cc-hwr-200x392B500ms-253471-1615819904.log',
        ...                 data_path='./')
        <LogParser './sfr-cc-hwr-200x392B500ms-253471-1615819904.log'>
        """     # noqa: E501
        match = cls._LOG_NAME_C.match(filename)
        if match is not None:
            return cls(filename, networks=networks, data_path=data_path,
                       **match.groupdict())
        return None

    @property
    def logname(self):
        return os.path.join(self.data_path, self._logname)

    @property
    def nodes_info(self):
        if self._nodes_info is None:
            with open(self.nodes_csv) as nodes_file:
                csvfile = csv.DictReader(nodes_file)
                self._nodes_info = {}
                for row in csvfile:
                    addr = ipaddress.IPv6Address(row['addr'])
                    key = (addr.packed[14] << 8) | addr.packed[15]
                    self._nodes_info[key] = row['name']
        return self._nodes_info

    @property
    def times_csv(self):
        """
        >>> LogParser('test.log', data_path='./').times_csv
        './test.times.csv'
        """
        return f'{self.logname[:-4]}.times.csv'

    @property
    def stats_csv(self):
        """
        >>> LogParser('test.log', data_path='./').stats_csv
        './test.stats.csv'
        """
        return f'{self.logname[:-4]}.stats.csv'

    @property
    def cong_csvs(self):
        """
        >>> LogParser('test.log', data_path='./').cong_csvs['m3-2']
        './test.m3-2.cong.csv'
        """
        class CongCSVDict:
            # pylint: disable=too-few-public-methods
            def __getitem__(_, node):
                # pylint: disable=no-self-argument
                return f'{self.logname[:-4]}.{node}.cong.csv'
        return CongCSVDict()

    @property
    def nodes_csv(self):
        """
        >>> LogParser('test.log', data_path='./').nodes_csv
        './nodes.csv'
        """
        return os.path.join(self.data_path, 'nodes.csv')

    def _addr_to_node(self, addr):
        """
        >>> parser = LogParser('test.log')
        >>> parser._nodes_info = {1: 'm3-42'}
        >>> parser._addr_to_node(1)
        'm3-42'
        """
        return self.nodes_info[addr]

    @staticmethod
    def _get_csv_writers(times_csvfile, stats_csvfile, cong_csvfiles):
        times_fieldnames = ['mode', 'data_len', 'src', 'dst',
                            'hops_to_sink', 'pkt_id', 'src_addr',
                            'send_time', 'recv_time', 'send_errno']
        times_csv = csv.DictWriter(times_csvfile,
                                   fieldnames=times_fieldnames,
                                   delimiter=';')
        times_csv.writeheader()
        stats_fieldnames = ['node', 'hops_to_sink', 'successors',
                            'pktbuf_usage', 'pktbuf_size',
                            'rb_full', 'vrb_full', 'frags_comp', 'dgs_comp']
        stats_csv = csv.DictWriter(stats_csvfile,
                                   fieldnames=stats_fieldnames,
                                   delimiter=';')
        stats_csv.writeheader()
        cong_fieldnames = ['time', 'type', 'tag', 'cwnd', 'ifg',
                           'resource_usage', 'fbuf_usage']
        cong_csvs = {}
        for node in cong_csvfiles:
            cong_csv = csv.DictWriter(cong_csvfiles[node],
                                      fieldnames=cong_fieldnames,
                                      delimiter=';')
            cong_csv.writeheader()
            cong_csvs[node] = cong_csv
        return times_csv, stats_csv, cong_csvs

    def _write_csvs(self):
        stats_csvfile = open(self.stats_csv, 'w')
        times_csvfile = open(self.times_csv, 'w')
        cong_csvfiles = {}
        sink = self.network.split('x')[0]
        for node in self._congs:
            cong_csvfiles[node] = open(self.cong_csvs[node], 'w')
        try:
            times_csv, stats_csv, cong_csvs = self._get_csv_writers(
                times_csvfile,
                stats_csvfile,
                cong_csvfiles,
            )
            for row in self._times.values():
                row["dst"] = sink
                # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
                shortest_path = nx.shortest_path(self._graph,
                                                 source=row["src"],
                                                 target=sink)
                row["hops_to_sink"] = len(shortest_path) - 1
                times_csv.writerow(row)
            successors = nx.dfs_successors(self._graph, sink)
            for row in self._stats.values():
                if "l2_retrans" in row:
                    row["l2_retrans"] = max(row["l2_retrans"])
                # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
                shortest_path = nx.shortest_path(self._graph,
                                                 source=row["node"],
                                                 target=sink)
                row["hops_to_sink"] = len(shortest_path) - 1
                row["successors"] = len(successors.get(row["node"], []))
                stats_csv.writerow(row)
            for node in cong_csvs:
                for row in self._congs[node]:
                    cong_csvs[node].writerow(row)
        finally:
            stats_csvfile.close()
            times_csvfile.close()
            for node in cong_csvfiles:
                cong_csvfiles[node].close()

    def _check_experiment_started(self, line):
        match = self._c_started.search(line)
        if match:
            assert int(match['count']) == self.count
            self._experiment_started = True
            return match.groupdict()
        return None

    def _parse_times_line(self, line):
        # pylint: disable=line-too-long
        """
        >>> parser = LogParser('test.log', mode='sfr', data_len=392)
        >>> parser._nodes_info = {
        ...     'fe80::ec66:70a7:ac0d:1881': 'm3-281'
        ... }
        >>> parser._parse_times_line(
        ...     '1615844416.475571;m3-281;send;1881:61616;392;0037',
        ... )
        {'mode': 'sfr', 'data_len': 392, 'src': 'm3-281', 'pkt_id': 55, 'send_time': 1615844416.475571}
        >>> parser._parse_times_line(
        ...     '1615844417.729934;m3-273;recv;1881;392;37',
        ... )
        {'mode': 'sfr', 'data_len': 392, 'src': 'm3-281', 'dst': 'm3-273', 'pkt_id': 55, 'recv_time': 1615844417.729934}
        """     # noqa: E501
        match = self._c_data.match(line)
        if match is None:
            return None
        direction = match['dir']
        addr = int(match['addr'], base=16)
        assert direction != 'send' or addr
        assert direction != 'recv' or addr
        assert self.data_len == int(match['data_len'])
        if direction == 'send':
            node = match['node']
            pkt_id = int(match['pkt_id'], base=16)
            res = {
                'mode': self.mode,
                'data_len': self.data_len,
                'src': node,
                'pkt_id': pkt_id,
                'send_time': float(match['time']),
            }
        else:
            node = self._addr_to_node(addr)
            pkt_id = int(match['pkt_id'], base=16)
            if (node, pkt_id) not in self._times:
                line = line.strip()
                logging.warning('%s: %s has no out from %s', self, line, node)
            res = {
                'mode': self.mode,
                'data_len': self.data_len,
                'src': node,
                'dst': match['node'],
                'pkt_id': pkt_id,
                'recv_time': float(match['time']),
            }
        if (node, pkt_id) in self._times:
            self._times[node, pkt_id].update(res)
        else:
            self._times[node, pkt_id] = res
        return res

    def _parse_cong_line(self, line):
        # pylint: disable=line-too-long
        """
        >>> parser = LogParser('test.log')
        >>> parser._parse_cong_line(
        ...     '1615844416.475571;m3-281;ce;12;40;4213'
        ... )
        ('m3-281', {'time': 0.0, 'type': 'ce', 'tag': 12, 'cwnd': 40, 'ifg': 4213})
        >>> parser._parse_cong_line(
        ...     '1615844868.482895;m3-281;ei;14;12;16'
        ... )
        ('m3-281', {'time': 452.0073239803314, 'type': 'ei', 'tag': 14, 'resource_usage': 0.75})
        """     # noqa: E501
        match = self._c_cong.match(line)
        if match is None:
            return None
        node = match['node']
        if self._first_cong.get(node) is None:
            self._first_cong[node] = float(match['time'])
        typ = match['type']
        cong = {
            'time': float(match['time']) - self._first_cong[node],
            'type': typ,
            'tag': int(match['tag']),
        }
        if typ.startswith('c'):
            cong['cwnd'] = int(match['param1'])
            cong['ifg'] = int(match['param2'])
        elif typ.startswith('e'):
            cong['resource_usage'] = int(match['param1']) / \
                                     int(match['param2'])
        else:
            raise LogError(f"Unknown congestion event '{typ}'")
        if node not in self._congs:
            self._congs[node] = []
        self._congs[node].append(cong)
        return node, cong

    def _update_int_stats(self, key, match, group=None):
        if group is None:
            group = key
        node = match['node']
        res = {key: int(match[group])}
        if node in self._stats:
            self._stats[node].update(res)
        else:
            self._stats[node] = res
        return node, res

    def _parse_pktbuf_size(self, line):
        # pylint: disable=line-too-long
        """
        >>> parser = LogParser('test.log')
        >>> parser._parse_pktbuf_size(
        ...     '1615843845.638419;m3-289;packet buffer: first byte: 0x20002618, last byte: 0x20003e18 (size: 6144)'
        ... )
        ('m3-289', {'pktbuf_size': 6144})
        """     # noqa: E501
        match = self._c_pktbuf_size.search(line)
        if match is None:
            return None
        return self._update_int_stats('pktbuf_size', match)

    def _parse_pktbuf_usage(self, line):
        """
        >>> parser = LogParser('test.log')
        >>> parser._parse_pktbuf_usage(
        ...     '1615843845.639756;m3-3;  position of last byte used: 2872'
        ... )
        ('m3-3', {'pktbuf_usage': 2872})
        """
        match = self._c_pktbuf_usage.search(line)
        if match is None:
            return None
        return self._update_int_stats('pktbuf_usage', match)

    def _parse_rb_full(self, line):
        """
        >>> parser = LogParser('test.log')
        >>> parser._parse_rb_full(
        ...     '1615843785.565115;m3-72;rbuf full: 1232'
        ... )
        ('m3-72', {'rb_full': 1232})
        """
        match = self._c_rb_full.search(line)
        if match is None:
            return None
        return self._update_int_stats('rb_full', match)

    def _parse_vrb_full(self, line):
        """
        >>> parser = LogParser('test.log')
        >>> parser._parse_vrb_full(
        ...     '1615893034.879088;m3-273;VRB full: 0'
        ... )
        ('m3-273', {'vrb_full': 0})
        """
        match = self._c_vrb_full.search(line)
        if match is None:
            return None
        return self._update_int_stats('vrb_full', match)

    def _parse_frags_comp(self, line):
        """
        >>> parser = LogParser('test.log')
        >>> parser._parse_frags_comp(
        ...     '1615893034.883486;m3-72;frags complete: 10'
        ... )
        ('m3-72', {'frags_comp': 10})
        """
        match = self._c_frags_comp.search(line)
        if match is None:
            return None
        return self._update_int_stats('frags_comp', match)

    def _parse_dgs_comp(self, line):
        """
        >>> parser = LogParser('test.log')
        >>> parser._parse_dgs_comp(
        ...     '1615893034.883486;m3-72;dgs complete: 5'
        ... )
        ('m3-72', {'dgs_comp': 5})
        """
        match = self._c_dgs_comp.search(line)
        if match is None:
            return None
        return self._update_int_stats('dgs_comp', match)

    def log_to_csvs(self):
        logging.info('Converting %s to CSVs', self._logname)

        try:
            parsing_functions = [f for f in dir(self)
                                 if f.startswith('_parse')]
            with open(self.logname, "rb") as logfile:
                for line in logfile:
                    line = line.decode(errors='ignore')
                    if not self._experiment_started:
                        self._check_experiment_started(line)
                        continue
                    for function in parsing_functions:
                        if getattr(self, function)(line):
                            break
            self._write_csvs()
        except (AssertionError, KeyboardInterrupt, LogError) as exc:
            if os.path.exists(self.times_csv):
                os.remove(self.times_csv)
            if os.path.exists(self.stats_csv):
                os.remove(self.stats_csv)
            for node in self._congs:
                if os.path.exists(self.cong_csvs[node]):
                    os.remove(self.cong_csvs[node])
            raise exc


class ThreadableParser(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exc = None

    @staticmethod
    def the_target(logname, networks, data_path=DATA_PATH):
        parser = LogParser.match(logname, networks=networks,
                                 data_path=data_path)
        if parser:
            parser.log_to_csvs()

    def run(self):
        try:
            super().run()
        except BaseException as exc:    # pylint: disable=broad-except
            self.exc = exc

    def join(self, *args, **kwargs):    # pylint: disable=signature-differs
        super().join(*args, **kwargs)
        if self.exc:
            raise self.exc


def logs_to_csvs(networks, data_path=DATA_PATH):
    threads = []
    for logname in os.listdir(data_path):
        kwargs = {
            'logname': logname,
            'networks': networks,
            'data_path': data_path,
        }
        thread = ThreadableParser(target=ThreadableParser.the_target,
                                  kwargs=kwargs)
        threads.append(thread)
        thread.start()
        if len(threads) > (multiprocessing.cpu_count() * 2):
            threads[random.randint(0, len(threads) - 1)].join()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbosity', default='INFO')
    parser.add_argument('networks', nargs='+')
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.verbosity))
    logs_to_csvs(args.networks)


if __name__ == '__main__':
    main()
