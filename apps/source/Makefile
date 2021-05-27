# name of your application
APPLICATION ?= 6lo-ff-source

# If no BOARD is found in the environment, use this default:
BOARD ?= iotlab-m3

# This has to be the absolute path to the RIOT base directory:
RIOTBASE ?= $(CURDIR)/../../RIOT/


USEMODULE += auto_init_gnrc_netif
USEMODULE += gnrc_netdev_default
USEMOUDLE += gnrc_netif_pktq

USEMODULE += auto_init_gnrc_rpl
USEMODULE += gnrc_icmpv6_echo
USEMODULE += gnrc_ipv6_router_default
USEMODULE += gnrc_sixlowpan_frag_stats
USEMODULE += gnrc_rpl

USEMODULE += gnrc_udp
USEMODULE += sock_async_event
USEMODULE += sock_udp
USEMODULE += sock_util

USEMODULE += netstats_l2
USEMODULE += netstats_ipv6
USEMODULE += netstats_rpl

USEMODULE += shell
USEMODULE += shell_commands

USEMODULE += od
USEMODULE += prng_mersenne
USEMODULE += ps
USEMODULE += random

# configure experiment mode
# - hwr: hop-wise reassembly (HWR)
# - sfr: selective fragment recovery (SFR)
MODE ?= sfr

ifeq (sfr, $(MODE))
  USEMODULE += gnrc_sixlowpan_frag_sfr
  USEMODULE += gnrc_sixlowpan_frag_sfr_stats
  USEMODULE += gnrc_sixlowpan_frag_sfr_ecn_if_in
  USEMODULE += gnrc_sixlowpan_frag_sfr_ecn_if_out
  USEMODULE += gnrc_sixlowpan_frag_sfr_ecn_fqueue

  ifeq (,$(CONGURE_IMPL))
    USEMODULE += gnrc_sixlowpan_frag_sfr_congure_sfr
  else
    ifeq (congure_abe,$(CONGURE_IMPL))
      USEMODULE += gnrc_sixlowpan_frag_sfr_congure_abe
    else
      ifeq (congure_quic,$(CONGURE_IMPL))
        USEMODULE += gnrc_sixlowpan_frag_sfr_congure_quic
        USEMODULE += ztimer_msec
        USEMODULE += ztimer_periph_rtt
      else
        ifeq (congure_reno,$(CONGURE_IMPL))
          USEMODULE += gnrc_sixlowpan_frag_sfr_congure_reno
        else
          ifeq (congure_sfr,$(CONGURE_IMPL))
            USEMODULE += gnrc_sixlowpan_frag_sfr_congure_sfr
          else
            $(error "Unknown CongURE implementation `$(CONGURE_IMPL)`")
          endif
        endif
      endif
    endif
  endif
else
  ifneq (hwr,$(MODE))
    $(error "Unknown mode `$(MODE)`")
  endif
endif

DEVELHELP ?= 1

ifeq (1, $(DEVELHELP))
  USEMODULE += gnrc_pktbuf_cmd      # include `pktbuf` shell command
endif

APP_LOG ?= 1                # Enable logging of congestion events

PKTBUF_SIZE ?= 40960        # Packet buffer size
NETIF_SEND_QUEUE_SIZE ?= 8  # Network interface send queue size
FB_SIZE ?= 4                # Fragmentation buffer size
RB_SIZE ?= 1                # Reassembly buffer size
RB_TIMEOUT ?= 10000000      # Reassembly buffer timeout (10s)
RB_DEL_TIMER ?= 250         # Deletion timer for reassembly buffer entry after datagram completion
VRB_SIZE ?= 16              # Virtual reassembly buffer size
SFR_INIT_WIN_SIZE ?= 2      # Initial window size for recovery mechanism
SFR_INTER_FRAME_GAP ?= 170000   # Fallback for inter-frame gap: Microseconds between two SFR frames
SFR_ARQ_TIMEOUT ?= 2500     # Retry timeout for recovery mechanism
SFR_FRAG_RETRIES ?= 4       # Number of retries for recovery mechanism
SFR_DATAGRAM_RETRIES ?= 0   # Number of datagram retries for SFR
SFR_ECN_NUM ?= 1            # Numerator for ECN threshold fraction
SFR_ECN_DEN ?= 2            # Denominator for ECN threshold fraction
UDP_COUNT ?= 200            # Number of packets to send

CFLAGS += -DUDP_COUNT=$(UDP_COUNT)
CFLAGS += -DAPP_LOG_ENABLE=$(APP_LOG)
CFLAGS += -DDEBUG_ASSERT_VERBOSE=1    # activate verbose output on assert

# Expose environment variable to build docker image
DOCKER_ENV_VARS += DEVELHELP
DOCKER_ENV_VARS += APP_LOG
DOCKER_ENV_VARS += MODE
DOCKER_ENV_VARS += CONGURE_IMPL
DOCKER_ENV_VARS += PKTBUF_SIZE
DOCKER_ENV_VARS += NETIF_SEND_QUEUE_SIZE
DOCKER_ENV_VARS += FB_SIZE
DOCKER_ENV_VARS += RB_SIZE
DOCKER_ENV_VARS += RB_TIMEOUT
DOCKER_ENV_VARS += RB_DEL_TIMER
DOCKER_ENV_VARS += VRB_SIZE
DOCKER_ENV_VARS += SFR_INIT_WIN_SIZE
DOCKER_ENV_VARS += SFR_INTER_FRAME_GAP
DOCKER_ENV_VARS += SFR_ARQ_TIMEOUT
DOCKER_ENV_VARS += SFR_FRAG_RETRIES
DOCKER_ENV_VARS += SFR_DATAGRAM_RETRIES
DOCKER_ENV_VARS += SFR_ECN_NUM
DOCKER_ENV_VARS += SFR_ECN_DEN
DOCKER_ENV_VARS += UDP_COUNT

