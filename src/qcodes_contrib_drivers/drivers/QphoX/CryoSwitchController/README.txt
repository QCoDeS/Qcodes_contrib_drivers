The QCoDeS driver is a wrapper around the QphoX SDK retreived on 2024-02-23
from https://github.com/QphoX/CryoSwitchController

The driver is functional (at least) after pulfiling the following requirements:

cycler=0.11.0
kiwisolver==1.3.1
matplotlib~=3.8.3
numpy~=1.26.4
Pillow~=10.2.0
pyparsing==3.0.9
pyserial==3.5
python-dateutil==2.8.2
six==1.16.0

These requirements originate from QphoX SDK requirements file, and relaxed to be compatible with python 3.11. As-written, the requirements are likely much more restrictive than neccessary.

Wrapper written by Filip Malinowski
filip.malinowski@tno.nl.