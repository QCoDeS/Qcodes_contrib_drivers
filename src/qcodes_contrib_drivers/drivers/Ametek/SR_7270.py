# This Python file uses the following encoding: utf-8

"""
Created by Elyjah <elyjah.kiyooka@cea.fr>, Jan 2022

"""

from qcodes.instrument import VisaInstrument
from qcodes import validators as vals
from qcodes.utils import DelayedKeyboardInterrupt
from qcodes.validators import ComplexNumbers

class Signalrecovery7270(VisaInstrument):
    """
    This is the qcodes driver for the Ametex Signal Recovery
    Model 7270 DSP Lockin amplifier

    Note:
    ask_raw command has been rewritten (bottom) to also read an echo to remove from buffer.
    write_raw command have been rewritten to also read after writing using ask_raw.

    """
    def __init__(self, name: str, address: str, terminator='\n\x00', **kwargs):
        super().__init__(name, address, terminator=terminator, device_clear = True, **kwargs)

        idn = self.IDN.get()
        self.model = idn['model']

        self.add_parameter(name='x',
                        label='Lock-In X',
                        get_cmd='X.',
                        get_parser=float,
                        unit='V',
                        vals = vals.Numbers(),
                        docstring="Gets X lockin component in V; "
                                "only gettable.")

        self.add_parameter('y',
                        label='Lock-In Y',
                        get_cmd='Y.',
                        get_parser=float,
                        unit='V',
                        vals = vals.Numbers(),
                        docstring="Gets Y lockin component in V; "
                                "only gettable.")

        self.add_parameter('xy',
                        label='Lock-In XY Complex',
                        get_cmd=self._get_complex_voltage,
                        unit='V',
                        vals = ComplexNumbers(),
                        docstring="Complex voltage parameter "
                                "calculated from X, Y phase using "
                                "Z = X + j*Y")

        self.add_parameter(name='r',
                        label='Lock-In R',
                        get_cmd='MAG.',
                        get_parser=float,
                        unit='V',
                        vals = vals.Numbers(),
                        docstring="Gets magnitude of XY lockin components in V; "
                                "only gettable.")

        self.add_parameter(name='phase',
                        label='Lock-In Phase',
                        get_cmd='PHA.',
                        get_parser=float,
                        unit='Degrees',
                        vals = vals.Numbers(),
                        docstring="Gets the polar phase of lockin in degrees; "
                                "only gettable.")

        self.add_parameter(name='frequency',
                        label='Reference Frequency',
                        get_cmd='FRQ.',
                        get_parser=float,
                        unit='Hz',
                        vals = vals.Numbers(),
                        docstring="Gets frequency of demodulator in Hz; "
                                "only gettable.")

        self.add_parameter(name='osc_amplitude',
                        label='Oscillator Amplitude',
                        unit='V',
                        set_cmd='OA. {}',
                        set_parser=float,
                        get_cmd='OA.',
                        get_parser=float,
                        vals=vals.Numbers(min_value=0, max_value=5),
                        docstring="Get and set oscillator output amplitude in V;"
                                "Output is in rms values"
                                "gettable and settable.")

        self.add_parameter(name='osc_frequency',
                        label='Oscillator Frequency',
                        unit='Hz',
                        set_cmd='OF. {}',
                        set_parser=float,
                        get_cmd='OF.',
                        get_parser=float,
                        vals=vals.Numbers(min_value=10, max_value=250000),
                        docstring="Get and set oscillator output frequency in Hz; "
                                "gettable and settable.")

        self.add_parameter(name='reference',
                        label='Reference Input',
                        get_cmd='IE',
                        set_cmd='IE {}',
                        val_mapping = {'INT':       0,
                                        'EXT_rear':  1,
                                        'EXT_front': 2},
                        docstring="Get and set which reference signal is used; "
                                "gettable and settable.")

        self.add_parameter(name='noise_mode',
                        label='Noise mode',
                        get_cmd='NOISEMODE',
                        set_cmd='NOISEMODE {}',
                        initial_value='OFF',
                        val_mapping = {'OFF':    0,
                                        'ON':  1},
                        docstring=("Get and set the noise mode used. "
                                    "Should always leave off as it "
                                    "will change the values of TC "
                                    "and the low pass filter slope."))

        self.add_parameter(name='I_mode',
                        label='Current mode',
                        get_cmd='IMODE',
                        set_cmd='IMODE {}',
                        val_mapping = {'CURRENT_MODE_OFF': 0,
                                        'CURRENT_MODE_ON_HIGH_BW': 1,
                                        'CURRENT_MODE_ON_LOW_BW': 2},
                        docstring=("Get and set if current or voltage is to be measured"
                                    "n Input mode"
                                    "0 Current mode off - voltage mode input enabled"
                                    "1 High bandwidth current mode enabled -"
                                    "connect signal to B (I) input connector"
                                    "2 Low noise current mode enabled -"
                                    "connect signal to B (I) input connector "
                                    "If n = 0 then the input configuration "
                                    "is determined by the VMODE command. "
                                    "If n > 0 then current mode "
                                    "is enabled irrespective of the VMODE setting."))

        self.add_parameter(name='V_mode',
                        label='Voltage mode',
                        get_cmd='VMODE',
                        set_cmd='VMODE {}',
                        val_mapping = {'INPUTS_GNDED': 0,
                                        'A_INPUT_ONLY': 1,
                                        '-B_INPUT_ONLY': 2,
                                        'A_B_DIFFERENTIAL': 3},
                        docstring=("Get and set how the voltage is to be measured: "
                                   "INPUTS_GNDED:, 'A_INPUT_ONLY', '-B_INPUT_ONLY', or 'A-B DIFFERENTIAL.' "
                                    "Note that the IMODE command takes precedence over the VMODE command."))

        self.add_parameter(name='osc_sync',
                        label='Synchronize oscillator',
                        get_cmd='SYNCOSC',
                        set_cmd='SYNCOSC {}',
                        initial_value='OFF',
                        val_mapping = {'OFF':    0,
                                        'ON':  1},
                        docstring=("Get and set if the oscillator synchronizes "
                                    "Syncs to the external reference signal "
                                    "can only be used in external reference mode."))

        self.add_parameter(name='sensitivity',
                        label='Sensitivity',
                        unit='V',
                        get_cmd='SEN',
                        set_cmd='SEN {}',
                        val_mapping={   2e-9: 1,
                                        5e-9: 2,
                                        10e-9: 3,
                                        20e-9: 4,
                                        50e-9: 5,
                                        100e-9: 6,
                                        200e-9: 7,
                                        500e-9: 8,
                                        1e-6: 9,
                                        2e-6: 10,
                                        5e-6: 11,
                                        10e-6: 12,
                                        20e-6: 13,
                                        50e-6: 14,
                                        100e-6: 15,
                                        200e-6: 16,
                                        500e-6: 17,
                                        1e-3: 18,
                                        2e-3: 19,
                                        5e-3: 20,
                                        10e-3: 21,
                                        20e-3: 22,
                                        50e-3: 23,
                                        100e-3: 24,
                                        200e-3: 25,
                                        500e-3: 26,
                                        1: 27},
                        docstring=("Set measurement input sensitivity; "
                                   "only settable."))

        self.add_parameter(name='timeconstant',
                        label='Time constant',
                        unit='s',
                        get_cmd='TC',
                        set_cmd='TC {}',
                        val_mapping={   10e-6: 0,
                                        20e-6: 1,
                                        50e-6: 2,
                                        100e-6: 3,
                                        200e-6: 4,
                                        500e-6: 5,
                                        1e-3: 6,
                                        2e-3: 7,
                                        5e-3: 8,
                                        10e-3: 9,
                                        20e-3: 10,
                                        50e-3: 11,
                                        100e-3: 12,
                                        200e-3: 13,
                                        500e-3: 14,
                                        1: 15,
                                        2: 16,
                                        5: 17,
                                        10: 18,
                                        20: 19,
                                        50: 20,
                                        100: 21,
                                        200: 22,
                                        500: 23,
                                        1e+3: 24,
                                        2e+3: 25,
                                        5e+3: 26,
                                        10e+3: 27,
                                        20e+3: 28,
                                        50e+3: 29,
                                        100e+3: 30},
                        docstring=("Set measurement time constant; "
                                   "only settable."))

    def ask_raw(self, cmd:str) -> str:
        """
        Reimplementaion of ask function to handle lockin echo.

        Args:
            cmd: Command to be sent (asked) to lockin.

        Raises:
            Runtimeerror: If the response does not end with the expected terminators '\\n\\x00' or '\\x00'

        Returns:
            str: Return string from lockin with terminator character stripped of.

        """
        with DelayedKeyboardInterrupt():
            self.visa_handle.clear()
            response = self.visa_handle.query(cmd)
            if response.endswith('\x00'):
                resp = response[:-1]
                if resp.endswith('\n'):
                    return resp[:-1]
                else:
                    return resp
            else:
                return response

    def write_raw(self, cmd:str) -> None:
        """
        Reimplementation of write function to handle lockin echo.
        Calls on ask_raw (defined above) to read echo.

        Args:
            cmd: Command to be sent (asked) to lockin.

        """
        with DelayedKeyboardInterrupt():
            status = self.ask_raw(cmd)

    def get_idn(self):
        """
        Rewrite default get_idn commmand since SR7270 uses different IDN command.
        vendor is hard input; model is called; serial and firmware remain unknown.

        Returns:
            Dict of 'vendor', 'model', 'serial', 'firmware'

        """
        response = self.ask_raw('IDN?')
        idparts = ['Ametek', response, None, None]
        return dict(zip(('vendor', 'model', 'serial', 'firmware'), idparts))

    def _get_complex_voltage(self) -> complex:
        """
        Function to get XY lockin components and return a complex number.

        Returns:
            complex: x + j*y as one complex number

        """
        XY = self.ask_raw('XY.')
        x = float(XY.split(',',1)[0])
        y = float(XY.split(',',1)[1])
        return x + 1j*y
