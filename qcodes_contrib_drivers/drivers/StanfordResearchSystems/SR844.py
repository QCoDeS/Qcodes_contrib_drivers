from functools import partial
import numpy as np
from typing import Any, Iterable, Tuple, Union

from qcodes import VisaInstrument
from qcodes.instrument.parameter import ArrayParameter, Parameter, ParamRawDataType, ParameterWithSetpoints
from qcodes.utils.validators import Numbers, Enum, Strings, Arrays

class ChannelTrace(ParameterWithSetpoints):
    """
    Parameter class for the two channel buffers
    """

    def __init__(self, name: str, channel: int, **kwargs: Any) -> None:
        """
        Args:
            name: The name of the parameter
            channel: The relevant channel (1 or 2). The name should
                match this.
        """
        super().__init__(name, **kwargs)

        self._valid_channels = (1, 2)

        if channel not in self._valid_channels:
            raise ValueError('Invalid channel specifier. SR844 only has '
                             'channels 1 and 2.')

        if not isinstance(self.root_instrument, SR844):
            raise ValueError('Invalid parent instrument. ChannelTrace '
                             'can only live on an SR844.')

        self.channel = channel
        self.update_unit()

    def update_unit(self) -> None:
        assert isinstance(self.root_instrument, SR844)
        params = self.root_instrument.parameters
        if params["ratio_mode"].get() != "none":
            self.unit = "%"
        else:
            disp = params[f"ch{self.channel}_display"].get()
            if "Phase" in disp:
                self.unit = "deg"
            elif "dBm" in disp:
                self.unit = "dBm"
            else:
                self.unit = "V"


    def get_raw(self) -> ParamRawDataType:
        """
        Get command. Returns numpy array
        """
        assert isinstance(self.root_instrument, SR844)
        N = self.root_instrument.buffer_npts()
        if N == 0:
            raise ValueError('No points stored in SR844 data buffer.'
                             ' Cannot poll anything.')

        # poll raw binary data
        self.root_instrument.write(f'TRCL ? {self.channel}, 0, {N}')
        rawdata = self.root_instrument.visa_handle.read_raw()

        # parse it
        realdata = np.frombuffer(rawdata, dtype="<i2")
        numbers = realdata[::2] * 2.0 ** (realdata[1::2] - 124)
        return numbers
    def poll_raw_binary_data(self) -> "<i2":
        self.root_instrument.write(f'TRCL ? {self.channel}, 0, {N}')
        return self.root_instrument.visa_handle.read_raw()

