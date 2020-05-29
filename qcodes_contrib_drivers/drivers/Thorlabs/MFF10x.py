from qcodes import Instrument
from .APT import Thorlabs_APT, ThorlabsHWType


class Thorlabs_MFF10x(Instrument):
    """
    Instrument driver for the Thorlabs MFF10x mirror flipper.

    Args:
        name: Instrument name.
        device_id: ID for the desired mirror flipper.
        apt: Thorlabs APT server.

    Attributes:
        apt: Thorlabs APT server.
        serial_number: Serial number of the mirror flipper.
        model: Model description.
        version: Firmware version.
    """

    def __init__(self, name: str, device_id: int, apt: Thorlabs_APT, **kwargs):

        super().__init__(name, **kwargs)

        # save APT server link
        self.apt = apt

        # initialization
        self.serial_number: int = self.apt.get_hw_serial_num_ex(ThorlabsHWType.MFF10x, device_id)
        self.apt.init_hw_device(self.serial_number)
        self.model, self.version, _ = self.apt.get_hw_info(self.serial_number)

        # add parameters
        self.add_parameter('position',
                           get_cmd=self._get_position,
                           set_cmd=self._set_position,
                           get_parser=int,
                           label='Position')

        # print connect message
        self.connect_message()

    # get methods
    def get_idn(self):
        return {'vendor': 'Thorlabs', 'model': self.model,
                'firmware': self.version, 'serial': self.serial_number}

    def _get_position(self):
        status_bits = bin(self.apt.mot_get_status_bits(self.serial_number) & 0xffffffff)
        return status_bits[-1]

    # set methods
    def _set_position(self, position):
        self.apt.mot_move_jog(self.serial_number, position+1, False)
