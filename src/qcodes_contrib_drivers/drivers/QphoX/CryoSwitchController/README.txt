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

############### Usage example: ###############

# load driver
from qcodes_contrib_drivers.drivers.QphoX.CryoSwitchController.qcodes_driver import CryoSwitchControllerDriver

# connect to the switch
switchcontroller = CryoSwitchControllerDriver('switchcontroller')
switchcontroller.start()

# set a switch model
switchcontroller.switch_model('CRYO')

# set pulse parameters
switchcontroller.output_voltage(15)
switchcontroller.OCP_value(100)
switchcontroller.pulse_duration(8)

# get all switch states based on the "status.json"
# there is no direct way to see the state of the switch
switchcontroller.get_switches_state()

# connect contact 3 of port A
switchcontroller.channels.A.connect(3)

# smart switch to contact 5 (and automatically disconnect from 3)
# there is no software or hardware control to ensure that only contact is connected
# once the pulse parameters are reliable, I recommend only using the "smart_connect" function
switchcontroller.channels.A.smart_connect(5)

# get an active contact
switchcontroller.channels.A.active_contact()

# disconnect from contact 5
data = switchcontroller.channels.A.disconnect(5)

# plot a current transient for the "disconnect" action
plt.plot(data)

# get an active contact (should return 0 when nothing is connected)
switchcontroller.channels.A.active_contact()

# close the switchcontroller instrument
switchcontroller.close()