class ChannelBuffer(ArrayParameter):
    """
    Parameter class for the two channel buffers

    Currently always returns the entire buffer
    TODO (WilliamHPNielsen): Make it possible to query parts of the buffer.
    The instrument natively supports this in its TRCL call.
    """

    def __init__(self, name: str, instrument: "SR844", channel: int) -> None:
        """
        Args:
            name: The name of the parameter
            instrument: The parent instrument
            channel: The relevant channel (1 or 2). The name should 
                should match this.          # how should the name match the channel?
        """
        self._valid_channels = (1, 2)

        if channel not in self._valid_channels:
            raise ValueError('Invalid channel specifier. SR844 only has '
                             'channels 1 and 2.')

        if not isinstance(instrument, SR844):
            raise ValueError(
                "Invalid parent instrument. ChannelBuffer " " can only live on an SR844."
            )

        super().__init__(
            name,
            shape=(1,),  # dummy initial shape
            unit="V",  # dummy initial unit
            setpoint_names=("Time",),
            setpoint_labels=("Time",),
            setpoint_units=("s",),
            docstring="Holds an acquired (part of the) " "data buffer of one channel.",
        )

        self.channel = channel
        self._instrument = instrument


    def prepare_buffer_readout(self) -> None:
        """
        Function to generate the setpoints for the channel buffer and
        get the right units
        """
        assert isinstance(self._instrument, SR844)
        N = self._instrument.buffer_npts()  # problem if this is zero?
        # TODO (WilliamHPNielsen): what if SR was changed during acquisition?
        SR = self._instrument.buffer_SR()
        if SR == "Trigger":
            self.setpoint_units = ("",)
            self.setpoint_names = ("trig_events",)
            self.setpoint_labels = ("Trigger event number",)
            self.setpoints = (tuple(np.arange(0, N)),)
        else:
            dt = 1 / SR
            self.setpoint_units = ("s",)
            self.setpoint_names = ("Time",)
            self.setpoint_labels = ("Time",)
            self.setpoints = (tuple(np.linspace(0, N * dt, N)),)

        self.shape = (N,)

        params = self._instrument.parameters
        # YES, it should be: comparing to the string 'none' and not
        # the None literal
        if params["ratio_mode"].get() != "none":
            self.unit = "%"
        else:
            disp = params[f"ch{self.channel}_display"].get()
            if disp == "Phase":
                self.unit = "deg"
            elif "dBm" in disp:
                self.unit = "dBm"
            else:
                self.unit = "V"

        if self.channel == 1:
            self._instrument._buffer1_ready = True
        else:
            self._instrument._buffer2_ready = True


    def get_raw(self) -> ParamRawDataType:
        """
        Get command. Returns numpy array
        """
        assert isinstance(self._instrument, SR844)
        if self.channel == 1:
            ready = self._instrument._buffer1_ready
        else:
            ready = self._instrument._buffer2_ready

        if not ready:
            raise RuntimeError("Buffer not ready. Please run " "prepare_buffer_readout")
        N = self._instrument.buffer_npts()
        if N == 0:
            raise ValueError(
                "No points stored in SR844 data buffer." " Can not poll anything."
            )

        # poll raw binary data
        self._instrument.write(f"TRCL ? {self.channel}, 0, {N}")
        rawdata = self._instrument.visa_handle.read_raw()

        # parse it
        realdata = np.fromstring(rawdata, dtype="<i2")
        numbers = realdata[::2] * 2.0 ** (realdata[1::2] - 124)
        if self.shape[0] != N:
            raise RuntimeError(
                "SR844 got {} points in buffer expected {}".format(N, self.shape[0])
            )
        return numbers


