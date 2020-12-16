Sink application
================
This application is for the most part the same application as the [`source`
application](../source) with the only difference that the `RB_SIZE` environment
variable defaults to 16. See the [README](../source/README.md) of that
application for more information.

## Usage
Once the node is up a global address can be configured using

```
ifconfig <if> add <addr>
```

To configure a 6LoWPAN compression context for global addresses use

```
6ctx add <context ID> <prefix> <ltime>
```

Once the experiment's network is set-up this way, the UDP server can be started
by using

```
udp server start <port>
```

and stopped using

```
udp server stop
```
