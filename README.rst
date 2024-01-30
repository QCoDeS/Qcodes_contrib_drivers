######################
QCoDeS contrib drivers
######################

This repository contains QCoDeS instrument drivers developed by members of the QCoDeS community.
These drivers are not supported by the QCoDeS developers but instead supported on a best effort basis
by the developers of the individual drivers.

Default branch is now main
##########################

The default branch in qcodes_contrib_drivers has been remamed to main.
If you are working with a local clone of qcodes_contrib_drivers you should update it as follows.

* Run ``git fetch origin`` and ``git checkout main``
* Run ``git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/main`` to update your HEAD reference.

Getting started
###############

Prerequisites
*************

The drivers in this repository work with and heavily depend on QCoDeS. Start by installing `QCoDeS <https://github.com/QCoDeS/Qcodes>`_ .

Installation
************

Install the contrib drivers with ``pip``

.. code-block::

  pip install qcodes_contrib_drivers

Drivers documentation
*********************

The documentations of the drivers in this repository can be read `here <https://qcodes.github.io/Qcodes_contrib_drivers>`_.

Contributing
############

This repository is open for contribution of new drivers,
as well as improvements to existing drivers. Each driver should
contain an implementation of the driver and a Jupyter notebook showing how the
driver should be used. In addition we strongly encourage writing tests for the drivers.
An introduction for writing tests with PyVISA-sim can be found in the QCoDeS documentation linked
below.

Drivers are expected to be added to ``qcodes_contrib_drivers/drivers/MakerOfInstrument/`` folder
while examples should be added to the ``docs/examples`` folder and tests placed in the
``qcodes_contrib_drivers/tests/MakerOfInstrument`` folder. Please follow naming conventions for
consistency.

For general information about writing drivers and how to write tests refer to the `QCoDeS documentation <http://microsoft.github.io/Qcodes/>`_.
Especially the examples `here <https://microsoft.github.io/Qcodes/examples/index.html#writing-drivers>`__
are useful.

LICENSE
#######

QCoDeS-Contrib-drivers is licensed under the MIT license except the ``Tektronix AWG520`` and
``Tektronix Keithley 2700`` drivers which are licensed under the GPL 2 or later License.