INCLUDES += -I$(CURDIR)

include $(RIOTBASE)/Makefile.include

ifndef CONFIG_GNRC_PKTBUF_SIZE
  CFLAGS += -D"CONFIG_GNRC_PKTBUF_SIZE"=$(PKTBUF_SIZE)
endif
ifndef CONFIG_GNRC_NETIF_PKTQ_POOL_SIZE
  CFLAGS += -D"CONFIG_GNRC_NETIF_PKTQ_POOL_SIZE"=$(NETIF_SEND_QUEUE_SIZE)
endif
ifndef CONFIG_GNRC_SIXLOWPAN_FRAG_FB_SIZE
  CFLAGS += -D"CONFIG_GNRC_SIXLOWPAN_FRAG_FB_SIZE"=$(FB_SIZE)
endif
ifndef CONFIG_GNRC_SIXLOWPAN_FRAG_RBUF_SIZE
  CFLAGS += -D"CONFIG_GNRC_SIXLOWPAN_FRAG_RBUF_SIZE"=$(RB_SIZE)
endif
ifndef CONFIG_GNRC_SIXLOWPAN_FRAG_RBUF_TIMEOUT_US
  CFLAGS += -D"CONFIG_GNRC_SIXLOWPAN_FRAG_RBUF_TIMEOUT_US"=$(RB_TIMEOUT)
endif
ifndef CONFIG_GNRC_SIXLOWPAN_FRAG_RBUF_DO_NOT_OVERRIDE=1
  CFLAGS += -D"CONFIG_GNRC_SIXLOWPAN_FRAG_RBUF_DO_NOT_OVERRIDE"=1
endif
ifndef CONFIG_GNRC_SIXLOWPAN_FRAG_RBUF_DEL_TIMER
  CFLAGS += -D"CONFIG_GNRC_SIXLOWPAN_FRAG_RBUF_DEL_TIMER"=$(RB_DEL_TIMER)
endif
ifndef CONFIG_GNRC_SIXLOWPAN_FRAG_VRB_SIZE
  CFLAGS += -D"CONFIG_GNRC_SIXLOWPAN_FRAG_VRB_SIZE"=$(VRB_SIZE)
endif
ifndef CONFIG_GNRC_SIXLOWPAN_SFR_OPT_WIN_SIZE
  CFLAGS += -D"CONFIG_GNRC_SIXLOWPAN_SFR_OPT_WIN_SIZE"=$(SFR_INIT_WIN_SIZE)
endif
ifndef CONFIG_GNRC_SIXLOWPAN_SFR_INTER_FRAME_GAP_US
  CFLAGS += -D"CONFIG_GNRC_SIXLOWPAN_SFR_INTER_FRAME_GAP_US"=$(SFR_INTER_FRAME_GAP)
endif
ifndef CONFIG_GNRC_SIXLOWPAN_SFR_OPT_ARQ_TIMEOUT_MS
  CFLAGS += -D"CONFIG_GNRC_SIXLOWPAN_SFR_OPT_ARQ_TIMEOUT_MS"=$(SFR_ARQ_TIMEOUT)
endif
ifndef CONFIG_GNRC_SIXLOWPAN_SFR_FRAG_RETRIES
  CFLAGS += -D"CONFIG_GNRC_SIXLOWPAN_SFR_FRAG_RETRIES"=$(SFR_FRAG_RETRIES)
endif
ifndef CONFIG_GNRC_SIXLOWPAN_SFR_DG_RETRIES
  CFLAGS += -D"CONFIG_GNRC_SIXLOWPAN_SFR_DG_RETRIES"=$(SFR_DATAGRAM_RETRIES)
endif
ifndef CONFIG_GNRC_SIXLOWPAN_SFR_ECN_IF_IN_NUM
  CFLAGS += -D"CONFIG_GNRC_SIXLOWPAN_SFR_ECN_IF_IN_NUM"=$(SFR_ECN_NUM)
endif
ifndef CONFIG_GNRC_SIXLOWPAN_SFR_ECN_IF_IN_DEN
  CFLAGS += -D"CONFIG_GNRC_SIXLOWPAN_SFR_ECN_IF_IN_DEN"=$(SFR_ECN_DEN)
endif
ifndef CONFIG_GNRC_SIXLOWPAN_SFR_ECN_IF_OUT_NUM
  CFLAGS += -D"CONFIG_GNRC_SIXLOWPAN_SFR_ECN_IF_OUT_NUM"=$(SFR_ECN_NUM)
endif
ifndef CONFIG_GNRC_SIXLOWPAN_SFR_ECN_IF_OUT_DEN
  CFLAGS += -D"CONFIG_GNRC_SIXLOWPAN_SFR_ECN_IF_OUT_DEN"=$(SFR_ECN_DEN)
endif
ifndef CONFIG_GNRC_SIXLOWPAN_SFR_ECN_FQUEUE_NUM
  CFLAGS += -D"CONFIG_GNRC_SIXLOWPAN_SFR_ECN_FQUEUE_NUM"=$(SFR_ECN_NUM)
endif
ifndef CONFIG_GNRC_SIXLOWPAN_SFR_ECN_FQUEUE_DEN
  CFLAGS += -D"CONFIG_GNRC_SIXLOWPAN_SFR_ECN_FQUEUE_DEN"=$(SFR_ECN_DEN)
endif
ifndef CONFIG_GNRC_IPV6_NIB_NO_RTR_SOL
  CFLAGS += -D"CONFIG_GNRC_IPV6_NIB_NO_RTR_SOL"=1
endif

# Set a custom channel if needed
include $(RIOTMAKE)/default-radio-settings.inc.mk
