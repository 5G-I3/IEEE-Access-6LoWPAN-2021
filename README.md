# Fragment Forwarding in Lossy Networks (IEEE Access)

<!-- TODO badges -->

This repository contains code and documentation to reproduce experimental
results of the paper **"Fragment Forwarding in Lossy Networks"** published in
IEEE Access.

* Martine S. Lenders, Thomas C. Schmidt, Matthias Wählisch, "**Fragment
  Forwarding in Lossy Networks**", in *IEEE Access*, <!-- TODO vol, pp --> 2021
  <!-- TODO DOI -->

##### Abstract

> This paper evaluates four forwarding strategies for fragmented datagrams in the IoT on top of the common CSMA/CA MAC implementation for IEEE 802.15.4:
> hop-wise reassembly, a minimal approach to direct forwarding of fragments, classic end-to-end fragmentation, and direct forwarding utilizing selective fragment recovery.
> Additionally, we evaluate congestion control mechanisms for selective fragment recovery by increasing the feature set of congestion control.
> Direct fragment forwarding and selective fragment recovery are challenged by the lack of forwarding information at subsequent fragments in 6LoWPAN and thus require additional data at the nodes.
> We compare the four approaches in extensive experiments evaluating reliability, end-to-end latency, and memory consumption.
> Our findings indicate  that direct fragment forwarding should be deployed with care, since higher packet transmission rates on the link layer can significantly reduce its reliability, which in turn can even further reduce end-to-end latency because of highly increased link layer retransmissions.
> Selective fragment recovery can compensate this disadvantage but struggles with the same problem underneath, constraining its full potential.
> Congestion control for selective fragment recovery should be chosen so that small congestion windows that are growable together with fragment pacing are used.
> In case of fewer fragments per datagram, pacing is less of a concern, but the congestion window has an upper bound.

[paper-badge]: https://img.shields.io/badge/Paper-IEEE%20Xplore-green

## Repository structure

### [RIOT/][RIOT]
The explicit RIOT version is included as a submodule in this repository
([RIOT]). It is based on the [2021.04 release][2021.04] of RIOT but also
contains all relevant changes to conduct the experiments. The PRs these changes
came from are documented within the git history and the history can be recreated
using the [`cherry-pick-prs.sh`](./cherry-pick-prs.sh) (merge conflicts might
need to be resolved by hand). For more information use

```sh
cd RIOT
git log
```

### [apps/](./apps)
The `apps` directory contains the RIOT applications required for the
experiments, one for the data [sink](./apps/sink) and one for the sources
[sources and forwarders](./apps/source). Please refer to their `README`s for
their usage.

### [scripts/](./scripts)
The `scripts` directory contains scripts for [measuring the testbed as
described in Section IV-A of the paper](./scripts/testbed_measure), to [conduct
the experiments](./scripts/experiment_ctrl), and to plot the results of both
[Section IV. COMPARISON OF FRAGMENT FORWARDING METHODS](./scripts/plots-ff)
and [Section V. EVALUATION OF CONGESTION CONTROL WITH SFR](./scripts/plots-cc).
Please also refer to their respective `README`s for their usage.

To handle the rather specific dependencies of the scripts, we recommend using
[virtualenv]:

```sh
virtualenv -p python3 env
source env/bin/activate
```

[virtualenv]: https://virtualenv.pypa.io/en/latest/

### [results/](./results)
In their default configuration, the scripts will put their result files into the
`results` directory. There, we also  provided the
[NetworkX](./scripts/plots-ff#requirements) [edge
list file](./results/m3-57x9938589e.edgelist.gz) and the two graphical
representations (logical and geographic topology) of that network, for your
convenience.

Usage
-----
You can look into all the code and its documentation to figure everything out,
but the quickest way to start the experiments (given the [provided network for
Section IV. in results/](./results/m3-57x9938589e.edgelist.gz) is bookable in
the IoT-LAB and all requirements on the OS side are fulfilled, see [scripts
README's](./scripts/experiment_ctrl/README.md)) is to just run:

```sh
rm -rf env
virtualenv -p python3 env
source env/bin/activate
pip install -r ./scripts/experiment_ctrl/requirements.txt
# only one of the following two, the `descs.yaml` is newly generated for either
./scripts/experiment_ctrl/create_ff_descs.py    # for Section IV experiments
./scripts/experiment_ctrl/create_cc_descs.py    # for Section V experiments
./scripts/experiment_ctrl/setup_exp.sh
```

[RIOT]: https://github.com/5G-I3/RIOT-public/tree/ieee-access-2021
[2021.04]: https://github.com/RIOT-OS/RIOT/releases/tag/2021.04
