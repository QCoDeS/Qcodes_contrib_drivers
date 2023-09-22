from qcodes import VisaInstrument


class ThorlabsPM100D(VisaInstrument):

    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, terminator='\n', **kwargs)

        self.add_parameter('wav',
                           get_cmd='CORR:WAV?',
                           set_cmd='CORR:WAV {}',
                           get_parser=float,
                           set_parser=lambda value: '{:.8E}'.format(value),
                           label='wavelength',
                           unit='nm')
        self.add_parameter('pow',
                           get_cmd='READ?',
                           get_parser=float,
                           label='power',
                           unit='Watt')
