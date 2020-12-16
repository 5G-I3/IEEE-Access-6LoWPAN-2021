# Source application
This application implements both source and sink for the experiments for the
paper. It starts as an IPv6 router. There is also a dedicated
[`sink` application](../sink), but the only difference to this application is
that the environment variable `RB_SIZE` defaults to 16.

## Compile-time configuration
There are some compile-time configurations that are exposed to the via
environment variables

- `MODE`: (default: `hwr`) Can be either `hwr` (for hop-wise reassembly),
  `ff` (for fragment forwarding), `e2e` (for end-to-end fragmentation), or
  `sfr` (for selective fragment recovery)
- `CONJURE_IMPL`: (optional) Sets the congestion control for `sfr`. Can either
  be `congure_sfr` (for congestion control as proposed in Appendix C of [RFC
  8931]), `congure_reno` (for congestion control as proposed in [RFC 5681]),
  `congure_abe` (for congestion control as proposed in [RFC 8511]), or
  `congure_quic` (for congestion control as proposed in [RFC 9002]). If unset,
  `sfr` will be compiled without any congestion control and the window size will
  just be set to `SFR_INIT_WIN_SIZE`.
- `APP_LOG`: (default: 0 without `CONGURE_IMPL`, 1 with `CONGURE_IMPL`) Log
  congestion events.
- `PKTBUF_SIZE`: (default: 6144 without `CONGURE_IMPL`, 40960 with
  `CONGURE_IMPL`) Packet buffer size.
- `NETIF_PKTQ_POOL_SIZE`: (default: 64 without `CONGURE_IMPL`, 8 with
  `CONGURE_IMPL`) Network interface packet queue pool size
- `FB_SIZE`: (default: 64 without `CONGURE_IMPL`, 4 with `CONGURE_IMPL`) Fragmentation buffer size
- `RB_SIZE`: (default: 1) The size of the forwarder's reassembly buffer
- `RB_TIMEOUT`: (default: 10000000) Reassembly timeout in microseconds
- `RB_DEL_TIMER`: (default: 250) Deletion timer for reassembly buffer entry
  after datagram completion.
- `VRB_SIZE`: (default: 16) The size of the virtual reassembly buffer (with
  modes `ff` and `sfr`)
  reassembly buffer when full)
- `SFR_INIT_WIN_SIZE`: (default: 2) Window size for mode `sfr`. With
  `CONGURE_IMPL` set, this will be the initial window size used by the
  congestion control mechanism, with `CONGURE_IMPL` unset, this will be the
  window size throughout the whole experiment as well as the maximum window size
  (for allocation).
- `SFR_INTER_FRAME_GAP`: (default: 170000) Inter-frame gap in microseconds for
  mode `sfr`
- `SFR_ARQ_TIMEOUT`: (default: 2500) Retry timeout in milliseconds for mode
  `sfr`
- `SFR_FRAG_RETRIES`: (default: 4) Number of retries for mode `sfr`
- `SFR_DATAGRAM_RETRIES`: (default: 0) Number of datagram retries for mode `sfr`
- `SFR_ECN_NUM`: (default: 1) Numerator for ECN threshold fraction when
  `CONGURE_IMPL` is set.
- `SFR_ECN_DEN`: (default: 2) Denominator for ECN threshold fraction when
  `CONGURE_IMPL` is set.
- `UDP_COUNT`: (default: 200) Number of UDP packets the `udp send` command
  sends.

## Usage
Once the node is up a global address can be configured using

```
ifconfig <if> add <addr>
```

The MTU for IPv6 can be changed (for `e2e`) using

```
ifconfig <if> set mtu <mtu>
```

The default route to upstream can be configured using

```
nib route <if> default <next-hop link-local addr>
```

To configure a 6LoWPAN compression context for global addresses use

```
6ctx add <context ID> <prefix> <ltime>
```

Once the experiment's network is set-up this way, the sending of periodic UDP
packets can be started by using

```
udp send <sink global address>:<port> <payload length> <delay>
```

With `<delay>` being the mean in milliseconds of the randomized delay.
The delay is uniquely distributed between 0.5×`<delay>` and 1.5×`<delay>`.
`<payload length>` may not be 0 as the bytes of the payload are used to identify
the packets at the sink.

[RFC 5681]: https://tools.ietf.org/html/rfc5681
[RFC 8511]: https://tools.ietf.org/html/rfc8511
[RFC 8931]: https://tools.ietf.org/html/rfc8931
[RFC 9002]: https://tools.ietf.org/html/rfc9002
