# CryoSwitchController

## Project structure

## Getting started

This repository holds the QP-CryoSwitchController compatible software.


## Installation
- Clone the repo
- Run: ```pip install -r requirements.txt```
- Browse the CryoSwitchController.py file for library implementation


## Library Usage
A basic implementation of the CryoSwitchController class can be done with the following functions:
- start()

        Input: None
        Default: None
        Enables the voltage rails, voltage converter and output channels

- set_output_voltage(Vout)

        Input: Desired output voltage (Vout)
        Default: 5V
        Sets the converter voltage to Vout. The output stage later utilizes the converter voltage to generate the positive/negative pulses.

- set_pulse_duration_ms(ms_duration)

        Input: Pulse width duration in milliseconds (ms_duration).
        Default: 10ms.
        Sets the output pulse (positive/negative) duration in milliseconds.

- connect(port, contact)

        Input: Corresponding port and contact to be connected. Port={A, B, C, D}, contact={1,...,6}
        Default: None.
        Connects the specified contact of the specified port (switch).

- disconnect(port, contact)

        Input: Corresponding port and contact to be disconnected. Port={A, B, C, D}, contact={1,...,6}
        Default: None.
        Disconnects the specified contact of the specified port (switch).



## Advanced functions

- enable_OCP()

        Input: None
        Default: None.
        Enables the overcurrent protection.


- set_OCP_mA(OCP_value)

        Input: Overcurrent protection trigger value (OCP_value).
        Default: 100mA.
        Sets the overcurrent protection to the specified value.

- enable_chopping()

        Input: None.
        Default: None.
        Enables the chopping function. When an overcurrent condition occurs, the controller will 'chop' the excess current instead of disabling the output. Please refer to the installation guide for further information.

- disable_chopping()

        Input: None.
        Default: None.
        Disables the chopping function. When an overcurrent condition occurs, the controller will disable the output voltage. Please refer to the installation guide for further information.