class SR844(VisaInstrument):
    """
    This is the qcodes driver for the Stanford Research Systems SR844
    Lock-in Amplifier
    """

    def __init__(self, name: str, address: str, **kwargs: Any):
        super().__init__(name, address, **kwargs)

        # Reference and phase
        self.add_parameter(
            "phase_offset",
            label="Phase",
            get_cmd="PHAS?",
            get_parser=float,
            set_cmd="PHAS {:.2f}",
            unit="deg",
            vals=Numbers(min_value=-360, max_value=360),
        )

        self.add_parameter(
            "reference_source", 
            label="Reference source",
            get_cmd="FMOD?",
            set_cmd="FMOD {}",
            val_mapping={
                "external": 0,
                "internal": 1,
            },
            vals=Enum("external", "internal"),
        )

        self.add_parameter(
            "frequency",
            label="Frequency",
            get_cmd="FREQ?",
            get_parser=float,
            set_cmd=self._set_freq,
            unit="Hz",
            vals=Numbers(min_value=2.5e4, max_value=2e8),
        )

        self.add_parameter(
            "harmonic",
            label="Harmonic",
            get_cmd="HARM?",
            set_cmd=self._set_harmonic,
            val_mapping={
                "f": 0,
                "2f": 1,
            },
        )

        # FB: it seems the reference channel has only square wave 1.0Vpp nominal into 50Ω
        # self.add_parameter('amplitude',
        #                    label='Amplitude',
        #                    get_cmd='SLVL?',
        #                    get_parser=float,
        #                    set_cmd='SLVL {:.3f}',
        #                    unit='V',
        #                    vals=Numbers(min_value=0.004, max_value=5.000))

        self.add_parameter(
            "input_impedance",
            label="Input impedance",
            get_cmd="REFZ?",
            set_cmd="REFZ {}",
            val_mapping={
                "I 50k": 0,
                "I 1M": 1,
            },
        )

        # FB: sensitivity was read correctly by qcodes for 0 and 1, but not for setting #2. # No issue was noted on a rerun
        self.add_parameter(
            name="sensitivity",
            label="Sensitivity",
            get_cmd="SENS?",
            set_cmd="SENS {}",
            val_mapping={
                100e-9: 0,
                300e-9: 1,
                1e-6: 2,
                3e-6: 3,
                10e-6: 4,
                30e-6: 5,
                100e-6: 6,
                300e-6: 7,
                1e-3: 8,
                3e-3: 9,
                10e-3: 10,
                30e-3: 11,
                100e-3: 12,
                300e-3: 13,
                1: 14,
            },
        )

        self.add_parameter(
            "reserve",
            label="Reserve",
            get_cmd="WRSV?",
            set_cmd="WRSV {}",
            val_mapping={
                "high": 0,
                "normal": 1,
                "low noise": 2,
            },
        )

        self.add_parameter(
            "time_constant",
            label="Time constant",
            get_cmd="OFLT?",
            set_cmd="OFLT {}",
            unit="s",
            val_mapping={
                100e-6: 0,
                300e-6: 1,
                1e-3: 2,
                3e-3: 3,
                10e-3: 4,
                30e-3: 5,
                100e-3: 6,
                300e-3: 7,
                1: 8,
                3: 9,
                10: 10,
                30: 11,
                100: 12,
                300: 13,
                1e3: 14,
                3e3: 15,
                10e3: 16,
                30e3: 17,
            },
        )

        self.add_parameter(
            "filter_slope",
            label="Filter slope",
            get_cmd="OFSL?",
            set_cmd="OFSL {}",
            unit="dB/oct",
            val_mapping={
                0: 0,  # FB: To be updated
                6: 1,
                12: 2,
                18: 3,
                24: 4,
            },
        )

        # FB: offset function changed to DOFF and parameters modified accordingly
        self.add_parameter(
            "X_offset",
            get_cmd="DOFF? 1, 0",
            get_parser=float,
            set_cmd="DOFF 1, 0, {}",
            unit="% of full scale",
            vals=Numbers(min_value=-110, max_value=110),
        )

        self.add_parameter(
            "R_V_offset",
            get_cmd="DOFF? 1, 1",
            get_parser=float,
            set_cmd="DOFF 1, 1, {}",
            unit="% of full scale",
            vals=Numbers(min_value=-110, max_value=110),
        )

        self.add_parameter(
            "R_dBm_offset",
            get_cmd="DOFF? 1, 2",
            get_parser=float,
            set_cmd="DOFF 1, 2, {}",
            unit="% of 200 dBm scale",
            vals=Numbers(min_value=-110, max_value=110),
        )
        self.add_parameter(
            "Y_offset",
            get_cmd="DOFF? 2, 0",
            get_parser=float,
            set_cmd="DOFF 2, 0, {}",
            unit="% of full scale",
            vals=Numbers(min_value=-110, max_value=110),
        )
   
        for i in [1, 2]:
            self.add_parameter(
                f"aux_in{i}",
                label=f"Aux input {i}",
                get_cmd=f"AUXI? {i}",
                get_parser=float,
                unit="V",
            )

            self.add_parameter(
                f"aux_out{i}",
                label=f"Aux output {i}",
                get_cmd=f"AUXO? {i}",
                get_parser=float,
                set_cmd=f"AUXO {i}, {{}}",
                unit="V",
                vals=Numbers(min_value=-10.5, max_value=10.5)
            )

        self.add_parameter(
            "output_interface",
            label="Output interface",
            get_cmd="OUTX?",
            set_cmd="OUTX {}",
            val_mapping={
                "RS232": "0\n",
                "GPIB": "1\n",
            },
        )

        self.add_parameter(
            "ratio_mode",
            label="Ratio mode",
            get_cmd="DRAT?",
            set_cmd=self._set_ratio,
            val_mapping={
                "none": 0,
                "AuxIn1": 1,
                "AuxIn2": 2,
            },
        )
        
        # self.add_parameter(
        #     "ch1_display",
        #     label="Channel 1 display",
        #     get_cmd="DDEF? 1 ",
        #     set_cmd="DDEF 1, {}",
        #     val_mapping={
        #         "X": 0,
        #         "R_V": 1,
        #         "R_dBm": 2,
        #         "Xn": 3,
        #         "AuxIn1": 4,
        #     },
        # )
        
        # self.add_parameter(
        #     "ch2_display",
        #     label="Channel 2 display",
        #     get_cmd="DDEF? 2 ",
        #     set_cmd="DDEF 2, {}",
        #     val_mapping={
        #         "Y": 0,
        #         "P": 1,
        #         "Yn_V": 2,
        #         "Yn_dBm": 3,
        #         "AuxIn2": 4,
        #     },
        # )
        

        self.add_parameter("buffer_SR",
                           label="Buffer sample rate",
                           get_cmd="SRAT ?",
                           set_cmd=self._set_buffer_SR,
                           unit="Hz",
                           val_mapping={
                                62.5e-3: 0,
                                0.125: 1,
                                0.250: 2,
                                0.5: 3,
                                1: 4,
                                2: 5,
                                4: 6,
                                8: 7,
                                16: 8,
                                32: 9,
                                64: 10,
                                128: 11,
                                256: 12,
                                512: 13,
                                "Trigger": 14,
                           },
                           get_parser=int)

        self.add_parameter("buffer_acq_mode",
                           label="Buffer acquistion mode",
                           get_cmd="SEND ?",
                           set_cmd="SEND {}",
                           val_mapping={"single shot": 0, "loop": 1},
                           get_parser=int)

        self.add_parameter("buffer_trig_mode",
                           label="Buffer trigger start mode",
                           get_cmd="TSTR ?",
                           set_cmd="TSTR {}",
                           val_mapping={"ON": 1, "OFF": 0},
                           get_parser=int)

        self.add_parameter("buffer_npts",
                           label="Buffer number of stored points",
                           get_cmd="SPTS ?",
                           get_parser=int)
        
        self.add_parameter('sweep_setpoints',
                           parameter_class=GeneratedSetPoints,
                           vals=Arrays(shape=(self.buffer_npts.get,)))
        
        for ch in [1, 2]:

            self.add_parameter(f'ch{ch}_display',
                               label=f'Channel {ch} display',
                               get_cmd=partial(self._get_ch_display, ch),
                               set_cmd=partial(self._set_ch_display, ch),
                               vals=Strings())
            self.add_parameter(f"ch{ch}_databuffer", 
                               channel=ch, 
                               parameter_class=ChannelBuffer)
            self.add_parameter(f'ch{ch}_datatrace',
                               channel=ch,
                               vals=Arrays(shape=(self.buffer_npts.get,)),
                        setpoints=(self.sweep_setpoints,),
                        parameter_class=ChannelTrace)

        # Data transfer FB: added RSR844m]
        self.add_parameter("X", 
                           get_cmd="OUTP? 1", 
                           get_parser=float,
                           unit="V")

        self.add_parameter("Y", 
                           get_cmd="OUTP? 2", 
                           get_parser=float, 
                           unit="V")

        self.add_parameter("R_V", 
                           get_cmd="OUTP? 3", 
                           get_parser=float, 
                           unit="V")

        self.add_parameter("R_dBm", 
                           get_cmd="OUTP? 4", 
                           get_parser=float, 
                           unit="dBm")
        
        self.add_parameter("phase", 
                           get_cmd="OUTP? 5", 
                           get_parser=float, 
                           unit="deg")
        
        self.add_parameter("ch1", 
                           get_cmd="OUTR? 1", 
                           get_parser=float, 
                           unit="V")
                
        self.add_parameter("ch2", 
                           get_cmd="OUTR? 2", 
                           get_parser=float, 
                           unit="V")
                                        ### use of functions is advised against due to code transparency ###
        # Auto functions
        self.add_function("auto_gain", call_cmd="AGAN")
        self.add_function("auto_wideband_reserve ", call_cmd="AWRS")
        self.add_function("auto_close_in_reserve ", call_cmd="ACRS")
        self.add_function("auto_phase", call_cmd="APHS")
        # FB auto offset functions could be improved
        self.add_function("auto_offset_ch1", call_cmd="AOFF 1, {}", args=[Enum(0, 1, 2)])
        self.add_function("auto_offset_ch2", call_cmd="AOFF 2, {0}", args=[Enum(0)])

        # Interface
        self.add_function("reset", call_cmd="*RST")
        self.add_function("disable_front_panel", call_cmd="OVRM 0")
        self.add_function("enable_front_panel", call_cmd="OVRM 1")

        self.add_function(
            "send_trigger",
            call_cmd="TRIG",
            docstring=(
                "Send a software trigger. "
                "This command has the same effect as a "
                "trigger at the rear panel trigger"
                " input."
            ),
        )

        self.add_function(
            "buffer_start",
            call_cmd="STRT",
            docstring=(
                "The buffer_start command starts or "
                "resumes data storage. buffer_start"
                " is ignored if storage is already in"
                " progress."
            ),
        )

        self.add_function(
            "buffer_pause",
            call_cmd="PAUS",
            docstring=(
                "The buffer_pause command pauses data "
                "storage. If storage is already paused "
                "or reset then this command is ignored."
            ),
        )

        self.add_function(
            "buffer_reset",
            call_cmd="REST",
            docstring=(
                "The buffer_reset command resets the data"
                " buffers. The buffer_reset command can "
                "be sent at any time - any storage in "
                "progress, paused or not, will be reset."
                " This command will erase the data "
                "buffer."
            ),
        )

        # Initialize the proper units of the outputs and sensitivities
        # self.input_config()

        # start keeping track of buffer setpoints
        self._buffer1_ready = False
        self._buffer2_ready = False

        self.connect_message()

    SNAP_PARAMETERS = {
        "x": "1",
        "y": "2",
        "r_V": "3",
        "r_dBm": "4",
        "p": "5",
        "phase": "5",
        "θ": "5",
        "aux1": "6",
        "aux2": "7",
        "freq": "8",
        "ch1": "9",
        "ch2": "10",
    }

    def snap(self, *parameters: str) -> Tuple[float, ...]:
        """
        Get between 2 and 6 parameters at a single instant. This provides a
        coherent snapshot of measured signals. Pick up to 6 from: X, Y, R, θ,
        the aux inputs 1-2, frequency, or what is currently displayed on
        channels 1 and 2.

        Reading X and Y (or R and θ) gives a coherent snapshot of the signal.
        Snap is important when the time constant is very short, a time constant
        less than 100 ms.

        Args:
            *parameters: From 2 to 6 strings of names of parameters for which
                the values are requested. including: 'x', 'y', 'r', 'p',
                'phase' or 'θ', 'aux1', 'aux2', 'freq',
                'ch1', and 'ch2'.

        Returns:
            A tuple of floating point values in the same order as requested.

        Examples:
            >>> lockin.snap('x','y') -> tuple(x,y)

            >>> lockin.snap('aux1','aux2','freq','phase')
            >>> -> tuple(aux1,aux2,freq,phase)

        Note:
            Volts for x, y, r, and aux 1-4
            Degrees for θ
            Hertz for freq
            Unknown for ch1 and ch2. It will depend on what was set.

             - If X,Y,R and θ are all read, then the values of X,Y are recorded
               approximately 10 µs apart from R,θ. Thus, the values of X and Y
               may not yield the exact values of R and θ from a single snap.
             - The values of the Aux Inputs may have an uncertainty of
               up to 32 µs.
             - The frequency is computed only every other period or 40 ms,
               whichever is longer.
        """
        if not 2 <= len(parameters) <= 6:
            raise KeyError(
                "It is only possible to request values of 2 to 6 parameters"
                " at a time."
            )

        for name in parameters:
            if name.lower() not in self.SNAP_PARAMETERS:
                raise KeyError(
                    f"{name} is an unknown parameter. Refer"
                    f" to `SNAP_PARAMETERS` for a list of valid"
                    f" parameter names"
                )

        p_ids = [self.SNAP_PARAMETERS[name.lower()] for name in parameters]
        output = self.ask(f'SNAP? {",".join(p_ids)}')

        return tuple(float(val) for val in output.split(","))

    def increment_sensitivity(self) -> bool:
        """
        Increment the sensitivity setting of the lock-in. This is equivalent
        to pushing the sensitivity up button on the front panel. This has no
        effect if the sensitivity is already at the maximum.

        Returns:
            Whether or not the sensitivity was actually changed.
        """
        return self._change_sensitivity(1)


    def decrement_sensitivity(self) -> bool:
        """
        Decrement the sensitivity setting of the lock-in. This is equivalent
        to pushing the sensitivity down button on the front panel. This has no
        effect if the sensitivity is already at the minimum.

        Returns:
            Whether or not the sensitivity was actually changed.
        """
        return self._change_sensitivity(-1)


    def _set_harmonic(self, harm: int) -> None:
        if harm == 0:
            self.write("HARM 0")
        else:
            freq = self.parameters['frequency'].get()
            if freq < 50000:
                raise ValueError('Frequency must be 50kHz or greater to enable second harmonics')
            self.write("HARM 1")
            
            
    def _set_freq(self, freq: float) -> None:
        params = self.parameters
        if params['reference_source'].get() != "internal":
            raise ValueError("Cannot set frequency, since the frequency reference_source is not internal")
        else:
            if freq >= 50000:
                self.write(f"FREQ {freq}")
            else:
                harm = params['harmonic'].get()
                if harm == '2f':
                    raise ValueError('Frequency must be 50kHz or greater when lockin is in second harmonics configuration')
                self.write(f"FREQ {freq}")


    def _change_sensitivity(self, dn: int) -> bool:
        if self.input_config() in ["a", "a-b"]:
            n_to = self._N_TO_VOLT
            to_n = self._VOLT_TO_N
        else:
            n_to = self._N_TO_CURR
            to_n = self._CURR_TO_N

        n = to_n[self.sensitivity()]

        if n + dn > max(n_to.keys()) or n + dn < min(n_to.keys()):
            return False

        self.sensitivity.set(n_to[n + dn])
        return True


    def _set_buffer_SR(self, SR: int) -> None:
        self.write(f"SRAT {SR}")
        self._buffer1_ready = False
        self._buffer2_ready = False

    # def _get_ch_ratio(self, channel: int) -> str:
    #     val_mapping = {0: 'none',
    #                    1: 'AuxIn1',
    #                    2: 'AuxIn2'}
    #     resp = int(self.ask(f'DRAT ?').split(',')[1])

    #     return val_mapping[channel][resp]

    def _set_ratio(self, ratio_int: int) -> None:
        self.write(f'DRAT {ratio_int}')
        self._buffer_ready = False
        params = self.parameters
        for ch in [1, 2]:
            dataparam = params[f'ch{ch}_datatrace']
            assert isinstance(dataparam, ChannelTrace)
            dataparam.update_unit()

    def _get_ch_display(self, channel: int) -> str:
        val_mapping = {1: {0: 'X',
                           1: 'R_V',
                           2: 'R_dBm',
                           3: 'X Noise',
                           4: 'AuxIn1'},
                       2: {0: 'Y',
                           1: 'Phase',
                           2: 'Y Noise',
                           3: 'Y_dBm Noise',
                           4: 'AuxIn2'}}
        resp = int(self.ask(f'DDEF ? {channel}').split(',')[0]) 

        return val_mapping[channel][resp]

    def _set_ch_display(self, channel: int, disp: str) -> None:
        val_mapping = {1: {'X': 0,
                           'R_V': 1,
                           'R_dBm': 2,
                           'X Noise': 3,
                           'AuxIn1': 4},
                       2: {'Y': 0,
                           'Phase': 1,
                           'Y Noise': 2,
                           'Y_dBm Noise': 3,
                           'AuxIn2': 4}}
        vals = val_mapping[channel].keys()
        if disp not in vals:
            raise ValueError(f'{disp} not in {vals}')
        disp_int = val_mapping[channel][disp]
        # Since ratio AND display are set simultaneously,
        # we get and then re-set the current ratio value
        #ratio_val = int(self.ask(f'DRAT ?').split(',')[1])
        #self.write(f'DRAT {ratio_val}')
        self.write(f'DDEF {channel}, {disp_int}')
        self._buffer_ready = False
        # we update the unit of the datatrace
        # according to the choice of channel
        params = self.parameters
        dataparam = params[f'ch{channel}_datatrace']
        assert isinstance(dataparam, ChannelTrace)
        dataparam.update_unit()

    def set_sweep_parameters(self,
                             sweep_param: Parameter,
                             start: float,
                             stop: float,
                             n_points: int = 10,
                             label: Union[str, None] = None) -> None:

        self.sweep_setpoints.sweep_array = np.linspace(start, stop, n_points)
        self.sweep_setpoints.unit = sweep_param.unit
        if label is not None:
            self.sweep_setpoints.label = label
        elif sweep_param.label is not None:
            self.sweep_setpoints.label = sweep_param.label
    
