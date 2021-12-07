import logging
from functools import partial
from threading import RLock
from typing import List, Union, Optional, Dict, Any
from qcodes import validators as validator

from .SD_Module import SD_Module, result_parser, keysightSD1, is_sd1_3x
from keysightSD1 import (
        SD_Wave, SD_Waveshapes, SD_TriggerExternalSources, SD_FpgaTriggerDirection,
        SD_TriggerPolarity, SD_SyncModes, SD_DigitalFilterModes
        )


class SD_AWG(SD_Module):
    """
    This is the general SD_AWG driver class that implements shared parameters
    and functionality among all PXIe-based AWG cards by Keysight. (series
    M32xxA and M33xxA)

    This driver was written to be inherited from by a specific AWG card
    driver (e.g. M3201A).

    This driver was written with the M3201A card in mind.

    This driver makes use of the Python library provided by Keysight as part
    of the SD1 Software package (v.2.01.00).

    Args:
        name: an identifier for this instrument, particularly for
            attaching it to a Station.
        chassis: identification of the chassis.
        slot: slot of the module in the chassis.
        channels: number of channels of the module.
        triggers: number of triggers of the module.
        legacy_channel_numbering: indicates whether legacy channel number
            should be used. (Legacy numbering starts with channel 0)
    """

    def __init__(self, name: str, chassis: int, slot: int, channels: int,
                 triggers: int, legacy_channel_numbering: bool = True,
                 **kwargs) -> None:
        super().__init__(name, chassis, slot,
                         module_class=keysightSD1.SD_AOU, **kwargs)

        self.awg = self.SD_module
        self.legacy_channel_numbering = legacy_channel_numbering

        # Lock to avoid concurrent access of waveformLoad()/waveformReLoad()
        self._lock = RLock()

        # store card-specifics
        self.channels: int = channels
        self.triggers: int = triggers

        # Open the device, using the specified chassis and slot number
        awg_name = self.awg.getProductNameBySlot(chassis, slot)
        result_parser(awg_name, f'getProductNameBySlot({chassis}, {slot})')

        result_code = self.awg.openWithSlot(awg_name, chassis, slot)
        result_parser(result_code, f'openWithSlot({awg_name}, {chassis},'
                                   f' {slot})')

        self.add_parameter('trigger_io',
                           label='trigger io',
                           get_cmd=self.get_trigger_io,
                           set_cmd=self.set_trigger_io,
                           docstring='Trigger input value, 0 (OFF) or 1 (ON)',
                           vals=validator.Enum(0, 1))
        self.add_parameter('clock_frequency',
                           label='clock frequency',
                           unit='Hz',
                           get_cmd=self.get_clock_frequency,
                           set_cmd=self.set_clock_frequency,
                           docstring='The real hardware clock frequency in Hz',
                           vals=validator.Numbers(100e6, 500e6))
        self.add_parameter('clock_sync_frequency',
                           label='clock sync frequency',
                           unit='Hz',
                           get_cmd=self.get_clock_sync_frequency,
                           docstring='Frequency of the internal CLKsync in Hz')

        for i in range(triggers):
            pxi_trigger_offset = 0 if is_sd1_3x else 4000
            self.add_parameter(f'pxi_trigger_number_{i}',
                               label=f'pxi trigger number {i}',
                               get_cmd=partial(self.get_pxi_trigger,
                                               pxi_trigger=(pxi_trigger_offset + i)),
                               set_cmd=partial(self.set_pxi_trigger,
                                               pxi_trigger=(pxi_trigger_offset + i)),
                               docstring=f'The digital value of pxi trigger '
                                         f'no. {i}, 0 (ON) of 1 (OFF)',
                               vals=validator.Enum(0, 1))

        index_offset = 0 if legacy_channel_numbering else 1

        for i in range(channels):
            ch = i + index_offset
            self.add_parameter(f'frequency_channel_{ch}',
                               label=f'frequency channel {ch}',
                               unit='Hz',
                               set_cmd=partial(self.set_channel_frequency,
                                               channel_number=ch),
                               docstring=f'The frequency of channel {ch}',
                               vals=validator.Numbers(0, 200e6))
            self.add_parameter(f'phase_channel_{ch}',
                               label=f'phase channel {ch}',
                               unit='deg',
                               set_cmd=partial(self.set_channel_phase,
                                               channel_number=ch),
                               docstring=f'The phase of channel {ch}',
                               vals=validator.Numbers(0, 360))
            # TODO: validate the setting of amplitude and offset at the same time (-1.5<amp+offset<1.5)
            self.add_parameter(f'amplitude_channel_{ch}',
                               label=f'amplitude channel {ch}',
                               unit='V',
                               set_cmd=partial(self.set_channel_amplitude,
                                               channel_number=ch),
                               docstring=f'The amplitude of channel {ch}',
                               vals=validator.Numbers(-1.5, 1.5))
            self.add_parameter(f'offset_channel_{ch}',
                               label=f'offset channel {ch}',
                               unit='V',
                               set_cmd=partial(self.set_channel_offset,
                                               channel_number=ch),
                               docstring=f'The DC offset of channel {ch}',
                               vals=validator.Numbers(-1.5, 1.5))
            self.add_parameter(f'wave_shape_channel_{ch}',
                               label=f'wave shape channel {ch}',
                               set_cmd=partial(self.set_channel_wave_shape,
                                               channel_number=ch),
                               docstring=f'The output waveform type of '
                                         f'channel {ch}',
                               vals=validator.Enum(-1, 0, 1, 2, 4, 5, 6, 8))

        # initialize settings cache
        cache: Dict[str,Dict[int,Optional[float]]] = dict()
        for setting in ['offset', 'amplitude']:
            cache[setting] = {(i+index_offset):None for i in range(4)}

        self._settings_cache = cache

    #
    # Get-commands
    #

    def get_trigger_io(self, verbose: bool = False) -> int:
        """
        Reads and returns the trigger input

        Returns:
            Trigger input value, 0 (OFF) or 1 (ON), or negative numbers for
            errors
        """
        value = self.awg.triggerIOread()
        value_name = 'trigger_io'
        return result_parser(value, value_name, verbose)

    def get_clock_frequency(self, verbose: bool = False) -> int:
        """
        Returns the real hardware clock frequency (CLKsys)

        Returns:
            real hardware clock frequency in Hz, or negative numbers for errors
        """
        value = self.awg.clockGetFrequency()
        value_name = 'clock_frequency'
        return result_parser(value, value_name, verbose)

    def get_clock_sync_frequency(self, verbose: bool = False) -> int:
        """
        Returns the frequency of the internal CLKsync

        Returns:
            frequency of the internal CLKsync in Hz, or negative numbers for
            errors
        """
        value = self.awg.clockGetSyncFrequency()
        value_name = 'clock_sync_frequency'
        return result_parser(value, value_name, verbose)

    #
    # Set-commands
    #

    def set_clock_frequency(self, frequency: float,
                            verbose: bool = False) -> float:
        """
        Sets the module clock frequency

        Args:
            frequency: the frequency in Hz
            verbose: boolean indicating verbose mode

        Returns:
            the real frequency applied to the hardware in Hw, or negative
            numbers for errors
        """
        set_frequency = self.awg.clockSetFrequency(frequency)
        value_name = 'set_clock_frequency'
        return result_parser(set_frequency, value_name, verbose)

    def set_channel_frequency(self, frequency: int, channel_number: int,
                              verbose: bool = False) -> None:
        """
        Sets the frequency for the specified channel.
        The frequency is used for the periodic signals generated by the
        Function Generators.

        Args:
            channel_number: output channel number
            frequency: frequency in Hz
            verbose: boolean indicating verbose mode
        """
        with self._lock:
            value = self.awg.channelFrequency(channel_number, frequency)
        value_name = f'set frequency channel {channel_number} to {frequency} Hz'
        result_parser(value, value_name, verbose)

    def set_channel_phase(self, phase: int, channel_number: int,
                          verbose: bool = False) -> None:
        """
        Sets the phase for the specified channel.

        Args:
            channel_number: output channel number
            phase: phase in degrees
            verbose: boolean indicating verbose mode
        """
        with self._lock:
            value = self.awg.channelPhase(channel_number, phase)
        value_name = f'set phase channel {channel_number} to {phase} degrees'
        result_parser(value, value_name, verbose)

    def set_channel_amplitude(self, amplitude: float, channel_number: int,
                              verbose: bool = False) -> None:
        """
        Sets the amplitude for the specified channel.

        Args:
            channel_number: output channel number
            amplitude: amplitude in Volts
            verbose: boolean indicating verbose mode
        """
        if self._settings_cache['amplitude'][channel_number] == amplitude:
            return

        with self._lock:
            value = self.awg.channelAmplitude(channel_number, amplitude)
        value_name = f'set amplitude channel {channel_number} to {amplitude} V'
        result_parser(value, value_name, verbose)
        self._settings_cache['amplitude'][channel_number] = amplitude


    def set_channel_offset(self, offset: float, channel_number: int,
                           verbose: bool = False) -> None:
        """
        Sets the DC offset for the specified channel.

        Args:
            channel_number: output channel number
            offset: DC offset in Volts
            verbose: boolean indicating verbose mode
        """
        if self._settings_cache['offset'][channel_number] == offset:
            return
        with self._lock:
            value = self.awg.channelOffset(channel_number, offset)
        value_name = f'set offset channel {channel_number} to {offset} V'
        result_parser(value, value_name, verbose)
        self._settings_cache['offset'][channel_number] = offset

    def set_channel_wave_shape(self, wave_shape: int, channel_number: int,
                               verbose: bool = False) -> None:
        """
        Sets output waveform type for the specified channel.
            HiZ         :  -1 (only available for M3202A)
            No Signal   :   0
            Sinusoidal  :   1
            Triangular  :   2
            Square      :   4
            DC Voltage  :   5
            Arbitrary wf:   6
            Partner Ch. :   8

        Args:
            channel_number: output channel number
            wave_shape: wave shape type
            verbose: boolean indicating verbose mode
        """
        with self._lock:
            value = self.awg.channelWaveShape(channel_number, wave_shape)
        value_name = f'set wave shape channel {channel_number} to {wave_shape}'
        result_parser(value, value_name, verbose)

    def set_digital_filter_mode(self, filter_mode: SD_DigitalFilterModes) -> None:
        """
        Sets digital filter mode.

        Args:
            filter_mode: AOU_FILTER_OFF (0), AOU_FILTER_FLATNESS (1), AOU_FILTER_FIFTEEN_TAP (3)

        Note: AOU_FILTER_FIFTEEN_TAP is anti-ringing filter
        """
        result_parser(self.awg.setDigitalFilterMode(filter_mode),
                      f'filter_mode({filter_mode})')

    def set_trigger_io(self, value: int, verbose: bool = False) -> None:
        """
        Sets the trigger output. The trigger must be configured as output using
        config_trigger_io

        Args:
            value: Tigger output value: 0 (OFF), 1 (ON)
            verbose: boolean indicating verbose mode
        """
        result = self.awg.triggerIOwrite(value)
        value_name = f'set io trigger output to {value}'
        result_parser(result, value_name, verbose)

    def set_marker_config(self, channel_number: int, markerMode: int,
                          trgPXImask: int, trgIOmask: int, markerValue: int, syncMode: int, length: int,
                          delay: int) -> Any:
        """
        Configures the marker output from the trigger port

        Args:
            channel_number : trigger channel number
            markerMode : 0 disabled, 1 on start event, 2 On first sample of waveform (after starting delay), 3 on every cycle
            trgPXImask : Mask to select PXI triggers to use
            trgIOmask : Mask to select front panel triggers to use
            markerValue : 0 = marker signal is default low, pulses high. 1 = marker signal is default high, pulses low
            syncMode : 0 = syncronized to CLKsys. 1 = syncronized to 10MHz clock
            length : Marker pulse length (length * clock period * 5)
            delay : Delay to add before pulse (delay * clock period * 5)
        """
        result = self.awg.AWGqueueMarkerConfig(
            nAWG=channel_number,
            markerMode=markerMode,
            trgPXImask=trgPXImask,
            trgIOmask=trgIOmask,
            value=markerValue,
            syncMode=syncMode,
            length=length,
            delay=delay
        )
        return result

    #
    # The methods below are useful for controlling the device, but are not
    # used for setting or getting parameters
    #
    def off(self) -> None:
        """
        Stops the AWGs and sets the waveform of all channels to 'No Signal'
        """
        index_offset = 0 if self.legacy_channel_numbering else 1

        for i in range(self.channels):
            ch = i + index_offset
            awg_response = self.awg.AWGstop(ch)
            result_parser(awg_response, f'AWGstop({ch})')
            channel_response = self.awg.channelWaveShape(ch, SD_Waveshapes.AOU_OFF)
            result_parser(channel_response, f'channelWaveShape({ch}, SD_Waveshapes.AOU_OFF)')

    def reset_clock_phase(self, trigger_behaviour: int, trigger_source: int,
                          skew: float = 0.0, verbose: bool = False) -> None:
        """
        Sets the module in a sync state, waiting for the first trigger to
        reset the phase of the internal clocks CLKsync and CLKsys

        Args:
            trigger_behaviour: value indicating the trigger behaviour
                Active High     :   1
                Active Low      :   2
                Rising Edge     :   3
                Falling Edge    :   4

            trigger_source: value indicating external trigger source
                External I/O Trigger    :   0
                PXI Trigger [0..n]      :   4000+n

            skew: the skew between PXI_CLK10 and CLKsync in multiples of 10ns
            verbose: boolean indicating verbose mode
        """
        value = self.awg.clockResetPhase(trigger_behaviour,
                                         trigger_source, skew)
        value_name = f'reset_clock_phase trigger_behaviour:' \
                     f' {trigger_behaviour}, trigger_source:' \
                     f' {trigger_source}, skew: {skew}'
        result_parser(value, value_name, verbose)

    def reset_channel_phase(self, channel_number: int,
                            verbose: bool = False) -> None:
        """
        Resets the accumulated phase of the selected channel. This
        accumulated phase is the result of the phase continuous operation of
        the product.

        Args:
            channel_number: the number of the channel to reset
            verbose: boolean indicating verbose mode
        """
        value = self.awg.channelPhaseReset(channel_number)
        value_name = f'reset phase of channel {channel_number}'
        result_parser(value, value_name, verbose)

    def reset_multiple_channel_phase(self, channel_mask: int,
                                     verbose: bool = False) -> None:
        """
        Resets the accumulated phase of the selected channels simultaneously.

        Args:
            channel_mask: Mask to select the channel to reset (LSB is channel 0,
                bit 1 is channel 1 etc.)
            verbose: boolean indicating verbose mode

        Example:
            reset_multiple_channel_phase(5) would reset the phase of channel
            0 and 2
        """
        value = self.awg.channelPhaseResetMultiple(channel_mask)
        value_name = f'reset phase with channel mask {channel_mask}'
        result_parser(value, value_name, verbose)

    def config_angle_modulation(self, channel_number: int,
                                modulation_type: int, deviation_gain: int,
                                verbose: bool = False) -> None:
        """
        Configures the modulation in frequency/phase for the selected channel

        Args:
            channel_number: the number of the channel to configure
            modulation_type: the modulation type the AWG is used for
                No Modulation           :   0
                Frequency Modulation    :   1
                Phase Modulation        :   2
            deviation_gain: gain for the modulating signal
            verbose: boolean indicating verbose mode
        """
        value = self.awg.modulationAngleConfig(channel_number, modulation_type,
                                               deviation_gain)
        value_name = f'configure angle modulation of' \
                     f' channel {channel_number} modulation_type: ' \
                     f'{modulation_type}, deviation_gain: {deviation_gain}'
        result_parser(value, value_name, verbose)

    def config_amplitude_modulation(self, channel_number: int,
                                    modulation_type: int, deviation_gain: int,
                                    verbose: bool = False) -> None:
        """
        Configures the modulation in amplitude/offset for the selected channel

        Args:
            channel_number: the number of the channel to configure
            modulation_type: the modulation type the AWG is used for
                No Modulation           :   0
                Amplitude Modulation    :   1
                Offset Modulation       :   2
            deviation_gain: gain for the modulating signal
            verbose: boolean indicating verbose mode
        """
        value = self.awg.modulationAmplitudeConfig(channel_number,
                                                   modulation_type,
                                                   deviation_gain)
        value_name = f'configure amplitude modulation of channel' \
                     f' {channel_number} modulation_type: {modulation_type}, ' \
                     f'deviation_gain: {deviation_gain}'
        result_parser(value, value_name, verbose)

    def set_iq_modulation(self, channel_number: int, enable: int,
                          verbose: bool = False) -> None:
        """
        Sets the IQ modulation for the selected channel

        Args:
            channel_number: the number of the channel to configure
            enable: Enable (1) or Disable (0) the IQ modulation
            verbose: boolean indicating verbose mode
        """
        value = self.awg.modulationIQconfig(channel_number, enable)
        status = 'Enabled (1)' if enable == 1 else 'Disabled (0)'
        value_name = f'set IQ modulation for channel {channel_number} to ' \
                     f'{status}'
        result_parser(value, value_name, verbose)

    def config_clock_io(self, clock_config: int, verbose: bool = False) -> None:
        """
        Configures the operation of the clock output connector (CLK)

        Args:
            clock_config: clock connector function
                Disable         :   0   (The CLK connector is disabled)
                CLKref Output   :   1   (A copy of the reference clock is
                available at the CLK connector)
            verbose: boolean indicating verbose mode
        """
        value = self.awg.clockIOconfig(clock_config)
        status = 'CLKref Output (1)' if clock_config == 1 else 'Disabled (0)'
        value_name = f'configure clock output connector to {status}'
        result_parser(value, value_name, verbose)

    def config_trigger_io(self, direction: int, sync_mode: int,
                          verbose: bool = False) -> None:
        """
        Configures the trigger connector/line direction and
        synchronization/sampling method

        Args:
            direction: input (1) or output (0)
            sync_mode: sampling/synchronization mode
                Non-synchronized mode   :   0   (trigger is sampled with
                internal 100 Mhz clock)
                Synchronized mode       :   1   (trigger is sampled using CLK10)
            verbose: boolean indicating verbose mode
        """
        value = self.awg.triggerIOconfig(direction, sync_mode)
        status = 'input (1)' if direction == 1 else 'output (0)'
        value_name = f'configure trigger io port to direction: {status}, ' \
                     f'sync_mode: {sync_mode}'
        result_parser(value, value_name, verbose)

    #
    # Waveform related functions
    #

    def load_waveform(self, waveform_object: SD_Wave, waveform_number: int,
                      verbose: bool = False) -> int:
        """
        Loads the specified waveform into the module onboard RAM.
        Waveforms must be created first as an instance of the SD_Wave class.

        Args:
            waveform_object: pointer to the waveform object
            waveform_number: waveform number to identify the waveform in
                subsequent related function calls.
            verbose: boolean indicating verbose mode

        Returns:
            available onboard RAM in waveform points, or negative numbers for
                errors
        """
        # Lock to avoid concurrent access of waveformLoad()/waveformReLoad()
        with self._lock:
            value = self.awg.waveformLoad(waveform_object, waveform_number)
        value_name = f'load_waveform_int({waveform_number})'
        return result_parser(value, value_name, verbose)

    def load_waveform_int16(self, waveform_type: int, data_raw: List[int],
                            waveform_number: int, verbose: bool = False) -> int:
        """
        Loads the specified waveform into the module onboard RAM.
        Waveforms must be created first as an instance of the SD_Wave class.

        Args:
            waveform_type: waveform type
            data_raw: array with waveform points
            waveform_number: waveform number to identify the waveform
                in subsequent related function calls.
            verbose: boolean indicating verbose mode

        Returns:
            available onboard RAM in waveform points, or negative numbers for
                errors
        """
        # Lock to avoid concurrent access of waveformLoad()/waveformReLoad()
        with self._lock:
            value = self.awg.waveformLoadInt16(waveform_type, data_raw,
                                               waveform_number)
        value_name = f'load_waveform_int16({waveform_number})'
        return result_parser(value, value_name, verbose)

    def reload_waveform(self, waveform_object: SD_Wave, waveform_number: int,
                        padding_mode: int = 0, verbose: bool = False) -> int:
        """
        Replaces a waveform located in the module onboard RAM.
        The size of the new waveform must be smaller than or
        equal to the existing waveform.

        Args:
            waveform_object: pointer to the waveform object
            waveform_number: waveform number to identify the waveform
                in subsequent related function calls.
            padding_mode:
                0:  the waveform is loaded as it is, zeros are added at the
                    end if the number of points is not a multiple of the number
                    required by the AWG.
                1:  the waveform is loaded n times (using DMA) until the total
                    number of points is multiple of the number required by the
                    AWG. (only works for waveforms with even number of points)
            verbose: boolean indicating verbose mode

        Returns:
            available onboard RAM in waveform points, or negative numbers for
                errors
        """
        # Lock to avoid concurrent access of waveformLoad()/waveformReLoad()
        with self._lock:
            value = self.awg.waveformReLoad(waveform_object, waveform_number,
                                            padding_mode)
        value_name = f'reload_waveform({waveform_number})'
        return result_parser(value, value_name, verbose)

    def reload_waveform_int16(self, waveform_type: int, data_raw: List[int],
                              waveform_number: int, padding_mode: int = 0,
                              verbose: bool = False) -> int:
        """
        Replaces a waveform located in the module onboard RAM.
        The size of the new waveform must be smaller than or
        equal to the existing waveform.

        Args:
            waveform_type: waveform type
            data_raw: array with waveform points
            waveform_number: waveform number to identify the waveform
                in subsequent related function calls.
            padding_mode:
                0:  the waveform is loaded as it is, zeros are added at the
                    end if the number of points is not a multiple of the number
                    required by the AWG.
                1:  the waveform is loaded n times (using DMA) until the total
                    number of points is multiple of the number required by the
                    AWG. (only works for waveforms with even number of points)
            verbose: boolean indicating verbose mode

        Returns:
            available onboard RAM in waveform points, or negative numbers for
                errors
        """
        # Lock to avoid concurrent access of waveformLoad()/waveformReLoad()
        with self._lock:
            value = self.awg.waveformReLoadArrayInt16(waveform_type, data_raw,
                                                      waveform_number,
                                                      padding_mode)
        value_name = f'reload_waveform_int16({waveform_number})'
        return result_parser(value, value_name, verbose)

    def flush_waveform(self, verbose: bool = False) -> None:
        """
        Deletes all waveforms from the module onboard RAM and flushes all the
        AWG queues.
        """
        # Lock to avoid concurrent access of waveformLoad()/waveformReLoad()
        with self._lock:
            value = self.awg.waveformFlush()
        value_name = 'flushed AWG queue and RAM'
        result_parser(value, value_name, verbose)

    #
    # AWG related functions
    #

    def awg_from_file(self, awg_number: int, waveform_file: str,
                      trigger_mode: int, start_delay: int, cycles: int,
                      prescaler: int, padding_mode: int = 0,
                      verbose: bool = False) -> int:
        """
        Provides a one-step method to load, queue and start a single waveform
        in one of the module AWGs.

        Loads a waveform from file.

        Args:
            awg_number: awg number where the waveform is queued
            waveform_file: file containing the waveform points
            trigger_mode: trigger method to launch the waveform
                Auto                        :   0
                Software/HVI                :   1
                Software/HVI (per cycle)    :   5
                External trigger            :   2
                External trigger (per cycle):   6
            start_delay: defines the delay between trigger and wf launch
                given in multiples of 10ns.
            cycles: number of times the waveform is repeated once launched
                zero = infinite repeats
            prescaler: waveform prescaler value, to reduce eff. sampling rate

        Returns:
            available onboard RAM in waveform points, or negative numbers for
                errors
        """
        # Lock to avoid concurrent access of waveformLoad()/waveformReLoad()
        with self._lock:
            value = self.awg.AWGFromFile(awg_number, waveform_file,
                                         trigger_mode, start_delay, cycles,
                                         prescaler, padding_mode)
        value_name = 'AWG from file. available_RAM'
        return result_parser(value, value_name, verbose)

    def awg_from_array(self, awg_number: int, trigger_mode: int,
                       start_delay: int, cycles: int, prescaler: int,
                       waveform_type: int,
                       waveform_data_a: List[Union[int, float]],
                       waveform_data_b: Optional[
                           List[Union[int, float]]] = None,
                       padding_mode: int = 0, verbose: bool = False) -> int:
        """
        Provides a one-step method to load, queue and start a single waveform
        in one of the module AWGs.

        Loads a waveform from array.

        Args:
            awg_number: awg number where the waveform is queued
            trigger_mode: trigger method to launch the waveform
                Auto                        :   0
                Software/HVI                :   1
                Software/HVI (per cycle)    :   5
                External trigger            :   2
                External trigger (per cycle):   6
            start_delay: defines the delay between trigger and wf launch
                given in multiples of 10ns.
            cycles: number of times the waveform is repeated once launched
                zero = infinite repeats
            prescaler: waveform prescaler value, to reduce eff. sampling rate
            waveform_type: waveform type
            waveform_data_a: array with waveform points
            waveform_data_b: array with waveform points, only for the waveforms
                                        which have a second component

        Returns:
            available onboard RAM in waveform points, or negative numbers for
                errors
        """
        # Lock to avoid concurrent access of waveformLoad()/waveformReLoad()
        with self._lock:
            value = self.awg.AWGfromArray(awg_number, trigger_mode, start_delay,
                                          cycles, prescaler, waveform_type,
                                          waveform_data_a, waveform_data_b,
                                          padding_mode)
        value_name = 'AWG from file. available_RAM'
        return result_parser(value, value_name, verbose)

    def awg_queue_waveform(self, awg_number: int, waveform_number: int,
                           trigger_mode: int, start_delay: int, cycles: int,
                           prescaler: int) -> None:
        """
        Queues the specified waveform in one of the AWGs of the module.
        The waveform must be already loaded in the module onboard RAM.
        """
        with self._lock:
            result = self.awg.AWGqueueWaveform(awg_number, waveform_number,
                                               trigger_mode, start_delay, cycles,
                                               prescaler)
        result_parser(result,
                      f'AWGqueueWaveform({awg_number}, {waveform_number})')

    def awg_queue_config(self, awg_number: int, mode: int) -> None:
        """
        Configures the cyclic mode of the queue. All waveforms must be
        already queued in one of the AWGs

        Args:
            awg_number: awg number where the waveform is queued
            mode: operation mode of the queue: One Shot (0), Cyclic (1)
        """
        with self._lock:
            result = self.awg.AWGqueueConfig(awg_number, mode)
        result_parser(result, f'AWGqueueConfig({awg_number}, {mode})')

    def awg_flush(self, awg_number: int) -> None:
        """
        Empties the queue of the selected AWG.
        Waveforms are not removed from the onboard RAM.
        """
        with self._lock:
            result = self.awg.AWGflush(awg_number)
        result_parser(result, f'AWGflush({awg_number})')

    def awg_start(self, awg_number: int) -> None:
        """
        Starts the selected AWG from the beginning of its queue.
        The generation will start immediately or when a trigger is received,
        depending on the trigger selection of the first waveform in the queue
        and provided that at least one waveform is queued in the AWG.
        """
        with self._lock:
            result = self.awg.AWGstart(awg_number)
        result_parser(result, f'AWGstart({awg_number})')

    def awg_start_multiple(self, awg_mask: int) -> None:
        """
        Starts the selected AWGs from the beginning of their queues.
        The generation will start immediately or when a trigger is received,
        depending on the trigger selection of the first waveform in their queues
        and provided that at least one waveform is queued in these AWGs.

        Args:
            awg_mask: Mask to select the awgs to start (LSB is awg 0,
                bit 1 is awg 1 etc.)
        """
        with self._lock:
            result = self.awg.AWGstartMultiple(awg_mask)
        result_parser(result, f'AWGstartMultiple({awg_mask})')

    def awg_pause(self, awg_number: int) -> None:
        """
        Pauses the selected AWG, leaving the last waveform point at the output,
        and ignoring all incoming triggers.
        The waveform generation can be resumed calling awg_resume
        """
        with self._lock:
            result = self.awg.AWGpause(awg_number)
        result_parser(result, f'AWGpause({awg_number})')

    def awg_pause_multiple(self, awg_mask: int) -> None:
        """
        Pauses the selected AWGs, leaving the last waveform point at the output,
        and ignoring all incoming triggers.
        The waveform generation can be resumed calling awg_resume_multiple

        Args:
            awg_mask: Mask to select the awgs to pause (LSB is awg 0,
                bit 1 is awg 1 etc.)
        """
        with self._lock:
            result = self.awg.AWGpauseMultiple(awg_mask)
        result_parser(result, f'AWGpauseMultiple({awg_mask})')

    def awg_resume(self, awg_number: int) -> None:
        """
        Resumes the selected AWG, from the current position of the queue.
        """
        with self._lock:
            result = self.awg.AWGresume(awg_number)
        result_parser(result, f'AWGresume({awg_number})')

    def awg_resume_multiple(self, awg_mask: int) -> None:
        """
        Resumes the selected AWGs, from the current positions of their
        respective queue.

        Args:
            awg_mask: Mask to select the awgs to resume (LSB is awg 0,
                bit 1 is awg 1 etc.)
        """
        with self._lock:
            result = self.awg.AWGresumeMultiple(awg_mask)
        result_parser(result, f'AWGresumeMultiple({awg_mask})')

    def awg_stop(self, awg_number: int) -> None:
        """
        Stops the selected AWG, setting the output to zero and resetting the
        AWG queue to its initial position.
        All following incoming triggers are ignored.
        """
        with self._lock:
            result = self.awg.AWGstop(awg_number)
        result_parser(result, f'AWGstop({awg_number})')

    def awg_stop_multiple(self, awg_mask: int) -> None:
        """
        Stops the selected AWGs, setting their output to zero and resetting
        their AWG queues to the initial positions.
        All following incoming triggers are ignored.

        Args:
            awg_mask: Mask to select the awgs to stop (LSB is awg 0, bit 1 is
                awg 1 etc.)
        """
        with self._lock:
            result = self.awg.AWGstopMultiple(awg_mask)
        result_parser(result, f'AWGstopMultiple({awg_mask})')

    def awg_jump_next_waveform(self, awg_number: int) -> None:
        """
        Forces a jump to the next waveform in the awg queue.
        The jump is executed once the current waveform has finished a
        complete cycle.
        """
        with self._lock:
            result = self.awg.AWGjumpNextWaveform(awg_number)
        result_parser(result, f'AWGjumpNextWaveform({awg_number})')

    def awg_config_external_trigger(self, awg_number: int, external_source: int,
                                    trigger_behaviour: int) -> None:
        """
        Configures the external triggers for the selected awg.
        The external trigger is used in case the waveform is queued with th
        external trigger mode option.

        Args:
            awg_number: awg number
            external_source: value indicating external trigger source
                External I/O Trigger    :   0
                PXI Trigger [0..n]      :   4000+n
            trigger_behaviour: value indicating the trigger behaviour
                Active High     :   1
                Active Low      :   2
                Rising Edge     :   3
                Falling Edge    :   4
        """
        result = self.awg.AWGtriggerExternalConfig(awg_number, external_source,
                                                   trigger_behaviour)
        result_parser(result, f'AWGtriggerExternalConfig({awg_number})')

    def awg_trigger(self, awg_number: int) -> None:
        """
        Triggers the selected AWG.
        The waveform waiting in the current position of the queue is launched,
        provided it is configured with VI/HVI Trigger.
        """
        result = self.awg.AWGtrigger(awg_number)
        result_parser(result, f'AWGtrigger({awg_number})')

    def awg_trigger_multiple(self, awg_mask: int) -> None:
        """
        Triggers the selected AWGs.
        The waveform waiting in the current position of the queue is launched,
        provided it is configured with VI/HVI Trigger.

        Args:
            awg_mask: Mask to select the awgs to be triggered (LSB is awg 0,
                bit 1 is awg 1 etc.)
        """
        result = self.awg.AWGtriggerMultiple(awg_mask)
        result_parser(result, f'AWGtriggerMultiple({awg_mask})')

    def awg_is_running(self, channel: int) -> bool:
        """
        Returns True if awg on `channel` is running.
        """
        with self._lock:
            return self.awg.AWGisRunning(channel)

    #
    # Functions related to creation of SD_Wave objects
    #

    @staticmethod
    def new_waveform_from_file(waveform_file: str) -> SD_Wave:
        """
        Creates a SD_Wave object from data points contained in a file.
        This waveform object is stored in the PC RAM, not in the onboard RAM.

        Args:
            waveform_file: file containing the waveform points

        Returns:
            pointer to the waveform object, or negative numbers for errors
        """
        wave = keysightSD1.SD_Wave()
        result = wave.newFromFile(waveform_file)
        result_parser(result)
        return wave

    @staticmethod
    def new_waveform_from_double(waveform_type: int,
                                 waveform_data_a: List[float],
                                 waveform_data_b: Optional[List[float]] = None
                                 ) -> SD_Wave:
        """
        Creates a SD_Wave object from data points contained in an array.
        This waveform object is stored in the PC RAM, not in the onboard RAM.

        Args:
            waveform_type: waveform type
            waveform_data_a: array of (float) with waveform points
            waveform_data_b: array of (float) with waveform points, only for
                the waveforms which have a second component

        Returns:
            pointer to the waveform object, or negative numbers for errors
        """
        wave = keysightSD1.SD_Wave()
        result = wave.newFromArrayDouble(waveform_type, waveform_data_a,
                                         waveform_data_b)
        result_parser(result)
        return wave

    @staticmethod
    def new_waveform_from_int(waveform_type: int,
                              waveform_data_a: List[int],
                              waveform_data_b: Optional[List[int]] = None
                              ) -> SD_Wave:
        """
        Creates a SD_Wave object from data points contained in an array.
        This waveform object is stored in the PC RAM, not in the onboard RAM.

        Args:
            waveform_type: waveform type
            waveform_data_a: array of (int) with waveform points
            waveform_data_b: array of (int) with waveform points, only for
                the waveforms which have a second component

        Returns:
            pointer to the waveform object, or negative numbers for errors
        """
        wave = keysightSD1.SD_Wave()
        result = wave.newFromArrayInteger(waveform_type, waveform_data_a,
                                          waveform_data_b)
        result_parser(result)
        return wave

    @staticmethod
    def get_waveform_status(waveform: SD_Wave, verbose: bool = False) -> int:
        value = waveform.getStatus()
        value_name = 'waveform_status'
        return result_parser(value, value_name, verbose)

    @staticmethod
    def get_waveform_type(waveform: SD_Wave, verbose: bool = False) -> int:
        value = waveform.getType()
        value_name = 'waveform_type'
        return result_parser(value, value_name, verbose)

    def load_fpga_image(self, filename: str) -> None:
        """
        Loads specified image file in FPGA.

        Args:
            filename: name of image file to load
        """
        with self._lock:
            logging.info(f'loading fpga image "{filename}" ...')
            super().load_fpga_image(filename)
            logging.info(f'loaded fpga image.')

    def write_fpga(self, reg_name:str, value:int) -> None:
        """
        Writes a single 32-bit value to the specified FPGA register.

        Args:
            reg_name: name of register
            value: 32-bit value
        """
        with self._lock:
            reg = result_parser(self.awg.FPGAgetSandBoxRegister(reg_name),
                                reg_name)
            reg.writeRegisterInt32(value)

    def read_fpga(self, reg_name:str) -> int:
        """
        Reads a single 32-bit value from the specified FPGA register.

        Args:
            reg_name: name of register

        Returns:
            32-bit register value
        """
        with self._lock:
            reg = result_parser(self.awg.FPGAgetSandBoxRegister(reg_name),
                                reg_name)
            if reg.Address > 2**24 or reg.Address < 0:
                raise Exception(f'Register out of range: Reg {reg.Address:6} '
                                f'({reg.Length:6}) {reg_name}')
            return reg.readRegisterInt32()

    def write_fpga_array(self, reg_name:str, offset:int, data:List[int],
                         fixed_address:bool=False) -> None:
        """
        Writes a list of 32-bit values to the specified FPGA memory.

        Args:
            reg_name: name of memory
            offset: offset in memory block
            data: list of 32-bit values
            fixed_address:
                if True all data will be written sequentially to address specified by offset,
                else data will be written to consecutive addresses starting at offset
        """
        with self._lock:
            reg = result_parser(self.awg.FPGAgetSandBoxRegister(reg_name),
                                reg_name)
            result_parser(
                reg.writeRegisterBuffer(
                    offset, data,
                    keysightSD1.SD_AddressingMode.FIXED
                    if fixed_address else keysightSD1.SD_AddressingMode.AUTOINCREMENT,
                    keysightSD1.SD_AccessMode.DMA
                ),
                f'write_fpga_array({reg_name})'
            )

    def read_fpga_array(self, reg_name:str, offset:int, data_size:int,
                        fixed_address:bool=False) -> List[int]:
        """
        Reads a list of 32-bit values from the specified FPGA memory.

        Args:
            reg_name: name of memory
            offset: offset in memory block
            fixed_address:
                if True all data will be read sequentially from address specified by offset,
                else data will be read from consecutive addresses starting at offset

        Returns:
            list of 32-bit values
        """
        with self._lock:
            reg = result_parser(self.awg.FPGAgetSandBoxRegister(reg_name),
                                reg_name)
            data = result_parser(
                reg.readRegisterBuffer(
                    offset, data_size,
                    keysightSD1.SD_AddressingMode.FIXED
                    if fixed_address else keysightSD1.SD_AddressingMode.AUTOINCREMENT,
                    keysightSD1.SD_AccessMode.DMA
                ),
                f'read_fpga_array({reg_name})'
            )
            return data

    def config_fpga_trigger(self,
                            trigger:SD_TriggerExternalSources,
                            direction:SD_FpgaTriggerDirection,
                            polarity:SD_TriggerPolarity=SD_TriggerPolarity.ACTIVE_HIGH,
                            sync_mode:SD_SyncModes=SD_SyncModes.SYNC_NONE,
                            delay:int=0) -> None:
        """
        Configures external trigger for use in FPGA.

        Args:
            trigger: external trigger
            direction: IN = (0), INOUT (1)
            polarity: ACTIVE_LOW (0), ACTIVE_HIGH (1)
            sync_mode: SYNC_NONE (0), SYNC_CLK10 (1)
            delay: delay in steps of 5 ns.
        """
        with self._lock:
            result_parser(
                    self.awg.FPGATriggerConfig(trigger, direction, polarity, sync_mode, delay),
                    f'config_fpga_trigger({trigger})'
                    )

    def convert_sample_rate_to_prescaler(self, sample_rate: float) -> int:
        """
        Returns:
            prescaler: prescaler set to the awg.
        """
        if is_sd1_3x:
            # 0 = 1000e6, 1 = 200e6, 2 = 100e6, 3=66.7e6
            # round towards the lower prescaler, unless the value is close to the higher one (margin 0.5 ns)
            prescaler = int(200e6/sample_rate + 0.1)
        else:
            # 0 = 1000e6, 1 = 200e6, 2 = 50e6, 3=33.3e6
            if sample_rate > 200e6:
                prescaler = 0
            elif sample_rate > 50e6:
                prescaler = 1
            else:
                # round towards the lower prescaler, unless the value is close to the higher one
                prescaler = int(100e6/sample_rate + 0.1)

        return prescaler

    def convert_prescaler_to_sample_rate(self, prescaler: int) -> float:
        """
        Args:
            prescaler: prescaler set to the awg.

        Returns:
            sample_rate: effective sample rate the AWG will be running
        """
        if is_sd1_3x:
            # 0 = 1000e6, 1 = 200e6, 2 = 100e6, 3=66.7e6
            if prescaler == 0:
                return 1e9
            else:
                return 200e6/prescaler
        else:
            # 0 = 1000e6, 1 = 200e6, 2 = 50e6, 3=33.3e6
            if prescaler == 0:
                return 1e9
            if prescaler == 1:
                return 200e6
            else:
                return 100e6/prescaler
