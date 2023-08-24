from qcodes import Instrument
import qcodes.utils.validators as vals

from .Kinesis import Thorlabs_Kinesis


class Thorlabs_KLS1550(Instrument):
    def __init__(
        self,
        name: str,
        serial_number: str,
        polling_speed_ms: int,
        kinesis: Thorlabs_Kinesis,
        **kwargs,
    ):
        super().__init__(name, **kwargs)
        # Save Kinesis server reference
        self.kinesis = kinesis

        # Initialization
        self.serial_number = serial_number
        self.polling_speed_ms = polling_speed_ms
        self.kinesis.open_laser(self.serial_number)
        self.kinesis.start_polling(self.serial_number, self.polling_speed_ms)
        self.info = self.kinesis.laser_info(self.serial_number)
        self.model = self.info[0].value.decode("utf-8")
        self.version = self.info[4].value

        # Parameters
        self.add_parameter(
            "output_enabled",
            get_cmd=self._get_output_enabled,
            set_cmd=self._set_output_enabled,
            vals=vals.Bool(),
            unit="",
            label="Laser output on/off",
            docstring="Turn laser output on/off. Note that laser key switch must be on to turn laser output on.",
        )

        self.add_parameter(
            "power",
            get_cmd=self._get_power,
            set_cmd=self._set_power,
            vals=vals.Numbers(0, 0.007),  # [ATTENTION] max power for simulator is 10mW
            unit="W",
            label="Power output",
        )

        self.connect_message()

    def get_idn(self):
        return {
            "vendor": "Thorlabs",
            "model": self.model,
            "firmware": self.version,
            "serial": self.serial_number,
        }

    def _get_output_enabled(self):
        # First status bit represents 'output enabled'
        return bool(self.kinesis.laser_status_bits(self.serial_number) & 1)

    def _set_output_enabled(self, value: bool):
        if value:
            self.kinesis.laser_enable_output(self.serial_number)
        else:
            self.kinesis.laser_disable_output(self.serial_number)

    def _get_power(self):
        return self.kinesis.get_laser_power(self.serial_number)

    def _set_power(self, power_W: float):
        self.kinesis.set_laser_power(self.serial_number, power_W)

    def disconnect(self):
        self.kinesis.stop_polling(self.serial_number)
        self.kinesis.close_laser(self.serial_number)

    def close(self):
        self.disconnect()
        super().close()
