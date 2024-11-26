import logging
log = logging.getLogger(__name__)

from qcodes import VisaInstrument
import qcodes.utils.validators as vals

class DG645(VisaInstrument):
    """Qcodes driver for SRS DG645 digital delay generator.
    """
    CHANNEL_MAPPING = {
        'T0': 0, 'T1': 1, 'A': 2, 'B': 3, 'C': 4,
        'D': 5, 'E': 6, 'F': 7, 'G': 8, 'H': 9
    }
    OUTPUT_MAPPING = {'T0': 0, 'AB': 1, 'CD': 2, 'EF': 3, 'GH': 4}
    PRESCALE_MAPPING = {'trig': 0, 'AB': 1, 'CD': 2, 'EF': 3, 'GH': 4}
    TRIGGER_MAPPING = {
        'internal': 0,
        'ext_rising': 1,
        'ext_falling': 2,
        'single_ext_rising': 3,
        'single_ext_falling': 4,
        'single': 5,
        'line': 6,
    }
    POLARITY_MAPPING = {'-': 0, '+': 1}
    DISPLAY_MAPPING = {
        'trig_rate': 0,
        'trig_thresh': 1,
        'trig_single_shot': 2,
        'trig_line': 3,
        'advanced_trig_enable': 4,
        'trig_holdoff': 5,
        'prescale_config': 6,
        'burst_mode': 7,
        'burst_delay': 8,
        'burst_count': 9,
        'burst_period': 10,
        'channel_delay': 11,
        'channel_output_levels': 12,
        'channel_output_polarity': 13,
        'burst_T0_config': 14
    }
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, terminator='\r\n', timeout=10, **kwargs)
        self.add_parameter('trig_holdoff',
            label='Trigger holdoff',
            unit='s',
            get_cmd='HOLD?',
            get_parser=float,
            set_cmd='HOLD {}'
        )

        # Prescale parameters
        for channel, idx in self.PRESCALE_MAPPING.items():
            if idx > 0:
                self.add_parameter(
                    f'phase_{channel}',
                    label=f'{channel} prescale phase factor {k}',
                    get_cmd=f'PHAS?{idx}',
                    get_parser=int,
                    set_cmd=f'PHAS {idx},{{}}',
                    vals=vals.Ints(min_value=0),
                    docstring="""\
                    The prescale phase factor determines the phase at which the associated output is
                    enabled. The output is enabled when the prescaler counter equals the phase
                    factor. 
                    """
                )

            self.add_parameter(
                f'prescale_{channel}',
                label=f'{channel} prescale factor',
                get_cmd=f'PRES?{idx}',
                get_parser=int,
                set_cmd=f'PRES {idx},{{}}',
                vals=vals.Ints(min_value=0),
                docstring="""\
                A prescaler on the trigger input enables one to generate
                delay cycles at a sub-multiple of the trigger input frequency.
                """
            )

        # Trigger parameters
        self.add_parameter(
            'trigger_level',
            label='Trigger level',
            unit='V',
            get_cmd='TLVL?',
            get_parser=float,
            set_cmd='TLVL {}',
            vals=vals.Numbers()
        )
        self.add_parameter(
            'trigger_rate',
            label='Trigger rate',
            unit='Hz',
            get_cmd='TRAT?',
            get_parser=float,
            set_cmd='TRAT {}',
            vals=vals.Numbers(min_value=0)
        ) 
        self.add_parameter(
            'trigger_source',
            label='Trigger source',
            get_cmd=self._get_trigger_source,
            get_parser=str,
            set_cmd=self._set_trigger_source,
            vals=vals.Enum(*tuple(self.TRIGGER_MAPPING))
        )

        # Burst parameters
        self.add_parameter(
            'burst_count',
            label='Burst count',
            get_cmd='BURC?',
            get_parser=int,
            set_cmd='BURC {}',
            vals=vals.Ints(min_value=0)
        )
        self.add_parameter(
            'burst_delay',
            label='Burst delay',
            unit='s',
            get_cmd='BURD?',
            get_parser=float,
            set_cmd='BURD {}',
            vals=vals.Numbers(min_value=0)
        )
        self.add_parameter(
            'burst_period',
            label='Burst period',
            unit='s',
            get_cmd='BURP?',
            get_parser=float,
            set_cmd='BURC {}',
            vals=vals.Numbers(min_value=100e-9, max_value=2000-10e-9)
        )
        self.add_parameter(
            'burst_T0_config',
            label='Burst T0 configuration',
            get_cmd='BURT?',
            get_parser=int,
            set_cmd='BURT {}',
            vals=vals.Enum(0,1)
        )

        # Channel parameters
        for ch, idx in self.CHANNEL_MAPPING.items():
            if idx > 1:
                self.add_parameter(
                    f'delay_{ch}',
                    label=f'{ch} delay',
                    unit='s',
                    get_cmd=f'DLAY?{idx}',
                    get_parser=str,
                    set_cmd=lambda src_delay, channel=ch: self._set_delay(src_delay, channel),
                    vals=vals.Strings(),
                    docstring="""\
                    Set/query they delay of this channel relative to another.
                    Arguments/returned values strings of the form
                    '{index_of_other_channel},{delay_in_seconds}'. For example, '2,+0.001'
                    indicates that this channel is delayed from channel A by 1 ms, since
                    self.CHANNEL_MAPPING['A'] == 2.
                    """
                )
                self.add_parameter(
                    f'channel_link_{ch}',
                    label=f'Channel linked to {ch}',
                    get_cmd=f'LINK?{idx}',
                    get_parser=int,
                    set_cmd=lambda target, source=ch: self._set_link(target, source),
                    vals=vals.Enum(*tuple(k for k in self.CHANNEL_MAPPING if k != 'T1'))
                )

        # Output parameters
        for out, idx in self.OUTPUT_MAPPING.items():
            self.add_parameter(
                f'amp_out_{out}',
                label=f'Output {out} amplitude',
                unit='V',
                get_cmd=f'LAMP?{idx}',
                get_parser=float,
                set_cmd=f'LAMP {idx},{{}}',
                vals=vals.Numbers()
            )
            self.add_parameter(
                f'offset_out_{out}',
                label=f'Output {out} offset',
                unit='V',
                get_cmd=f'LOFF?{idx}',
                get_parser=float,
                set_cmd=f'LOFF {idx},{{}}',
                vals=vals.Numbers()
            )
            self.add_parameter(
                f'polarity_out_{out}',
                label=f'Output {out} polarity',
                get_cmd=f'LPOL?{idx}',
                get_parser=int,
                set_cmd=f'LPOL {idx},{{}}',
                vals=vals.Enum(0,1),
                docstring='0 -> negative polarity, 1 -> positive polarity.'
            )

        self.snapshot(update=True)
        self.connect_message()

    def self_calibrate(self) -> None:
        """Run auto-calibration routine.
        """
        self.write('*CAL?')
        self.wait()

    def self_test(self) -> None:
        """Run self-test routine.
        """
        self.write('*TST?')
        self.wait()

    def reset(self) -> None:
        """Reset instrument.
        """
        log.info(f'Resetting {self.name}.')
        self.write('*RST')

    def save_settings(self, location: int) -> None:
        """Save instrument settings to given location.

        Args:
            location: Location to which to save the settings (in [1..9]).
        """
        log.info(f'Saving instrument settings to location {location}.')
        self.write(f'*SAV {location}')

    def trigger(self) -> None:
        """Initiates a single trigger if instrument is in single shot mode.
        """
        self.write('*TRG')

    def wait(self) -> None:
        """Wait for all prior commands to execute before continuing.
        """
        self.write('*WAI')

    def local(self) -> None:
        """Go to local.
        """
        self.write('LCAL')

    def remote(self) -> None:
        """Go to remote.
        """
        self.write('REMT')

    def _set_trigger_source(self, src: str) -> None:  
        self.write(f'TSRC {self.TRIGGER_MAPPING[src]}')

    def _get_trigger_source(self) -> str:
        response = self.ask('TSRC?')
        keys = self.TRIGGER_MAPPING.keys()
        values = self.TRIGGER_MAPPING.values()
        return list(keys)[list(values).index(int(response))]

    def _set_delay(self, src_delay: str, target: str) -> None:
        source, delay = [s.strip() for s in src_delay.split(',')]
        self.write('DLAY {},{},{}'.format(self.CHANNEL_MAPPING[target],
                                          self.CHANNEL_MAPPING[source],
                                          delay))

    def _set_link(self, target: str, source: str) -> None:
        self.write('LINK {},{}'.format(self.CHANNEL_MAPPING[target],
                                       self.CHANNEL_MAPPING[source]))
