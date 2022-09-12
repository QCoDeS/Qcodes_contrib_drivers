# QDevil tests

This directory tests the QDevil QDAC-II driver.

## Linux/MacOS

### Run tests

Simulated instrument:

    $ source venv/bin/activate
    $ pytest qcodes_contrib_drivers/tests/QDevil/test_sim_qdac2_*.py

To silence warnings, use `-W ignore::DeprecationWarning`.

Real instrument:

    $ source venv/bin/activate
    $ export QDAC_IP_ADDR=192.168.8.153
    $ pytest qcodes_contrib_drivers/tests/QDevil/test_real_qdac2_*.py

Static types:

    $ mypy --no-incremental qcodes_contrib_drivers/drivers/QDevil/QDAC2.py

### One-time setup

    $ python3 -m venv venv
    $ source venv/bin/activate
    $ pip install --upgrade pip
    $ pip install -e .[test]
    $ pip install pyvisa-py==0.5.2
