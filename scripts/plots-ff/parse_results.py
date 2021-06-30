#!/usr/bin/env python3
#
# Copyright (C) 2019 Freie Universität Berlin
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

import csv
import ipaddress
import logging
import networkx as nx
import re
import multiprocessing
import os
import queue
import threading

__author__ = "Martine S. Lenders"
__copyright__ = "Copyright 2019 Freie Universität Berlin"
__license__ = "LGPL v2.1"
__email__ = "match.lenders@fu-berlin.de"

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))

DATA_PATH = os.environ.get("DATA_PATH",
                           os.path.join(SCRIPT_PATH, "..", "..", "results"))
GLOBAL_PREFIX = os.environ.get("GLOBAL_PREFIX", "2001:db8:0:1:")

NAME_PATTERN = r"6lo_comp_" \
               r"n(?P<network>m3-\d+x[0-9a-f]+)_c\d+__" \
               r"m{mode}_r{data_len}Bx(?P<count>\d+)x{delay}ms_(?P<timestamp>\d+)"
LOG_NAME_PATTERN = r"{}\.log".format(NAME_PATTERN.format(
    mode=r"(?P<mode>(hwr|ff|e2e|sfr-\w+))",
    data_len=r"(?P<data_len>\d+)",
    delay=r"\d+"
))

LOG_EXP_STARTED_PATTERN = r"Sending \d+ packets"
LOG_DATA_PATTERN = r"(?P<time>\d+.\d+);(?P<node>m3-\d+);" \
                   r"(> ?)?(?P<dir>(recv|send|error));" \
                   r"(?P<addr>[0-9a-f]+);" \
                   r"(?P<errno>\d+);(?P<pkt_id>[0-9a-f]+)"
LOG_RETRANS_PATTERN = r"(?P<node>m3-\d+);\s+TX succeeded \d+ errors \d+ " \
                      r"retransmissions (?P<retrans>\d+)"
LOG_PKTBUF_SIZE_PATTERN = r"(?P<node>m3-\d+);packet buffer: " \
                          r"first byte: 0x[0-9a-f]+, last byte: 0x[0-9a-f]+ " \
                          r"\(size: (?P<pktbuf_size>\d+)\)"
LOG_PKTBUF_USAGE_PATTERN = r"(?P<node>m3-\d+);  position of last byte " \
                           r"used: (?P<pktbuf_usage>\d+)"
LOG_RBUF_PATTERN = r"(?P<node>m3-\d+);rbuf full: (?P<rbuf_full>\d+)"
LOG_VRB_PATTERN = r"(?P<node>m3-\d+);VRB full: (?P<vrb_full>\d+)"
LOG_FRAG_COMP_PATTERN = r"(?P<node>m3-\d+);frags complete: (?P<frag_comp>\d+)"
LOG_DG_COMP_PATTERN = r"(?P<node>m3-\d+);dgs complete: (?P<dg_comp>\d+)"

LINK_LOCAL_PREFIX = "fe80::"


class LogError(Exception):
    pass


def times_csvname(logname):
    """
    >>> time_csvname("test.log")
    'test.csv'
    """
    csvname = "{}times.csv".format(logname[:-3])
    return csvname


def stats_csvname(logname):
    """
    >>> time_csvname("test.log")
    'test.csv'
    """
    csvname = "{}stats.csv".format(logname[:-3])
    return csvname


def _src_addr_to_src(addr, network, data_path=DATA_PATH):
    with open(os.path.join(data_path, "nodes.csv".format(network))) \
         as lla_file:
        csvfile = csv.DictReader(lla_file)
        for row in csvfile:
            lla = ipaddress.IPv6Address(row["addr"])
            if (lla.packed[14] << 8) | lla.packed[15] == int(addr, base=16):
                return row["name"]
    return None