class GeneratedSetPoints(Parameter):
    """
    A parameter that generates a setpoint array from start, stop and num points
    parameters.
    """
    def __init__(self,
                 sweep_array: Iterable[Union[float, int]] = np.linspace(0, 1, 10),
                 *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.sweep_array = sweep_array
        self.update_units_if_constant_sample_rate()

    def update_units_if_constant_sample_rate(self) -> None:
        """
        If the buffer is filled at a constant sample rate,
        update the unit to "s" and label to "Time";
        otherwise do nothing
        """
        assert isinstance(self.root_instrument, SR844)
        SR = self.root_instrument.buffer_SR.get()
        if SR != 'Trigger':
            self.unit = 's'
            self.label = 'Time'

    def set_raw(self, value: Iterable[Union[float, int]]) -> None:
        self.sweep_array = value

    def get_raw(self) -> ParamRawDataType:
        assert isinstance(self.root_instrument, SR844)
        SR = self.root_instrument.buffer_SR.get()
        if SR == 'Trigger':
            return self.sweep_array
        else:
            N = self.root_instrument.buffer_npts.get()
            dt = 1/SR

            return np.linspace(0, N*dt, N)

    # def _set_units(self, unit: str) -> None:
    #     # TODO:
    #     # make a public parameter function that allows to change the units
    #     for param in [self.X, self.Y, self.R, self.sensitivity]:
    #         param.unit = unit

    # def _get_input_config(self, s: int) -> str:
    #     mode = self._N_TO_INPUT_CONFIG[int(s)]

    #     if mode in ['a', 'a-b']:
    #         self.sensitivity.vals = self._VOLT_ENUM
    #         self._set_units('V')
    #     else:
    #         self.sensitivity.vals = self._CURR_ENUM
    #         self._set_units('A')

    #     return mode

    # def _set_input_config(self, s: str) -> int:
    #     if s in ['a', 'a-b']:
    #         self.sensitivity.vals = self._VOLT_ENUM
    #         self._set_units('V')
    #     else:
    #         self.sensitivity.vals = self._CURR_ENUM
    #         self._set_units('A')

    #     return self._INPUT_CONFIG_TO_N[s]

    # def _get_sensitivity(self, s: int) -> float:
    #     if self.input_config() in ['a', 'a-b']:
    #         return self._N_TO_VOLT[int(s)]
    #     else:
    #         return self._N_TO_CURR[int(s)]

    # def _set_sensitivity(self, s: float) -> int:
    #     if self.input_config() in ['a', 'a-b']:
    #         return self._VOLT_TO_N[s]
    #     else:
    #         return self._CURR_TO_N[s]
