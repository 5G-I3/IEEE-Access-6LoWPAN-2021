# Scripts to process and plot experiment results

## Overview

The scripts in this directory serve the processing and plotting of the
experiment results

`parse_results.py` transform the logs from the [experiment
runs](../experiment_ctrl) into easier to work with CSV files.

`plot_results.py` then takes these CSV files and generates the plots you can see
in the paper from them.

## Requirements
The scripts assume they are run with Python 3.

The following python packages are required (version numbers indicate tested
versions):

- `matplotlib` v3.1
- `networkx` v2.3

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
easy to digest CSV files. Two files for each log are generated:

- A `.times.csv` which contains a line for each UDP packet sent during the
  experiment, logging its send time and reception time during the experiment and
  also some additional meta-data. It is used to generate the Packet Delivery
  Ratio and Source-to-sink Latency plots.
- A `.stats.csv` which contains all the statistical data gathered after the end
  of an experiment run. This includes: the number of failed transmissions, the
  packet buffer usage, and the number instances the (virtual) reassembly buffer
  was full.

The script takes no argument. Just execute it with

```sh
./parse_results.py
``

#### Environment variables
- `DATA_PATH`: (default: `./../../results`) Path where the logs to consider are
  stored.
- `GLOBAL_PREFIX` (default: `2001:db8:0:1:`) Global IPv6 address prefix used
  during experiments (has to be of length 64 bits)

### `plot_results.py`
This script generates various plots generated from the CSV files created with
[`parse_results.py`][#parse_resultspy]. It also tries to call `parse_results`
in case the CSV files for a log don't exist yet (on-the-fly CSV generation).
Because of that it is recommended to re-run `parse_results.py` after you
execute `plot_results.py` while new logs are still generated to incorparate data
added to the logs during your execution of `plot_results.py`.

For more information on the script, see

```sh
./plot_results.py
```

#### Environment variables
- `DATA_PATH`: (default: `./../../results`) Path where the logs to consider are
  stored.

For on-the-fly CSV generation you also can set the environment variables used by
[`parse_results.py`][#parse_results.py]