def _parse_times_line(network, mode, data_len, line, match, times,
                      data_path=DATA_PATH):
    direction = match.group("dir")
    addr = match.group("addr")
    if direction in ["send", "error"]:
        node = match.group("node")
        pkt_id = int(match.group("pkt_id"), base=16)
        return {
            "mode": mode,
            "data_len": data_len,
            "src": node,
            "pkt_id": pkt_id,
            "send_time": float(match.group("time")),
            "send_errno": int(match.group("errno") if direction == "error" else
                              0)
        }
    else:
        node = _src_addr_to_src(addr, network, data_path)
        pkt_id = int(match.group("pkt_id"), base=16)
        dst = match.group("node")
        assert node is not None
        return {
            "mode": mode,
            "data_len": data_len,
            "src": node,
            "dst": dst,
            "pkt_id": pkt_id,
            "src_addr": addr,
            "recv_time": float(match.group("time")),
        }


def _get_csv_writers(times_csvfile, stats_csvfile):
    times_fieldnames = ["mode", "data_len", "src", "dst",
                        "hops_to_sink", "pkt_id", "src_addr",
                        "send_time", "recv_time", "send_errno"]
    times_csv = csv.DictWriter(times_csvfile,
                               fieldnames=times_fieldnames,
                               delimiter=";")
    stats_fieldnames = ["node", "hops_to_sink", "successors",
                        "l2_retrans", "pktbuf_usage", "pktbuf_size",
                        "rbuf_full", "vrb_full", "frag_comp", "dg_comp"]
    stats_csv = csv.DictWriter(stats_csvfile,
                               fieldnames=stats_fieldnames,
                               delimiter=";")
    times_csv.writeheader()
    stats_csv.writeheader()
    return times_csv, stats_csv


def _write_csvs(times, times_csvfile, stats, stats_csvfile, graph, sink):
    times_csv, stats_csv = _get_csv_writers(times_csvfile, stats_csvfile)
    for row in times.values():
        row["dst"] = sink
        shortest_path = nx.shortest_path(graph, row["src"], sink)
        row["hops_to_sink"] = len(shortest_path) - 1
        times_csv.writerow(row)
    successors = nx.dfs_successors(graph, sink)
    for row in stats.values():
        if "l2_retrans" in row:
            row["l2_retrans"] = max(row["l2_retrans"])
        shortest_path = nx.shortest_path(graph, row["node"], sink)
        row["hops_to_sink"] = len(shortest_path) - 1
        row["successors"] = len(successors.get(row["node"], []))
        stats_csv.writerow(row)


