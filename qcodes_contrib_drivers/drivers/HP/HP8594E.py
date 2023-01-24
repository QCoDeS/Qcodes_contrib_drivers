import logging
from typing import Any, Dict
import struct
import numpy as np
import datetime
import qcodes.validators as vals
from qcodes.parameters import (
    Parameter,
    ParameterWithSetpoints,
    ParamRawDataType,
)
from qcodes.instrument import VisaInstrument
import numpy.typing as npt


class HP8594E(VisaInstrument):
    """
    This is the QCoDeS driver for the Hewlett Packard HP8594E Network Analyzer
    """

    def __init__(self, name: str, address: str, **kwargs: Any) -> None:
        super().__init__(name, address, terminator="\n", **kwargs)

        self.add_parameter(
            "start_freq",
            label="Sweep start frequency",
            unit="Hz",
            set_cmd="FA {} Hz",
            get_cmd="FA?",
            get_parser=float,
            vals=vals.Numbers(0, 2900000000.0),
        )

        self.add_parameter(
            "stop_freq",
            label="Sweep stop frequency",
            unit="Hz",
            set_cmd="FB {} Hz",
            get_cmd="FB?",
            get_parser=float,
            vals=vals.Numbers(0, 2900000000.0),
        )

        self.add_parameter(
            "center_freq",
            label="center frequency",
            unit="Hz",
            set_cmd="CF {} Hz",
            get_cmd="CF?",
            get_parser=float,
            vals=vals.Numbers(9000, 1800000000),
        )

        self.add_parameter(
            "span",
            label="span",
            unit="Hz",
            set_cmd="SP {} Hz",
            get_cmd="SP?",
            get_parser=float,
            vals=vals.Numbers(9000, 1800000000),
        )

        self.add_parameter(
            "sweep_time",
            label="sweep time",
            unit="s",
            set_cmd="ST {} sc",
            get_cmd="ST?",
            get_parser=float,
            vals=vals.Numbers(0, 4),
        )

        self.add_parameter(
            "resolution_bandwidth",
            label="resolution bandwidth",
            unit="Hz",
            set_cmd="RB {} HZ",
            get_cmd="RB?",
            get_parser=float,
            vals=vals.Numbers(300, 5000000.0),
        )

        self.add_parameter(
            "video_bandwidth",
            label="Video Bandwidth",
            unit="Hz",
            set_cmd="VB {} HZ",
            get_cmd="VB?",
            get_parser=float,
            vals=vals.Numbers(30, 3000000),
        )

        self.add_parameter(
            "attenuation",
            label="Attenuation",
            unit="dbm",
            set_cmd="AT {} DB",
            get_cmd="AT?",
            get_parser=float,
            vals=vals.Numbers(0, 30),
        )

        self.add_parameter(
            "reference_level",
            label="Reference Level",
            unit="dbm",
            set_cmd="RL {} DB",
            get_cmd="RL?",
            get_parser=float,
            vals=vals.Numbers(0, 30),
        )

        self.add_parameter(
            "freq_axis",
            parameter_class=FreqAxis,
            unit="Hz",
            vals=vals.Arrays(shape=(401,)),
        )

        self.add_parameter(
            "trace",
            parameter_class=Trace,
            unit="dBm",
            setpoints=(self.freq_axis,),
            vals=vals.Arrays(shape=(401,)),
        )

    def get_info(self) -> Dict:
        info = {}

        # get model/firmware info
        info["model"] = self.ask("ID?").strip()
        info["firmware_date"] = self.ask("REV?")  # firmware date
        info["serial_number"] = self.ask("SER?")  # firmware date

        # get uptime
        uptime_str = self.ask("PWRUPTIME?").strip()  # in ms
        info["uptime"] = str(datetime.timedelta(seconds=float(uptime_str) / 1e3))

        return info

    def reset(self):
        # preset state
        self.write("IP")

        # single sweep mode
        self.write("SNGLS")

        # set date/time and display on instrument
        datetime_str = datetime.datetime.now().strftime("%y%m%d%H%M%S")
        self.write(f"TIMEDATE {datetime_str}")
        self.write("TIMEDSP ON")


class FreqAxis(Parameter):
    """ """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def get_raw(self) -> ParamRawDataType:
        assert isinstance(self.root_instrument, HP8594E)
        start = self.root_instrument.start_freq()
        stop = self.root_instrument.stop_freq()
        return np.linspace(start, stop, 401)


class Trace(ParameterWithSetpoints):
    """ """

    def __init__(self, transfer_type: str = "bytes", *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.transfer_type = transfer_type

        if not isinstance(self.root_instrument, HP8594E):
            raise TypeError("Root instrument must be HP8594E")
        else:
            self.hp8594e = self.root_instrument

    def get_raw(self) -> ParamRawDataType:
        self.hp8594e.write("SNGLS")
        if self.transfer_type == "ASCII":
            return self.transfer_ascii()
        elif self.transfer_type == "bytes":
            return self.transfer_bytes()
        else:
            raise ValueError(
                f"transfer_type must be bytes or ASCII you have used {self.transfer_type} "
            )

    def transfer_ascii(self) -> npt.NDArray[np.float_]:
        data = self.hp8594e.ask("TS;TDF P;TRA?;")
        return np.array([float(x) for x in data.split(",")])

    def transfer_bytes(self) -> npt.NDArray[np.float_]:
        self.hp8594e.write("TDF B")
        self.hp8594e.write("MDS B")
        self.hp8594e.write("TS;TRA?")
        data_bytes = self.hp8594e.visa_handle.read_raw()
        data_int = struct.unpack(">401B", data_bytes)
        ref_level = self.hp8594e.reference_level()
        data_float = [(x * 32 - 8000) * 0.01 + ref_level for x in data_int]
        return np.array(data_float)
