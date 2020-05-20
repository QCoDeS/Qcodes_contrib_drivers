from qcodes import Instrument
from .APT import Thorlabs_APT, ThorlabsHWType


class Thorlabs_PRM1Z8(Instrument):
    """
    Instrument driver for the Thorlabs PRMZ1Z8 polarizer wheel.

    Args:
        name: Instrument name.
        device_id: ID for the desired polarizer wheel.
        apt: Thorlabs APT server.

    Attributes:
        apt: Thorlabs APT server.
        serial_number: Serial number of the polarizer wheel.
        model: Model description.
        version: Firmware version.
    """

    def __init__(self, name: str, device_id: int, apt: Thorlabs_APT, **kwargs):

        super().__init__(name, **kwargs)

        # save APT server link
        self.apt = apt

        # initialization
        self.serial_number: int = self.apt.get_hw_serial_num_ex(ThorlabsHWType.PRM1Z8, device_id)
        self.apt.init_hw_device(self.serial_number)
        self.model, self.version, _ = self.apt.get_hw_info(self.serial_number)

        # add parameters
        self.add_parameter('position',
                           get_cmd=self._get_position,
                           set_cmd=self._set_position,
                           unit=u"\u00b0",
                           label='Position')

        # print connect message
        self.connect_message()

    # get methods
    def get_idn(self):
        return {'vendor': 'Thorlabs', 'model': self.model,
                'firmware': self.version, 'serial': self.serial_number}

    def _get_position(self):
        return self.apt.mot_get_position(self.serial_number)

    # set methods
    def _set_position(self, position):
        self.apt.mot_move_absolute_ex(self.serial_number, position, True)
