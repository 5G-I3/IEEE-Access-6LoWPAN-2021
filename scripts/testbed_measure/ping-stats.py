#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (C) 2019 Freie Universität Berlin
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

import csv
import iotlabcli.auth
import iotlabcli.experiment
import iotlabcli.rest
import logging
import math
import random
import pexpect
import os
import sys
import threading
import time
import urllib.error

__author__ = "Martine S. Lenders"
__copyright__ = "Copyright 2019 Freie Universität Berlin"
__license__ = "LGPL v2.1"
__email__ = "m.lenders@fu-berlin.de"

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.environ.get("DATA_PATH",
                           os.path.join(SCRIPT_PATH, "..", "..", "results"))
DISTANCES_CSV = os.path.join(DATA_PATH, "distance_test.csv")
FIRMWARE_ELF = os.environ.get("FIRMWARE_ELF",
                              os.path.join(SCRIPT_PATH, "firmware.elf"))

DEFAULT_DURATION = 5

ARCHI_SHORT = "m3"
ARCHI_FULL = "m3:at86rf231"
SITE = "lille"
DOMAIN = "iot-lab.info"

exp_ids = set()


def _node_positions(api):
    nodes = iotlabcli.experiment.info_experiment(
            api,
            site=SITE,
            archi=ARCHI_FULL,
            state="Alive"
        )["items"]
    res = {}
    for node in nodes:
        node_num = int(node["network_address"].split(".")[0][3:])
        res[node_num] = (
                float(node["x"]),
                float(node["y"]),
                float(node["z"])
            )
    return res


def _get_exp_resources(nodes):
    def _node_url(node):
        """
        >>> _node_url(3)
        'm3-3.grenoble.iot-lab.info'
        """
        return "{}-{}.{}.{}".format(ARCHI_SHORT, node, SITE, DOMAIN)

    assert(os.path.exists(FIRMWARE_ELF))
    return [
            iotlabcli.experiment.exp_resources(
                    [_node_url(node) for node in nodes], FIRMWARE_ELF
                )
        ]


def _stop_experiment(exp_id, wait=True):
    iotlabcli.experiment.stop_experiment(api, exp_id)
    exp_ids.remove(exp_id)
    if wait:
        iotlabcli.experiment.wait_experiment(api, exp_id, "Finishing")


def _distance(node, ref):
    return math.sqrt((node[0] - ref[0])**2 +
                     (node[1] - ref[1])**2 +
                     (node[2] - ref[2])**2)


def run_experiment(user):
    nodes = _node_positions(api)
    pinger = random.choice(list(nodes.keys()))
    target = pinger
    d = 30
    while pinger == target or d > 20:
        target = random.choice(list(nodes.keys()))
        d = _distance(nodes[pinger], nodes[target])
    exp = iotlabcli.experiment.submit_experiment(api, "test-ping",
                                                 DEFAULT_DURATION,
                                                 _get_exp_resources([pinger,
                                                                     target]))
    exp_ids.add(exp["id"])
    try:
        iotlabcli.experiment.wait_experiment(api, exp["id"],
                                             timeout=60)
        child = pexpect.spawnu("ssh {}@{}.{} serial_aggregator -i {}"
                               .format(user, SITE, DOMAIN, exp["id"]))
        child.logfile = sys.stdout
        child.sendline("m3-{};ifconfig".format(target))
        res = child.expect([r"inet6 addr: (fe80::[0-9a-f:]+)  "
                            r"scope: local  VAL",
                            r"Connection closed", pexpect.EOF])
        # something went wrong on the node => stop experiment
        if res > 0:
            return
        target_addr = child.match.group(1)
        while True:
            child.sendline("m3-{};ping6 -c 500 -i 50 -W 100 {}"
                           .format(pinger, target_addr))
            child.expect([r", (\d+)% packet loss", r"Connection closed",
                          pexpect.TIMEOUT, pexpect.EOF])
            if res > 0:
                break
            else:
                with open("distance_test.csv", "a") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow([exp["id"], pinger, target, d,
                                     int(child.match.group(1))])
            time.sleep(1)
    finally:
        _stop_experiment(exp["id"])


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s: %(message)s',
                        level=logging.INFO)
    # user, password
    credentials = iotlabcli.auth.get_user_credentials()
    api = iotlabcli.rest.Api(*credentials)
    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)
    if not os.path.exists(DISTANCES_CSV):
        with open(DISTANCES_CSV, "w") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["exp_id", "node1", "node2", "d", "packet loss"])
    threads = []
    try:
        while True:
            ts = list(range(10))
            for i, t in enumerate(ts):
                ts[i] = threading.Timer(random.randint(1, 3000) / 1000,
                                        run_experiment, (credentials[0],))
                ts[i].start()
            threads.extend(ts)
            time.sleep(DEFAULT_DURATION * 60)
    finally:
        for exp_id in exp_ids:
            try:
                _stop_experiment(exp_id, False)
            except urllib.error.HTTPError:
                pass
        for t in threads:
            t.join()
