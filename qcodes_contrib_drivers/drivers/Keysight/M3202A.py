from .SD_common.SD_AWG import SD_AWG


class M3202A(SD_AWG):
    """
    qcodes driver for the Keysight M3202A AWG PXIe card.
    
    M3202A channel numbers start with 1.

    Args:
        name (str): name for this instrument, passed to the base instrument
        chassis (int): chassis number where the device is located
        slot (int): slot number where the device is plugged in
    """

    def __init__(self, name, chassis, slot, **kwargs):
        super().__init__(name, chassis, slot, channels=4, triggers=8, 
                         legacy_channel_numbering=False, **kwargs)

        module_name = self.__class__.__name__
        if self.module_name != module_name:
            raise Exception(f"Found module '{self.module_name}' in chassis {chassis} slot {slot}; expected '{module_name}'")
