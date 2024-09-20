"""  oi.DECS driver for Proteox dilution refrigerator systems  """
""" Developed and maintained by Oxford Instruments NanoScience """

from functools import partial
from typing import Any, Union
import time
import subprocess
import platform
import numpy as np

from qcodes.instrument import VisaInstrument
from qcodes.parameters import MultiParameter

from qcodes_contrib_drivers.drivers.OxfordInstruments._decsvisa.src.decs_visa_tools.decs_visa_settings import PORT
from qcodes_contrib_drivers.drivers.OxfordInstruments._decsvisa.src.decs_visa_tools.decs_visa_settings import HOST
from qcodes_contrib_drivers.drivers.OxfordInstruments._decsvisa.src.decs_visa_tools.decs_visa_settings import SHUTDOWN
from qcodes_contrib_drivers.drivers.OxfordInstruments._decsvisa.src.decs_visa_tools.decs_visa_settings import WRITE_DELIM

'''

    Please see the README.md file in this directory for setup instructions.

'''

#############################################
#    Configuration settings required     #
#############################################

# supply the file path from your working directory to the decs_visa.py file
decs_visa_path = "../../src/qcodes_contrib_drivers/drivers/OxfordInstruments/_decsvisa/src/decs_visa.py"

#############################################
#    System configuration settings     #
#############################################

# Does the system have a superconducting
# magnet fitted:
SYSTEM_HAS_MAGNET=True

# If there is a superconducting magnet
# is it fitted with a switch:
MAGNET_HAS_SWITCH=False

# Dual PTR (ProteoxLX) system:
DUAL_PTRS_FITTED=False # not currently used

# Does the system have the < 5mK; > 900 uW
# dilution unit installed
DUAL_TURBO_FITTED=False # not currently used

# Does the system have a 3He flow meter
HE3_FLOW_METER_FITTED=False

#############################################


class MagneticFieldParameters(MultiParameter):
    """
    Parameter for retrieving X, Y, and Z components of the magnetic field. 

    To Retrieve all three parameters via `instrument.Magnetic_Field_Vector()`
    """

    def __init__(
        self, name, instrument, **kwargs: Any
    ) -> None:
        super().__init__(
            name=name,
            instrument=instrument,
            names=("X_Field", "Y_Field", "Z_Field"),
            labels=(
                f"{instrument} X_Field",
                f"{instrument} Y_Field",
                f"{instrument} Z_Field",
            ),
            units=("T", "T", "T"),
            setpoints=((), (), ()),
            shapes=((), (), ()),
            snapshot_get=True,
            snapshot_value=True,
            **kwargs,
        )

    def get_raw(self) -> tuple[float, ...]:
        """
        Gets the values of magnetic field from the instrument
        """
        assert isinstance(self.instrument, oiDECS)
        #Bx, By, Bz = self.instrument._get_field_data()
        return self.instrument._get_field_data()

    def set_raw(self, value) -> None:
        """
        Unused overide of base class function
        """
        print("*** Field cannot be set directly with this function ***")

class MagnetCurrentParameters(MultiParameter):
    """
    Parameter for retrieving X, Y, and Z components of the magnet current. 

    Retrieve all three parameters via `instrument.Magnet_Current_Vector()`
    """

    def __init__(
        self, name, instrument, **kwargs: Any
    ) -> None:
        super().__init__(
            name=name,
            instrument=instrument,
            names=("X_Current", "Y_Current", "Z_Current"),
            labels=(
                f"{instrument} X_Current",
                f"{instrument} Y_Current",
                f"{instrument} Z_Current",
            ),
            units=("A", "A", "A"),
            setpoints=((), (), ()),
            shapes=((), (), ()),
            snapshot_get=True,
            snapshot_value=True,
            **kwargs,
        )

    def get_raw(self) -> tuple[float, ...]:
        """
        Gets the values of magnet current from the instrument
        """
        assert isinstance(self.instrument, oiDECS)
        #Ix, Iy, Iz = self.instrument._get_field_current_data()
        return self.instrument._get_field_current_data()

    def set_raw(self, value) -> None:
        """
        Unused overide of base class function
        """
        print("*** Current cannot be set directly with this function ***")