def log_to_csvs(logname, network, mode, data_len, data_path=DATA_PATH,
                count=50):
    logging.info("Converting {} to CSVs".format(logname))
    logging.info(" - {}".format(stats_csvname(logname)))
    logging.info(" - {}".format(times_csvname(logname)))

    try:
        network_edgelist = os.path.join(data_path,
                                        "{}.edgelist.gz".format(network))
        assert os.path.exists(network_edgelist)
        with open(logname, "rb") as logfile, \
                open(times_csvname(logname), "w") as times_csvfile, \
                open(stats_csvname(logname), "w") as stats_csvfile:
            c_started = re.compile(LOG_EXP_STARTED_PATTERN)

            c_data = re.compile(LOG_DATA_PATTERN)

            c_retrans = re.compile(LOG_RETRANS_PATTERN)
            c_pktbuf_size = re.compile(LOG_PKTBUF_SIZE_PATTERN)
            c_pktbuf_usage = re.compile(LOG_PKTBUF_USAGE_PATTERN)
            c_rbuf = re.compile(LOG_RBUF_PATTERN)
            c_vrb = re.compile(LOG_VRB_PATTERN)
            c_frag_comp = re.compile(LOG_FRAG_COMP_PATTERN)
            c_dg_comp = re.compile(LOG_DG_COMP_PATTERN)
            experiment_started = False
            times = {}
            stats = {}
            graph = nx.read_edgelist(network_edgelist,
                                     data=[("weight", float)])
            stats = {n: {"node": n} for n in graph.nodes}
            sink = network.split("x")[0]
            for line in logfile:
                line = line.decode(errors="ignore")
                if not experiment_started:
                    if c_started.search(line) is not None:
                        experiment_started = True
                    continue

                match = c_data.match(line)
                if match is not None:
                    res = _parse_times_line(network, mode, data_len,
                                            line, match, times, data_path)
                    if (res["src"], res["pkt_id"]) in times:
                        times[res["src"], res["pkt_id"]].update(res)
                    else:
                        times[res["src"], res["pkt_id"]] = res
                    continue

                match = c_retrans.search(line)
                if match is not None:
                    node = match.group("node")
                    l2_retrans = int(match.group("retrans"))
                    if "l2_retrans" in stats[node]:
                        stats[node]["l2_retrans"].append(l2_retrans)
                    else:
                        stats[node].update({"l2_retrans": [l2_retrans]})
                    continue

                match = c_pktbuf_size.search(line)
                if match is not None:
                    node = match.group("node")
                    pktbuf_size = int(match.group("pktbuf_size"))
                    stats[node].update({"pktbuf_size": pktbuf_size})
                    continue

                match = c_pktbuf_usage.search(line)
                if match is not None:
                    node = match.group("node")
                    pktbuf_usage = int(match.group("pktbuf_usage"))
                    stats[node].update({"pktbuf_usage": pktbuf_usage})
                    continue

                match = c_rbuf.search(line)
                if match is not None:
                    node = match.group("node")
                    rbuf_full = int(match.group("rbuf_full"))
                    stats[node].update({"rbuf_full": rbuf_full})
                    continue

                match = c_vrb.search(line)
                if match is not None:
                    node = match.group("node")
                    vrb_full = int(match.group("vrb_full"))
                    stats[node].update({"vrb_full": vrb_full})
                    continue

                match = c_frag_comp.search(line)
                if match is not None:
                    node = match.group("node")
                    frag_comp = int(match.group("frag_comp"))
                    stats[node].update({"frag_comp": frag_comp})
                    continue

                match = c_dg_comp.search(line)
                if match is not None:
                    node = match.group("node")
                    dg_comp = int(match.group("dg_comp"))
                    stats[node].update({"dg_comp": dg_comp})
                    continue
            _write_csvs(times, times_csvfile, stats, stats_csvfile,
                        graph, sink)
    except KeyboardInterrupt as exc:
        os.remove(times_csvname(logname))
        os.remove(stats_csvname(logname))
        raise exc
    except LogError as exc:
        os.remove(times_csvname(logname))
        os.remove(stats_csvname(logname))
        logging.error(exc)


class ConverterThread(threading.Thread):
    def __init__(self, data_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = queue.Queue()
        self.data_path = data_path

    def run(self, *args, **kwargs):
        while True:
            item = self.queue.get()
            if item["logname"] is None:
                return
            log_to_csvs(item["logname"], data_path=self.data_path,
                        **item["params"])


def match_to_dict(match):
    res = match.groupdict()
    res["data_len"] = int(res["data_len"])
    del res["timestamp"]
    return res


def logs_to_csvs(data_path=DATA_PATH):
    comp = re.compile(LOG_NAME_PATTERN)
    threads = [ConverterThread(data_path)
               for _ in range(multiprocessing.cpu_count())]
    next_thread = 0
    for thread in threads:
        thread.start()
    for logname in os.listdir(data_path):
        match = comp.match(logname)
        if match is not None:
            logname = os.path.join(data_path, logname)
            threads[next_thread].queue.put(
                {"logname": logname, "params": match_to_dict(match)}
            )
            next_thread += 1
            next_thread %= len(threads)
    for thread in threads:
        thread.queue.put({"logname": None})
    for thread in threads:
        thread.join()


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s: %(message)s',
                        level=logging.INFO)
    logs_to_csvs()
