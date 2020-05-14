from qcodes.instrument.visa import VisaInstrument


class Keithley_6500(VisaInstrument):

    def __init__(self, name: str,
                 address: str,
                 terminator="\n",
                 reset: bool = False,
                 **kwargs):
        super().__init__(name, address, terminator=terminator, **kwargs)

        self.add_parameter('sense_voltage_dc',
                           unit='V',
                           get_parser=float,
                           label='Measured voltage',
                           get_cmd=':MEAS:VOLT:DC?',
                           docstring='Value of measured DC voltage.',
                           )