class oiDECS(VisaInstrument):
    """ Main implementation of the oi.DECS driver """
    def __init__(self, name, **kwargs):

        running_on = platform.platform()
        if running_on.startswith("Windows"):
            print(f"Running on {running_on} - start subprocess without PIPEd output")
            subprocess.Popen(["python", decs_visa_path])
        else:
            print(f"Running on {running_on} - start subprocess with PIPEd output")
            subprocess.Popen(["python3", decs_visa_path], stdout=subprocess.PIPE)

        time.sleep(1)

        super().__init__(name, f'TCPIP::{HOST}::{PORT}::SOCKET', terminator=WRITE_DELIM, **kwargs)

        self.add_parameter(
            "PT1_Head_Temperature",
            unit="K",
            label=name,
            get_cmd="get_PT1_T1",
            get_parser=float
        )

        self.add_parameter(
            "PT1_Plate_Temperature",
            unit="K",
            label=name,
            get_cmd="get_DR1_T",
            get_parser=float
        )

        self.add_parameter(
            "PT2_Head_Temperature",
            unit="K",
            label=name,
            get_cmd="get_PT2_T1",
            get_parser=float
        )

        self.add_parameter(
            "PT2_Plate_Temperature",
            unit="K",
            label=name,
            get_cmd="get_DR2_T",
            get_parser=float
        )

        self.add_parameter(
            "Sorb_Temperature",
            unit="K",
            label=name,
            get_cmd="get_SRB_T",
            get_parser=float
        )

        self.add_parameter(
            "Still_Plate_Temperature",
            unit="K",
            label=name,
            get_cmd="get_STILL_T",
            get_parser=float
        )

        self.add_parameter(
            "Still_Heater_Power",
            unit="W",
            label=name,
            get_cmd="get_STILL_H",
            set_cmd=partial(self._param_setter, "set_STILL_H"),
            get_parser=float
        )

        self.add_parameter(
            "Cold_Plate_Temperature",
            unit="K",
            label=name,
            get_cmd="get_CP_T",
            get_parser=float
        )

        self.add_parameter(
            "Mixing_Chamber_Temperature",
            unit="K",
            label=name,
            get_cmd="get_MC_T",
            set_cmd=partial(self._param_setter, "set_MC_T"),
            get_parser=float
        )

        self.add_parameter(
            "Mixing_Chamber_Temperature_Target",
            unit="K",
            label=name,
            get_cmd="get_MC_T_SP",
            set_cmd=partial(self._param_setter, "set_MC_T"),
            get_parser=float
        )

        self.add_parameter(
            "Mixing_Chamber_Heater_Power",
            unit="W",
            label=name,
            get_cmd="get_MC_H",
            set_cmd=partial(self._param_setter, "set_MC_H"),
            get_parser=float
        )

        self.add_parameter(
            "Sample_Temperature",
            unit="K",
            label=name,
            get_cmd="get_SAMPLE_T",
            set_cmd=partial(self._param_setter, "set_SAMPLE_T"),
            get_parser=float
        )

        self.add_parameter(
            "OVC_Pressure",
            unit="Pa",
            label=name,
            get_cmd="get_OVC_P",
            get_parser=float
        )

        self.add_parameter(
            "P1_Pressure",
            unit="Pa",
            label=name,
            get_cmd="get_P1_P",
            get_parser=float
        )

        self.add_parameter(
            "P2_Pressure",
            unit="Pa",
            label=name,
            get_cmd="get_P2_P",
            get_parser=float
        )

        self.add_parameter(
            "P3_Pressure",
            unit="Pa",
            label=name,
            get_cmd="get_P3_P",
            get_parser=float
        )

        self.add_parameter(
            "P4_Pressure",
            unit="Pa",
            label=name,
            get_cmd="get_P4_P",
            get_parser=float
        )

        self.add_parameter(
            "P5_Pressure",
            unit="Pa",
            label=name,
            get_cmd="get_P5_P",
            get_parser=float
        )

        self.add_parameter(
            "P6_Pressure",
            unit="Pa",
            label=name,
            get_cmd="get_P6_P",
            get_parser=float
        )

        if HE3_FLOW_METER_FITTED:
            self.add_parameter(
                "He3_Flow",
                unit="mol/s",
                label=name,
                get_cmd="get_3He_F",
                get_parser=float
            )

        if SYSTEM_HAS_MAGNET:
            self.add_parameter(
                "Magnet_Temperature",
                unit="K",
                label=name,
                get_cmd="get_MAG_T",
                get_parser=float
            )

            self.add_parameter(
                "Magnet_State",
                label=name,
                get_cmd="get_MAG_STATE",
                get_parser=str,
                val_mapping={'Holding Not Persistent': '0',
                            'Holding Persistent': '10',
                            'Ramping Magnetic Field': '20',
                            'Ramping Power Supply Output Current': '30',
                            'Opening Superconducting Switches': '40',
                            'Closing Superconducting Switches': '50',
                            'Magnet Safety Non-Persistent': '60',
                            'Magnet Safety Persistent': '70'
                            },
            )

            self.add_parameter(
                name = "Magnetic_Field_Vector",
                parameter_class=MagneticFieldParameters,
            )

            self.add_parameter(
                name = "Magnet_Current_Vector",
                parameter_class=MagnetCurrentParameters,
            )

            if MAGNET_HAS_SWITCH:
                self.add_parameter(
                    "Switch_State",
                    label=name,
                    get_cmd="get_SWZ_STATE",
                    get_parser=float,
                    val_mapping={'OPEN': 1.0, 'CLOSED': 0.0}
                )

        self.connect_message()

    def publish(self, msg, msg_group):
        """Function to publish an 'event'"""
        self._param_setter("PUBLISH", f"{msg},{msg_group}")

    def _get_field_data(self):
        B_str = self.ask("get_MAG_VEC")
        B_array = B_str.split(',')
        return float(B_array[0]), float(B_array[1]), float(B_array[2])
    
    def _get_field_current_data(self):
        I_str = self.ask("get_MAG_CURR_VEC")
        I_array = I_str.split(',')
        return float(I_array[0]), float(I_array[1]), float(I_array[2])

    def mixing_chamber_heater_off(self):
        """Function to turn off MC heater"""
        self._param_setter('set_MC_H_OFF', 0)

    def still_heater_off(self):
        """Function to turn off still heater"""
        self._param_setter('set_STILL_H_OFF', 0)

    def set_magnet_target(self, coord, x, y, z, sweep_mode, sweep_rate, persist_on_completion):
        """Function to set field vector target"""
        match sweep_mode:
            case 'RATE':
                param = [coord, x, y, z, 20, sweep_rate, persist_on_completion]
                self._param_setter('set_MAG_TARGET', param)
            case 'TIME':
                param = [coord, x, y, z, 10, sweep_rate, persist_on_completion]
                self._param_setter('set_MAG_TARGET', param)
            case 'ASAP':
                param = [coord, x, y, z, 0, sweep_rate, persist_on_completion]
                self._param_setter('set_MAG_TARGET', param)
            case _:
                print('Incorrect inputs.')
                print('[x,y,z,mode,rate,persist_on_completion]')


    def set_output_current_target(self, x, y, z, sweep_mode, sweep_rate, persist_on_completion):
        """Function to set current vector target"""
        match sweep_mode:
            case 'RATE':
                param = [x, y, z, 20, sweep_rate, persist_on_completion]
                self._param_setter('set_CURR_TARGET', param)
            case 'TIME':
                param = [x, y, z, 10, sweep_rate, persist_on_completion]
                self._param_setter('set_CURR_TARGET', param)
            case 'ASAP':
                param = [x, y, z, 0, sweep_rate, persist_on_completion]
                self._param_setter('set_CURR_TARGET', param)
            case _:
                print('Incorrect inputs.')
                print('[x,y,z,mode,rate,persist_on_completion]')

    def set_magnet_state(self, state):
        """Function to set VRM state target"""
        match state:
            case 0:
                self._param_setter('set_MAG_STATE', state)
                print('Holding Field')
            case 10:
                self._param_setter('set_MAG_STATE', state)
                print('Entering Persistent Mode')
            case 20:
                self._param_setter('set_MAG_STATE', state)
                print('Leaving Persistent Mode')
            case 30:
                self._param_setter('set_MAG_STATE', state)
                print('Sweeping Field')
            case 40:
                self._param_setter('set_MAG_STATE', state)
                print('Sweeping PSU Output')
            case _:
                print("**NB** Demandable states are:")
                print("0 - Hold, 10 - Enter Persistent Mode")
                print("20 - Leave Persistent Mode, 30 - Sweep Field, 40 - Sweep PSU Output")

    def sweep_field(self):
        """VRM utility function"""
        self.set_magnet_state(30)

    def sweep_psu_output(self):
        """VRM utility function"""
        self.set_magnet_state(40)

    def enter_persistent_mode(self):
        """VRM utility function"""
        self.set_magnet_state(10)

    def leave_persistent_mode(self):
        """VRM utility function"""
        self.set_magnet_state(20)

    def hold_field(self):
        """VRM utility function"""
        self.set_magnet_state(0)

    def open_switch(self):
        """VRM utility function"""
        self.set_magnet_state(20)

    def close_switch(self):
        """VRM utility function"""
        self.set_magnet_state(10)

    def sweep_small_field_step(self, coord):
        '''
        Function sweeps a single VRM group.
        Used for changing the field by values < 100 mA.
        '''
        # sweep VRM group
        self.sweep_field()
        # wait until sweep failed
        time.sleep(2)
        status = self.Magnet_State()
        while status != 'Holding Not Persistent':
            status = self.Magnet_State()
            time.sleep(1)
        # sweep X, Y or Z group of VRM
        if coord=='X':
            self._param_setter('set_MAG_X_STATE', 10)
        elif coord=='Y':
            self._param_setter('set_MAG_Y_STATE', 10)
        elif coord=='Z':
            self._param_setter('set_MAG_Z_STATE', 10)

    def wait_until_field_stable(self):
        """VRM utility function"""
        time.sleep(2)
        status = self.Magnet_State()
        while status != 'Holding Not Persistent':
            status = self.Magnet_State()
            time.sleep(1)
        print(f'Status: {self.Magnet_State()}.')

    def wait_until_field_persistent(self):
        """VRM utility function"""
        status = self.Magnet_State()
        while status != 'Holding Persistent':
            status = self.Magnet_State()
            time.sleep(1)
        print(f'Status: {self.Magnet_State()}.')

    def wait_until_field_depersisted(self):
        """VRM utility function"""
        status = self.Magnet_State()
        while status != 'Holding Not Persistent':
            status = self.Magnet_State()
            time.sleep(1)
        print(f'Status: {self.Magnet_State()}.')

    def wait_until_temperature_stable_std_control(self, stable_mean, stable_std, time_between_readings):
        """
        Mixing chamber temperature control utility function

        Takes a moving average of 30 temperature readings and finds the mean and the std of the last 30 readings,
        until the difference between the mean and target value is below 'stable_mean' and the standard deviation is below 'stable_std'.

        Args:
            stable_mean: float - difference between the mean and target value to be achieved by the last 30 temperature readings
            stable_std: float - standard deviation to be achieved by the last 30 temperature readings
            time_between_readings: float - time between taking temperature readings
        
        """
        target_temp = self.Mixing_Chamber_Temperature_Target()

        print(f'Waiting for temperature to stablilise at {target_temp} K.')
        
        #take 30 temperature readings 
        t1 = time.time()
        t_array = np.zeros(30)
        for n in range(0,30):
            time.sleep(time_between_readings)
            temp = self.Mixing_Chamber_Temperature()
            t_array[n] = float(temp)
            
        stab = False
        while stab is False:
            time.sleep(time_between_readings)
            temp = self.Mixing_Chamber_Temperature()
            t_array = np.append(t_array, float(temp))

            t_array = t_array[1:]
            s = np.std(t_array)
            m = np.abs(np.mean(t_array) - target_temp)
            
            if (s < stable_std) and (m < stable_mean):
                stab = True
                
        t2 = time.time()
        tt = t2-t1
        print(f'Temperature = {t_array[-1]} K')
        print(f'Temperature stable after {int(tt)} seconds. (Mean-Target = {m} K, StdDev = {s} K)')

    def ask(self, cmd: str) -> str:
        """
        Args:
            cmd: the command to send to the instrument
        """
        resp = self.visa_handle.query(cmd)

        return resp

    def _param_setter(self, set_cmd: str, value: Union[float, str]) -> None:
        """
        General setter function for parameters

        Args:
            set_cmd: raw string for the command, e.g. 'set_target_temperature'
        """
        dressed_cmd = f"{set_cmd}:{value}"
        # the instrument always provides a response
        # even when issuing a 'set' command.
        # Hence ask rather than write
        self.ask(dressed_cmd)

    def close(self) -> None:
        # Kill off the WAMP and socket connections
        self.write(SHUTDOWN)
        return super().close()

