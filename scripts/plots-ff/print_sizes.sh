#!/bin/bash
#
# Copyright (C) 2019 Freie Universität berlin
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

if ! command -v arm-none-eabi-size &> /dev/null; then
    echo "Needs arm-none-eabi-size tool not in PATH" >&2
    return 1
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}"  )" >/dev/null 2>&1 && pwd  )"
SOURCE_DIR=$(realpath "${SCRIPT_DIR}/../../apps/source/")

win=${1:-1}
ifg=${2:-100}
arq=${3:-1200}
frag=${4:-4}
dg=${5:-0}

for mode in hwr ff sfr; do
    echo "${mode}"
    MODE=${mode} WIN_SIZE=${win} INTER_FRAME_GAP=${ifg} RIOT_CI_BUILD=1 \
        RETRY_TIMEOUT=${arq} RETRIES=${frag} DATAGRAM_RETRIES=${dg} WERROR=0 \
        CFLAGS=-DNDEBUG=1 make -C ${SOURCE_DIR} clean all -j &> /dev/null || \
        exit 1
    arm-none-eabi-size -t \
        bin/iotlab-m3/gnrc_sixlowpan_frag_fb.a 2> /dev/null | \
        grep "(TOTALS)" | awk '{print "Fragmentation Buffer",$1+$2,$2+$3}'
    arm-none-eabi-size -t \
        bin/iotlab-m3/gnrc_sixlowpan_frag_rb.a 2> /dev/null | \
        grep "(TOTALS)" | awk '{print "Reassembly Buffer",$1+$2,$2+$3}'
    arm-none-eabi-size -t \
        bin/iotlab-m3/gnrc_sixlowpan_frag_vrb.a 2> /dev/null | \
        grep "(TOTALS)" | awk '{print "Virtual Reassembly Buffer",$1+$2,$2+$3}'
    arm-none-eabi-size -t \
        bin/iotlab-m3/gnrc_sixlowpan_ctx.a \
        bin/iotlab-m3/gnrc_sixlowpan_iphc.a \
        bin/iotlab-m3/gnrc_sixlowpan_frag.a \
        bin/iotlab-m3/gnrc_sixlowpan_frag_minfwd.a \
        bin/iotlab-m3/gnrc_sixlowpan_frag_sfr.a 2> /dev/null | \
        grep "(TOTALS)" | awk '{print "Protocol implementation",$1+$2,$2+$3}'
    arm-none-eabi-size -t \
        bin/iotlab-m3/gnrc_sixlowpan_frag_fb.a \
        bin/iotlab-m3/gnrc_sixlowpan_frag_rb.a \
        bin/iotlab-m3/gnrc_sixlowpan_frag_vrb.a \
        bin/iotlab-m3/gnrc_sixlowpan_ctx.a \
        bin/iotlab-m3/gnrc_sixlowpan_iphc.a \
        bin/iotlab-m3/gnrc_sixlowpan_frag.a \
        bin/iotlab-m3/gnrc_sixlowpan_frag_minfwd.a \
        bin/iotlab-m3/gnrc_sixlowpan_frag_sfr.a 2> /dev/null | \
        grep "(TOTALS)" | awk '{print "Sum",$1+$2,$2+$3}'
done
