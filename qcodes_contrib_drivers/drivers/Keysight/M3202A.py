from .SD_common.SD_AWG_Async import SD_AWG_Async


class M3202A(SD_AWG_Async):
    """
    qcodes driver for the Keysight M3202A AWG PXIe card.

    M3202A channel numbers start with 1.

    This driver is derived from SD_AWG_Async which uses a thread per module to
    upload waveforms concurrently. The sychronous methods like load_waveform are
    not available in this class.

    Example:
        awg1 = M3202A('awg1', 0, 2)
        ref_1 = awg1.upload_waveform(wave1)

        trigger_mode = keysightSD1.SD_TriggerModes.EXTTRIG
        awg1.awg_queue_waveform(1, ref_1, trigger_mode, 0, 1, 0)

    If you want to test M3202A based on the synchronous SD_AWG, then you can
    instantiate SD_AWG directly.
    Example:
        m3202a_sync = SD_AWG(name, chassis, slot, channels=4, triggers=8,
                             legacy_channel_numbering=False)

    Args:
        name: name for this instrument, passed to the base instrument
        chassis: chassis number where the device is located
        slot: slot number where the device is plugged in
    """
    def __init__(self, name: str, chassis: int, slot: int, **kwargs):
        super().__init__(name, chassis, slot, channels=4, triggers=8,
                         legacy_channel_numbering=False, **kwargs)

        module_name = 'M3202A'
        if self.module_name != module_name:
            raise Exception(f"Found module '{self.module_name}' in chassis "
                            f"{chassis} slot {slot}; expected '{module_name}'")
