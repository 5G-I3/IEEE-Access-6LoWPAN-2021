# Fragment Forwarding in Lossy Networks

Code and documentation to reproduce our experiment results.

## Code

The explicit RIOT version is included as a submodule in this repository
([RIOT]). It is based on the 2021.04 release of RIOT but also contains all
relevant changes to conduct the experiments. The PRs these changes came from are
documented within the git history and the history can be recreated using the
[`cherry-pick-prs.sh`](./cherry-pick-prs.sh) (merge conflicts might need to be
resolved by hand). For more information use

```sh
cd RIOT
git log
```

The `apps` directory contains the RIOT applications required for the
experiments, one for the data [sink](./apps/sink) and one for the sources
[sources and forwarders](./apps/source). Please refer to their `README`s for
their usage.

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

Documentation
-------------
TODO: link paper if it is accepted

[RIOT]: https://github.com/5G-I3/RIOT-public/tree/ieee-access-2021
