#!/bin/bash
#
# Copyright (C) 2019 Freie Universität berlin
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}"  )" >/dev/null 2>&1 && pwd  )"
export DATA_DIR=$(realpath -L ${SCRIPT_DIR}/../../results)

SESSION=6lo-comp
RUN_WINDOW=run
DISPATCH_WINDOW=dispatch

export PYTHONPATH=$(readlink -f "${SCRIPT_DIR}/../../RIOT/dist/pythonlibs")

. ${SCRIPT_DIR}/ssh-agent.cfg
if [ -z "${SSH_AGENT_PID}" ] || ! ps -p ${SSH_AGENT_PID} > /dev/null; then
    ssh-agent > ${SCRIPT_DIR}/ssh-agent.cfg
    . ${SCRIPT_DIR}/ssh-agent.cfg
fi

if ! ssh-add -l &> /dev/null; then
    ssh-add
fi

tmux new-session -d -s ${SESSION} -n ${RUN_WINDOW} -c ${SCRIPT_DIR} \
        script -fa "${DATA_DIR}/${SESSION}.${RUN_WINDOW}.log" \; \
     send-keys -t ${SESSION}:${RUN_WINDOW} "cd ${SCRIPT_DIR}" Enter \; \
     new-window -t ${SESSION} -n ${DISPATCH_WINDOW} -c ${SCRIPT_DIR} \
        script -fa "${DATA_DIR}/${SESSION}.${DISPATCH_WINDOW}.log" \; \
     send-keys -t ${SESSION}:${DISPATCH_WINDOW} "cd ${SCRIPT_DIR}" Enter \; \
     send-keys -t ${SESSION}:${DISPATCH_WINDOW} \
        ". ${SCRIPT_DIR}/env/bin/activate" Enter \; \
     send-keys -t ${SESSION}:${DISPATCH_WINDOW} \
        "pip install -r${SCRIPT_DIR}/requirements.txt" Enter \; \
     send-keys -t ${SESSION}:${DISPATCH_WINDOW} \
        "while true; do ${SCRIPT_DIR}/dispatch_experiments.py && break; " \
        "sleep 10; done" Enter \; \
     attach -t ${SESSION}:${DISPATCH_WINDOW}
