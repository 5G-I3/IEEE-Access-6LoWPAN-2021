/*
 * Copyright (C) 2015 Freie Universität Berlin
 *
 * This file is subject to the terms and conditions of the GNU Lesser
 * General Public License v2.1. See the file LICENSE in the top level
 * directory for more details.
 */

/**
 * @ingroup     tests
 * @{
 *
 * @file
 *
 * @author      Martine Lenders <mlenders@inf.fu-berlin.de>
 * @}
 */

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#include "assert.h"
#include "mutex.h"
#include "net/af.h"
#include "net/sock/async/event.h"
#include "net/sock/udp.h"
#include "net/sock/util.h"
#include "random.h"
#include "shell.h"
#include "thread.h"
#include "xtimer.h"

#include "app.h"

#ifndef UDP_COUNT
#define UDP_COUNT   (200)
#endif

#if APP_LOG_ENABLE
mutex_t app_output_mutex;
#endif

static uint8_t sock_inbuf[1232U];
static uint8_t sock_outbuf[1232U];
static char server_stack[THREAD_STACKSIZE_DEFAULT];
static event_queue_t server_queue;
static sock_udp_t server_sock;
static bool server_running;
static kernel_pid_t server_pid;

static void _udp_recv(sock_udp_t *sock, sock_async_flags_t flags, void *arg)
{
    (void)arg;
    if (flags & SOCK_ASYNC_MSG_RECV) {
        sock_udp_ep_t src;
        int res;

        if ((res = sock_udp_recv(sock, sock_inbuf, sizeof(sock_inbuf),
                                 0, &src)) < 2) {
            printf("error");
        }
        else {
            printf("recv;%02x%02x;%d;%02x%02x\n", src.addr.ipv6[14],
                   src.addr.ipv6[15], res, sock_inbuf[0], sock_inbuf[1]);
        }
    }
}

static void *_server_thread(void *args)
{
    (void)args;
    event_queue_init(&server_queue);
    event_loop(&server_queue);
    return NULL;
}

static int udp_send(char *addr_str, int data_len, int delay)
{
    sock_udp_t sock;
    sock_udp_ep_t dst = SOCK_IPV6_EP_ANY;
    xtimer_ticks32_t last_wakeup;
    int delay_base = ((delay * US_PER_MS) - ((delay * US_PER_MS) / 2));
    int delay_range = delay * US_PER_MS;

    static_assert(UDP_COUNT <= 0xffff);
    if ((data_len <= 0) || (data_len > 1232)) {
        printf("Error: invalid data_len %d\n", data_len);
    }
    if (delay <= 0) {
        printf("Error: invalid delay %d\n", delay);
    }
    /* parse destination address */
    if (sock_udp_str2ep(&dst, addr_str) < 0) {
        puts("Error: unable to parse destination address");
        return 1;
    }
    if (dst.port == 0) {
        puts("Error: no port or illegal port value provided");
        return 1;
    }
    if (sock_udp_create(&sock, NULL, NULL, 0) < 0) {
        puts("Error: can not create sock");
        return 1;
    }
    printf("Sending %d packets\n", UDP_COUNT);
    xtimer_msleep(random_uint32_range(0, delay + 1));
    for (unsigned int i = 0; i < UDP_COUNT; i++) {
        int res = 0;

        for (int j = 0; j < data_len; j += 2) {
            sock_outbuf[j] = (i >> 8) & 0xff;
            if ((j + 1) < data_len) {
                sock_outbuf[j + 1] = i & 0xff;
            }
        }
        if (i > 0) {
            xtimer_periodic_wakeup(
                &last_wakeup,
                delay_base +
                ((delay_range) ? random_uint32_range(0, delay_range) : 0)
            );
        }
        else {
            last_wakeup = xtimer_now();
        }
        if ((res = sock_udp_send(&sock, sock_outbuf, data_len, &dst)) < 0) {
            APP_LOG("error;%02x%02x;%d;%02x%02x\n", dst.addr.ipv6[14],
                    dst.addr.ipv6[15], -res, sock_outbuf[0],
                    sock_outbuf[1]);
        }
        else {
            APP_LOG("send;%02x%02x;%d;%02x%02x\n", dst.addr.ipv6[14],
                    dst.addr.ipv6[15], res, sock_outbuf[0],
                    sock_outbuf[1]);
        }
    }
    return 0;
}

static int udp_start_server(char *port_str)
{
    sock_udp_ep_t server_addr = SOCK_IPV6_EP_ANY;
    int res;

    if (server_running) {
        puts("Server already running");
        return 1;
    }
    /* parse port */
    server_addr.port = atoi(port_str);
    if ((res = sock_udp_create(&server_sock, &server_addr, NULL, 0)) < 0) {
        printf("Unable to open UDP server on port %" PRIu16 " (error code %d)\n",
               server_addr.port, -res);
        return 1;
    }
    if ((server_pid == KERNEL_PID_UNDEF) &&
        (server_pid = thread_create(server_stack, sizeof(server_stack),
                                    THREAD_PRIORITY_MAIN - 1,
                                    THREAD_CREATE_STACKTEST, _server_thread,
                                    port_str, "UDP server")) <= KERNEL_PID_UNDEF) {
        return 1;
    }
    sock_udp_event_init(&server_sock, &server_queue, _udp_recv, NULL);
    server_running = true;
    printf("Success: started UDP server on port %" PRIu16 "\n",
           server_addr.port);
    return 0;
}

static int udp_stop_server(void)
{
    sock_udp_close(&server_sock);
    server_running = false;
    puts("Success: stopped UDP server");
    return 0;
}

int udp_cmd(int argc, char **argv)
{
    if (argc < 2) {
        printf("usage: %s [send|server]\n", argv[0]);
        return 1;
    }

    if (strcmp(argv[1], "send") == 0) {
        if (argc < 5) {
            printf("usage: %s send <addr>:<port> <data_len> <delay in ms>\n",
                   argv[0]);
            return 1;
        }
        return udp_send(argv[2], atoi(argv[3]), atoi(argv[4]));
    }
    else if (strcmp(argv[1], "server") == 0) {
        if (argc < 3) {
            printf("usage: %s server [start|stop]\n", argv[0]);
            return 1;
        }
        if (strcmp(argv[2], "start") == 0) {
            if (argc < 4) {
                printf("usage %s server start <port>\n", argv[0]);
                return 1;
            }
            return udp_start_server(argv[3]);
        }
        if (strcmp(argv[2], "stop") == 0) {
            return udp_stop_server();
        }
        else {
            puts("error: invalid command");
            return 1;
        }
    }
    else {
        puts("error: invalid command");
        return 1;
    }
}

/** @} */
