# Scripts to construct network and conduct experiment

## Overview

The scripts in this directory serve the experiment setup and conduction.

`construct_network.py` constructs a network of up to 50 nodes (may be less due
to bookings within the selected site).

## Requirements
The scripts assume they are run with Python 3.

The following python packages are required (version numbers indicate tested
versions):

- `iotlab_controller` (see https://github.com/miri64/iotlab_controller)
- `networkx` v2.3
- `matplotlib` v3.1
- `scipy` v1.3

The required packages are listed in `requirements.txt` and can be installed
using

```sh
pip3 install -r requirements.txt
```

You must also configure your IoT-LAB credentials using `iotlab-auth` which is
provided by the `iotlabcli` python package (which is automatically installed
with `iotlab_controller`). See

```sh
iotlab-auth -h
```

for further instructions.

## Usage

### `construct_network.py`

This script constructs a sink-oriented network using predefined values. See

```sh
./construct_network.py -h
```

for further information. The resulting `edgelist.gz` file will be stored in
`./../../results`

#### Environment variables

- `DATA_PATH`: (default: `./../../results`) Path to store the edge list file in
