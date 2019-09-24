This repository contains drivers developed by members of the QCoDeS community.
These drivers are not supported by the QCoDeS developers but supported on a best effort basis
by the developers of the individual drivers.

How to contribute a driver:

This repository is open for contribution of new drivers. Each driver should
contain an implementation of the driver and a Jupyter notebook showing how the
drivers should be used. In addition we strongly encourage writing tests for the drivers.
An intruduction for writing tests with PyVISA-sim can be found in the QCoDeS documentation linked
below.

Drivers are expected to be added to ``qcodes_contrib_drivers/drivers/MakeofInstrument/`` folder
while examples should be added to the ``docs/examples`` folder and tests placed in the
``qcodes_contrib_drivers/tests`` folder.

For general information about writing drivers and how to write tests refer to the QCoDeS documentation.
Especially the examples `here <https://qcodes.github.io/Qcodes/examples/index.html#writing-drivers>`__
are useful.
