from collections import namedtuple
import logging
from typing import TYPE_CHECKING

from qcodes.validators import Bool

if TYPE_CHECKING:
    from typing_extensions import (
        Unpack,
    )

from qcodes.instrument import (
    VisaInstrument,
    VisaInstrumentKWArgs,
)

OUT="out"
IN="in"

log = logging.getLogger(__name__)


class PicoPST(VisaInstrument):
    """
    QCoDeS instrument driver for the Pico SCPI USBTMC LabTool (PST)
    ===============================================================

    Pico SCPI labTool (PST) is an ordinary,
    $4 Raspberry Pi Pico with specialized firmware from https://github.com/michaelstoops/pico_scpi_usbtmc_labtool.
    It works on Pico 1 and 1W,
    and may work on other RP2040 boards.

    It does not currently work on the Pico 2 series based on the RP2350 chip.

    Setup
    -----

    To get a PST:

    1. Acquire a `Raspberry Pi Pico`_ or compatible device.
    2. Acquire `the firmware (~80 KB on GitHub)`_.
       This code was tested against v0.01.
    3. Hold down the device's `BOOTSEL` button while plugging the Pico into USB.
       It will appear in your system as a USB mass storage device called RPI-RP2.
    4. Copy the firmware image to RPI-RP2.
       The device will reboot.
       Ignore your system's complaint about unsafely removing the device.
    5. Your device is now a PST instrument.
       You can power it up and down whenever you want.
       The firmware is stored in FLASH ROM and will remain until you change it with the BOOTSEL procedure.

    .. _Raspberry Pi Pico: https://www.raspberrypi.com/products/raspberry-pi-pico/
    .. _the firmware (~80 KB on GitHub): https://github.com/michaelstoops/pico_scpi_usbtmc_labtool/releases/download/v0.01/pico_scpi_usbtmc_labtool.uf2

    You should be able to find the PST on your system under the name "Pico SCPI labTool" (product ID 0x41C0),
    manufacturer "Pico" (vendor ID 0x1209).
    It implements the USB Test and Measurement Class,
    so it should work with any VISA library.

    The testing device appeared in NI VISA Interactive Control on MacOS as `USB0::0x1209::0x41C0::E660583883555B31::INSTR`.
    Your device should have a similar ID,
    but the fourth field is based on an internal hardware ID and will vary.

    Configuration
    -------------

    Inputs start in the disabled state.
    That's not to say they don't work,
    but depending on electrical conditions,
    you may not get what you expect.::

        PicoPST.inputs_enabled(True)

    There is no corresponding enablement for outputs.

    Parameters, GPIO, SCPI, and Pins
    --------------------------------

    The instrument's parameters are named for their GPIO blocks: GPxx,
    which are given by the chip manufacturer.
    The instrument driver maps these to These are mapped to SCPI commands,
    which use zero-based indices: OUTx, INx.

    The device firmware then maps the SCPI commands to GPIO blocks on the RP2040 chip.
    These could be configured differently,
    depending on the firmware build,
    so do be mindful.

    The circuit board then routes the GPIO blocks to edge pins.
    There is a helpful reference at https://pico.pinout.xyz/.
    Pico 1 and 1W are the same, but other boards vary.

    **IMPORTANT! Electrical Limits**

    See the Raspberry Pi Pico documentation (`5.5.3. Pin Specifications`_) for electrical characteristics of the pins.
    The quick summary is:
    * GPIO is between 0V and 3.3V.
      Voltages higher or lower will harm the device.
    * You must add current-limiting resistors of at least 470 ohms.
    * Do not pass more than 12 mA through any GPIO pin,
      nor more than 50 mA in all.

    .. _5.5.3. Pin Specifications: https://pip.raspberrypi.com/documents/RP-008371-DS#page=615

    For the `tested firmware`_,
    and the Raspberry Pi Pico 1 or 1W,
    the instrument parameters, SCPI command,
    GPIO block, and pins are as follows:

    .. _tested firmware: https://github.com/michaelstoops/pico_scpi_usbtmc_labtool/releases/download/v0.01/pico_scpi_usbtmc_labtool.uf2

    +----------------------+-----------------+------+----+
    | Instrument Parameter | SCPI Command    | GPIO | Pin|
    +======================+=================+======+====+
    | output_gp19          | DIGItal:OUTPut0 | GP19 | 25 |
    +----------------------+-----------------+------+----+
    | output_gp20          | DIGItal:OUTPut1 | GP20 | 26 |
    +----------------------+-----------------+------+----+
    | output_gp21          | DIGItal:OUTPut2 | GP21 | 27 |
    +----------------------+-----------------+------+----+
    | output_gp22          | DIGItal:OUTPut3 | GP22 | 29 |
    +----------------------+-----------------+------+----+
    | input_gp10           | DIGItal:INPut0  | GP10 | 14 |
    +----------------------+-----------------+------+----+
    | input_gp11           | DIGItal:INPut1  | GP11 | 15 |
    +----------------------+-----------------+------+----+
    | input_gp12           | DIGItal:INPut2  | GP11 | 16 |
    +----------------------+-----------------+------+----+
    | input_gp13           | DIGItal:INPut3  | GP11 | 17 |
    +----------------------+-----------------+------+----+

    The device firmware and this instrument driver were created by Michael Stoops.
    The firmware was developed from pico_scpi_usbtmc_labtool by Jan Cumps, who deserves much credit.
    See his `blog post on element14`_.
    The firmware uses `TinyUSB`_ by Ha Thach,
    and `scpi-parser`_ by Jan Breuer.

    .. _blog post on element14: https://community.element14.com/technologies/test-and-measurement/b/blog/posts/pst-program-the-pico-scpi-labtool
    .. _TinyUSB: https://github.com/hathach/tinyusb
    .. _scpi-parser: https://github.com/j123b567/scpi-parser
    """

    default_terminator = "\n"

    # Table of digital inputs/outputs parameters
    DigitalIO = namedtuple("DigitalIO","dir, scpi_num, gp, pico_pin")
    _digital_ios = [
        DigitalIO(OUT, 0, 19, 25),
        DigitalIO(OUT, 1, 20, 26),
        DigitalIO(OUT, 2, 21, 27),
        DigitalIO(OUT, 3, 22, 29),
        DigitalIO(IN, 0, 10, 14),
        DigitalIO(IN, 1, 11, 15),
        DigitalIO(IN, 2, 12, 16),
        DigitalIO(IN, 3, 13, 17),
    ]

    @staticmethod
    def _int_as_bool(*args, **kwargs) -> bool:
        return bool(int(*args, **kwargs))

    def __init__(
        self, name: str, address: str, **kwargs: "Unpack[VisaInstrumentKWArgs]"
    ):
        super().__init__(name, address, **kwargs)

        # Add digital IOs as parameters
        for io in self._digital_ios:
            parameter = self.add_parameter(
                f"{io.dir}put_gp{io.gp}",
                # Digital states are unitless
                unit="",
                set_cmd=f"DIGI:{io.dir.upper()}P{io.scpi_num} {{:d}}",
                get_cmd=f"DIGI:{io.dir.upper()}P{io.scpi_num}?",
                vals=Bool(),
                get_parser=self._int_as_bool,
                docstring=f"Turns GP{io.gp} (Pico pin {io.pico_pin}) on or off" if io.dir == IN else "Indicates whether GP20 (Pico pin 26) is on or off"
            )
            parameter.__doc__= f"Digital {io.dir.upper()}put GP{io.gp} (Pico pin {io.pico_pin})"
            setattr(self, f"output_{io.gp}", parameter)

        # Inputs must be enabled before they are used
        self.inputs_enabled = self.add_parameter(
            "inputs_enabled",
            unit="",
            set_cmd="STAT:OPER:DIGI:INP:ENAB {:d}",
            get_cmd="STAT:OPER:DIGI:INP:ENAB?",
            vals=Bool(),
            get_parser=self._int_as_bool,
            docstring="Enables or disables the use of inputs"
        )
        """Inputs Enabled"""

        # Other functions exist but are not implemented here.

        self.connect_message()
