# Scripts to process and plot experiment results for Section V

## Overview

The scripts in this directory serve the processing and plotting of the
experiment results as described in Section V. EVALUATION OF CONGESTION CONTROL
WITH SFR.

`parse_results.py` transform the logs from the [experiment
runs](../experiment_ctrl) into easier to work with CSV files.

`plot_pdr.py` to generate a bar plot of the PDRs by fragment multiplicity.

`plot_cong.py` to generate the congestion event plots from the paper for all
available transactions.

`plot_size.py` to generate the memory size comparison bar plot from the paper.


## Requirements
The scripts assume they are run with Python 3.

The following python packages are required (version numbers indicate tested
versions):

- `matplotlib` v3.3
- `networkx` v2.5
- `scipy` v1.6

The required packages are listed in `requirements.txt` and can be installed
using

```sh
pip3 install -r requirements.txt
```

Depending on your operating system and if you are in a `virtualenv` you might
need to install `tkinter` to show the plots during script execution. On Ubuntu
you can do this with

```sh
sudo apt-get install python3-tk
```

## Usage

### `parse_results.py`
This scripts takes the logs from your experiments runs and transforms them into
easy to digest CSV files. A number of files for each log are generated.

- A `.times.csv` which contains a line for each UDP packet sent during the
  experiment, logging its send time and reception time during the experiment and
  also some additional meta-data. It is used to generate the Packet Delivery
  Ratio and Source-to-sink Latency plots.
- A `.stats.csv` which contains all the statistical data gathered after the end
  of an experiment run. This includes: the number of failed transmissions, the
  packet buffer usage, and the number instances the (virtual) reassembly buffer
  was f
- A `.cong.csv` for each node of the experiment which contains all the
  congestion events on that node. The content is logging the relative time the
  congestion event happened, starting from the first congestion event, the type
  of the event, the tag of the fragment causing the event, the resulting
  congestion window, the resulting inter-frame gap, and usage of both the queues
  observed for ECN as well as the fragment buffer.

The script takes at least one ID of a network (see generated `edgelist.gz` files
in `results/` as argument). See

```sh
./parse_results.py -h
```

for more information.

#### Environment variables
- `DATA_PATH`: (default: `./../../results`) Path where the logs to consider are
  stored and output path.

### `plot_pdr.py`
This script plots a PDR bar chart generated from the CSV files created with
[`parse_results.py`](#parse_resultspy).

It takes no required arguments, see

```sh
./plot_pdr.py -h
```

for more information.

#### Environment variables
- `DATA_PATH`: (default: `./../../results`) Path where the logs to consider are
  stored and output path.

### `plot_cong.py`
This script plots a congestion event plot generated from the CSV files created
with [`parse_results.py`](#parse_resultspy).

It takes the `node` on which the events happened and the UDP payload `data_len`
for which to analyze the congestion events as arguments. See

```sh
./plot_cong.py -h
```

for more information.

**Attention:** This generates a lot of output files.

#### Environment variables
- `DATA_PATH`: (default: `./../../results`) Output path for the plots.

### `plot_size.py`
This script plots a memory usage bar chart generated from static data within the
script.

It takes no required parameters, see

```sh
./plot_size.py -h
```

for more information.

#### Environment variables
- `DATA_PATH`: (default: `./../../results`) Path where the logs to consider are
  stored and output path.
