from functools import partial
from typing import Optional

from qcodes import Instrument
import socket, nanonis_tramea_specs
"""
IMPORTANT

Before using the Driver, you must have our python package installed, because many of functions in this driver are merely
wrapper functions of functions from said package. How to install:

pip install nanonis-tramea-specs
"""


class NanonisTramea(Instrument):
    # log = logging.getLogger(__name__)

    def __init__(self, name: str, address: str, port: int, **kwargs):
        super().__init__(name, **kwargs)

        self._address = address
        self._port = port

        self.model = "SPM"
        self.serial = 1234
        self.firmware = 1

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self._address, self._port))

        self.n = nanonis_tramea_specs.Nanonis(self._socket)
        # self.n.Bias_Set(np.float32(1.2))

        self.add_parameter(
            "Output1",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(1, 1)[2])[0]
        )

        self.add_parameter(
            "Output2",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(2, 1)[2])[0]
        )

        self.add_parameter(
            "Output3",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(3, 1)[2])[0]
        )

        self.add_parameter(
            "Output4",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(4, 1)[2])[0]
        )

        self.add_parameter(
            "Output5",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(5, 1)[2])[0]
        )

        self.add_parameter(
            "Output6",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(6, 1)[2])[0]
        )

        self.add_parameter(
            "Output7",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(7, 1)[2])[0]
        )

        self.add_parameter(
            "Output8",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(8, 1)[2])[0]
        )

        self.add_parameter(
            "Output9",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(9, 1)[2])[0]
        )

        self.add_parameter(
            "Output10",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(10, 1)[2])[0]
        )

        self.add_parameter(
            "Output11",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(11, 1)[2])[0]
        )

        self.add_parameter(
            "Output12",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(12, 1)[2])[0]
        )

        self.add_parameter(
            "Output13",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(13, 1)[2])[0]
        )

        self.add_parameter(
            "Output14",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(14, 1)[2])[0]
        )

        self.add_parameter(
            "Output15",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(15, 1)[2])[0]
        )

        self.add_parameter(
            "Output16",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(16, 1)[2])[0]
        )

        self.add_parameter(
            "Output17",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(17, 1)[2])[0]
        )

        self.add_parameter(
            "Output18",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(18, 1)[2])[0]
        )

        self.add_parameter(
            "Output19",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(19, 1)[2])[0]
        )

        self.add_parameter(
            "Output20",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(20, 1)[2])[0]
        )

        self.add_parameter(
            "Output21",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(21, 1)[2])[0]
        )

        self.add_parameter(
            "Output22",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(22, 1)[2])[0]
        )
        self.add_parameter(
            "Output23",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(23, 1)[2])[0]
        )

        self.add_parameter(
            "Output24",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(24, 1)[2])[0]
        )

        self.add_parameter(
            "Output25",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(25, 1)[2])[0]
        )

        self.add_parameter(
            "Output26",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(26, 1)[2])[0]
        )

        self.add_parameter(
            "Output27",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(27, 1)[2])[0]
        )

        self.add_parameter(
            "Output28",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(28, 1)[2])[0]
        )

        self.add_parameter(
            "Output29",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(29, 1)[2])[0]
        )

        self.add_parameter(
            "Output30",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(30, 1)[2])[0]
        )

        self.add_parameter(
            "Output31",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(31, 1)[2])[0]
        )

        self.add_parameter(
            "Output32",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(32, 1)[2])[0]
        )

        self.add_parameter(
            "Output33",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(33, 1)[2])[0]
        )

        self.add_parameter(
            "Output34",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(34, 1)[2])[0]
        )

        self.add_parameter(
            "Output35",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(35, 1)[2])[0]
        )

        self.add_parameter(
            "Output36",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(36, 1)[2])[0]
        )

        self.add_parameter(
            "Output37",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(37, 1)[2])[0]
        )

        self.add_parameter(
            "Output38",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(38, 1)[2])[0]
        )

        self.add_parameter(
            "Output39",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(39, 1)[2])[0]
        )

        self.add_parameter(
            "Output40",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(40, 1)[2])[0]
        )

        self.add_parameter(
            "Output41",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(41, 1)[2])[0]
        )

        self.add_parameter(
            "Output42",
            set_cmd=self.partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(42, 1)[2])[0]
        )

        self.add_parameter(
            "Output43",
            set_cmd=self.partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(43, 1)[2])[0]
        )

        self.add_parameter(
            "Output44",
            set_cmd=self.partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(44, 1)[2])[0]
        )

        self.add_parameter(
            "Output45",
            set_cmd=self.partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(45, 1)[2])[0]
        )

        self.add_parameter(
            "Output46",
            set_cmd=self.partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(46, 1)[2])[0]
        )
        self.add_parameter(
            "Output47",
            set_cmd=self.partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(47, 1)[2])[0]
        )

        self.add_parameter(
            "Output48",
            set_cmd=self.partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(48, 1)[2])[0]
        )

        self.add_parameter(
            "Output49",
            set_cmd=self.partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(49, 1)[2])[0]
        )

        self.add_parameter(
            "Output50",
            set_cmd=partial(self.n.UserOut_ValSet, 1),
            get_cmd=(self.n.Signals_ValGet(50, 1)[2])[0]
        )
        self.add_parameter(
            "Input0",
            get_cmd=(self.n.Signals_ValGet(1, 1)[2])[0]
        )


        self.add_parameter(
            "Input1",
            get_cmd=(self.n.Signals_ValGet(2, 1)[2])[0]
        )

        self.add_parameter(
            "Input2",
            get_cmd=(self.n.Signals_ValGet(3, 1)[2])[0]
        )

        self.add_parameter(
            "Input3",
            get_cmd=(self.n.Signals_ValGet(4, 1)[2])[0]
        )

        self.add_parameter(
            "Input4",
            get_cmd=(self.n.Signals_ValGet(5, 1)[2])[0]
        )

        self.add_parameter(
            "Input5",
            get_cmd=(self.n.Signals_ValGet(6, 1)[2])[0]
        )

        self.add_parameter(
            "Input6",
            get_cmd=(self.n.Signals_ValGet(7, 1)[2])[0]
        )
        self.add_parameter(
            "Input7",
            get_cmd=(self.n.Signals_ValGet(8, 1)[2])[0]
        )

        self.add_parameter(
            "Input8",
            get_cmd=(self.n.Signals_ValGet(9, 1)[2])[0]
        )

        self.add_parameter(
            "Input9",
            get_cmd=(self.n.Signals_ValGet(10, 1)[2])[0]
        )

        self.add_parameter(
            "Input10",
            get_cmd=(self.n.Signals_ValGet(11, 1)[2])[0]
        )

        self.add_parameter(
            "Input11",
            get_cmd=(self.n.Signals_ValGet(12, 1)[2])[0]
        )

        self.add_parameter(
            "Input12",
            get_cmd=(self.n.Signals_ValGet(13, 1)[2])[0]
        )

        self.add_parameter(
            "Input13",
            get_cmd=(self.n.Signals_ValGet(14, 1)[2])[0]
        )

        self.add_parameter(
            "Input14",
            get_cmd=(self.n.Signals_ValGet(15, 1)[2])[0]
        )

        self.add_parameter(
            "Input15",
            get_cmd=(self.n.Signals_ValGet(16, 1)[2])[0]
        )

        self.add_parameter(
            "Input16",
            get_cmd=(self.n.Signals_ValGet(17, 1)[2])[0]
        )

        self.add_parameter(
            "Input17",
            get_cmd=(self.n.Signals_ValGet(18, 1)[2])[0]
        )

        self.add_parameter(
            "Input18",
            get_cmd=(self.n.Signals_ValGet(19, 1)[2])[0]
        )

        self.add_parameter(
            "Input19",
            get_cmd=(self.n.Signals_ValGet(20, 1)[2])[0]
        )

        self.add_parameter(
            "Input20",
            get_cmd=(self.n.Signals_ValGet(21, 1)[2])[0]
        )

        self.add_parameter(
            "Input21",
            get_cmd=(self.n.Signals_ValGet(22, 1)[2])[0]
        )

        self.add_parameter(
            "Input22",
            get_cmd=(self.n.Signals_ValGet(23, 1)[2])[0]
        )

        self.add_parameter(
            "Input23",
            get_cmd=(self.n.Signals_ValGet(24, 1)[2])[0]
        )

