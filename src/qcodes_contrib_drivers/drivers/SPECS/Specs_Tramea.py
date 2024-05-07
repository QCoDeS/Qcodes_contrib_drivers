from typing import Optional

from qcodes import Instrument
import socket, nanonis_tramea_specs
import numpy as np
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
            set_cmd=self.UserOut_ValSet1,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output2",
            set_cmd=self.UserOut_ValSet2,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output3",
            set_cmd=self.UserOut_ValSet3,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output4",
            set_cmd=self.UserOut_ValSet4,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output5",
            set_cmd=self.UserOut_ValSet5,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output6",
            set_cmd=self.UserOut_ValSet6,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output7",
            set_cmd=self.UserOut_ValSet7,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output8",
            set_cmd=self.UserOut_ValSet8,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output9",
            set_cmd=self.UserOut_ValSet9,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output10",
            set_cmd=self.UserOut_ValSet10,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output11",
            set_cmd=self.UserOut_ValSet11,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output12",
            set_cmd=self.UserOut_ValSet12,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output13",
            set_cmd=self.UserOut_ValSet13,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output14",
            set_cmd=self.UserOut_ValSet14,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output15",
            set_cmd=self.UserOut_ValSet15,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output16",
            set_cmd=self.UserOut_ValSet16,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output17",
            set_cmd=self.UserOut_ValSet17,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output18",
            set_cmd=self.UserOut_ValSet18,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output19",
            set_cmd=self.UserOut_ValSet19,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output20",
            set_cmd=self.UserOut_ValSet20,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output21",
            set_cmd=self.UserOut_ValSet21,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output22",
            set_cmd=self.UserOut_ValSet22,
            get_cmd=self.Signals_ValGet24,
        )
        self.add_parameter(
            "Output23",
            set_cmd=self.UserOut_ValSet23,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output24",
            set_cmd=self.UserOut_ValSet24,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output25",
            set_cmd=self.UserOut_ValSet25,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output26",
            set_cmd=self.UserOut_ValSet26,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output27",
            set_cmd=self.UserOut_ValSet27,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output28",
            set_cmd=self.UserOut_ValSet28,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output29",
            set_cmd=self.UserOut_ValSet29,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output30",
            set_cmd=self.UserOut_ValSet30,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output31",
            set_cmd=self.UserOut_ValSet31,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output32",
            set_cmd=self.UserOut_ValSet32,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output33",
            set_cmd=self.UserOut_ValSet33,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output34",
            set_cmd=self.UserOut_ValSet34,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output35",
            set_cmd=self.UserOut_ValSet35,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output36",
            set_cmd=self.UserOut_ValSet36,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output37",
            set_cmd=self.UserOut_ValSet37,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output38",
            set_cmd=self.UserOut_ValSet38,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output39",
            set_cmd=self.UserOut_ValSet39,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output40",
            set_cmd=self.UserOut_ValSet40,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output41",
            set_cmd=self.UserOut_ValSet41,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output42",
            set_cmd=self.UserOut_ValSet42,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output43",
            set_cmd=self.UserOut_ValSet43,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output44",
            set_cmd=self.UserOut_ValSet44,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output45",
            set_cmd=self.UserOut_ValSet45,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output46",
            set_cmd=self.UserOut_ValSet46,
            get_cmd=self.Signals_ValGet24,
        )
        self.add_parameter(
            "Output47",
            set_cmd=self.UserOut_ValSet47,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output48",
            set_cmd=self.UserOut_ValSet48,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output49",
            set_cmd=self.UserOut_ValSet49,
            get_cmd=self.Signals_ValGet24,
        )

        self.add_parameter(
            "Output50",
            set_cmd=self.UserOut_ValSet50,
            get_cmd=self.Signals_ValGet24,
        )
        self.add_parameter(
            "Input0",
            get_cmd=self.Signals_ValGet0,
        )


        self.add_parameter(
            "Input1",
            get_cmd=self.Signals_ValGet1,
        )

        self.add_parameter(
            "Input2",
            get_cmd=self.Signals_ValGet2,
        )

        self.add_parameter(
            "Input3",
            get_cmd=self.Signals_ValGet3,
        )

        self.add_parameter(
            "Input4",
            get_cmd=self.Signals_ValGet4,
        )

        self.add_parameter(
            "Input5",
            get_cmd=self.Signals_ValGet5,
        )

        self.add_parameter(
            "Input6",
            get_cmd=self.Signals_ValGet6,
        )
        self.add_parameter(
            "Input7",
            get_cmd=self.Signals_ValGet7,
        )

        self.add_parameter(
            "Input8",
            get_cmd=self.Signals_ValGet8,
        )

        self.add_parameter(
            "Input9",
            get_cmd=self.Signals_ValGet9,
        )

        self.add_parameter(
            "Input10",
            get_cmd=self.Signals_ValGet10,
        )

        self.add_parameter(
            "Input11",
            get_cmd=self.Signals_ValGet11,
        )

        self.add_parameter(
            "Input12",
            get_cmd=self.Signals_ValGet12,
        )

        self.add_parameter(
            "Input13",
            get_cmd=self.Signals_ValGet13,
        )

        self.add_parameter(
            "Input14",
            get_cmd=self.Signals_ValGet14,
        )

        self.add_parameter(
            "Input15",
            get_cmd=self.Signals_ValGet15,
        )

        self.add_parameter(
            "Input16",
            get_cmd=self.Signals_ValGet16,
        )

        self.add_parameter(
            "Input17",
            get_cmd=self.Signals_ValGet17,
        )

        self.add_parameter(
            "Input18",
            get_cmd=self.Signals_ValGet18,
        )

        self.add_parameter(
            "Input19",
            get_cmd=self.Signals_ValGet19,
        )

        self.add_parameter(
            "Input20",
            get_cmd=self.Signals_ValGet20,
        )

        self.add_parameter(
            "Input21",
            get_cmd=self.Signals_ValGet21,
        )

        self.add_parameter(
            "Input22",
            get_cmd=self.Signals_ValGet22,
        )

        self.add_parameter(
            "Input23",
            get_cmd=self.Signals_ValGet23,
        )




    def get_idn(self) -> dict[str, Optional[str]]:
        vendor = 'Ithaco (DL Instruments)'
        model = '1211'
        serial = None
        firmware = None
        return {'vendor': vendor, 'model': model,
                'serial': serial, 'firmware': firmware}

    # def DisplayInfo(self, displayInfo: int):
    #    self.n.displayInfo(displayInfo)
    def Signals_ValGet0(self):
        return (self.n.Signals_ValGet(0, 1)[2])[0]

    def Signals_ValGet1(self):
        return (self.n.Signals_ValGet(1, 1)[2])[0]

    def Signals_ValGet2(self):
        return (self.n.Signals_ValGet(2, 1)[2])[0]

    def Signals_ValGet3(self):
        return (self.n.Signals_ValGet(3, 1)[2])[0]

    def Signals_ValGet4(self):
        return (self.n.Signals_ValGet(4, 1)[2])[0]

    def Signals_ValGet5(self):
        return (self.n.Signals_ValGet(5, 1)[2])[0]

    def Signals_ValGet6(self):
        return (self.n.Signals_ValGet(6, 1)[2])[0]

    def Signals_ValGet7(self):
        return (self.n.Signals_ValGet(7, 1)[2])[0]

    def Signals_ValGet8(self):
        return (self.n.Signals_ValGet(8, 1)[2])[0]

    def Signals_ValGet9(self):
        return (self.n.Signals_ValGet(9, 1)[2])[0]

    def Signals_ValGet10(self):
        return (self.n.Signals_ValGet(10, 1)[2])[0]

    def Signals_ValGet11(self):
        return (self.n.Signals_ValGet(11, 1)[2])[0]

    def Signals_ValGet12(self):
        return (self.n.Signals_ValGet(12, 1)[2])[0]

    def Signals_ValGet13(self):
        return (self.n.Signals_ValGet(13, 1)[2])[0]

    def Signals_ValGet14(self):
        return (self.n.Signals_ValGet(14, 1)[2])[0]

    def Signals_ValGet15(self):
        return (self.n.Signals_ValGet(15, 1)[2])[0]

    def Signals_ValGet16(self):
        return (self.n.Signals_ValGet(16, 1)[2])[0]

    def Signals_ValGet17(self):
        return (self.n.Signals_ValGet(17, 1)[2])[0]

    def Signals_ValGet18(self):
        return (self.n.Signals_ValGet(18, 1)[2])[0]

    def Signals_ValGet19(self):
        return (self.n.Signals_ValGet(19, 1)[2])[0]

    def Signals_ValGet20(self):
        return (self.n.Signals_ValGet(20, 1)[2])[0]

    def Signals_ValGet21(self):
        return (self.n.Signals_ValGet(21, 1)[2])[0]

    def Signals_ValGet22(self):
        return (self.n.Signals_ValGet(22, 1)[2])[0]

    def Signals_ValGet23(self):
        return (self.n.Signals_ValGet(23, 1)[2])[0]

    def Signals_ValGet24(self):
        return (self.n.Signals_ValGet(24, 1)[2])[0]

    def Signals_ValGet25(self):
        return (self.n.Signals_ValGet(25, 1)[2])[0]

    def Signals_ValGet26(self):
        return (self.n.Signals_ValGet(26, 1)[2])[0]

    def Signals_ValGet27(self):
        return (self.n.Signals_ValGet(27, 1)[2])[0]

    def Signals_ValGet28(self):
        return (self.n.Signals_ValGet(28, 1)[2])[0]

    def Signals_ValGet29(self):
        return (self.n.Signals_ValGet(29, 1)[2])[0]

    def Signals_ValGet30(self):
        return (self.n.Signals_ValGet(30, 1)[2])[0]

    def Signals_ValGet31(self):
        return (self.n.Signals_ValGet(31, 1)[2])[0]

    def Signals_ValGet32(self):
        return (self.n.Signals_ValGet(32, 1)[2])[0]

    def Signals_ValGet33(self):
        return (self.n.Signals_ValGet(33, 1)[2])[0]

    def Signals_ValGet34(self):
        return (self.n.Signals_ValGet(34, 1)[2])[0]

    def Signals_ValGet35(self):
        return (self.n.Signals_ValGet(35, 1)[2])[0]

    def Signals_ValGet36(self):
        return (self.n.Signals_ValGet(36, 1)[2])[0]

    def Signals_ValGet37(self):
        return (self.n.Signals_ValGet(37, 1)[2])[0]

    def Signals_ValGet38(self):
        return (self.n.Signals_ValGet(38, 1)[2])[0]

    def Signals_ValGet39(self):
        return (self.n.Signals_ValGet(39, 1)[2])[0]

    def Signals_ValGet40(self):
        return (self.n.Signals_ValGet(40, 1)[2])[0]

    def Signals_ValGet41(self):
        return (self.n.Signals_ValGet(41, 1)[2])[0]

    def Signals_ValGet42(self):
        return (self.n.Signals_ValGet(42, 1)[2])[0]

    def Signals_ValGet43(self):
        return (self.n.Signals_ValGet(43, 1)[2])[0]

    def Signals_ValGet44(self):
        return (self.n.Signals_ValGet(44, 1)[2])[0]

    def Signals_ValGet45(self):
        return (self.n.Signals_ValGet(45, 1)[2])[0]

    def Signals_ValGet46(self):
        return (self.n.Signals_ValGet(46, 1)[2])[0]

    def Signals_ValGet47(self):
        return (self.n.Signals_ValGet(47, 1)[2])[0]

    def Signals_ValGet48(self):
        return (self.n.Signals_ValGet(48, 1)[2])[0]

    def Signals_ValGet49(self):
        return (self.n.Signals_ValGet(49, 1)[2])[0]

    def Signals_ValGet50(self):
        return (self.n.Signals_ValGet(50, 1)[2])[0]

    def Signals_ValGet51(self):
        return (self.n.Signals_ValGet(51, 1)[2])[0]

    def Signals_ValGet52(self):
        return (self.n.Signals_ValGet(52, 1)[2])[0]

    def Signals_ValGet53(self):
        return (self.n.Signals_ValGet(53, 1)[2])[0]

    def Signals_ValGet54(self):
        return (self.n.Signals_ValGet(54, 1)[2])[0]

    def Signals_ValGet55(self):
        return (self.n.Signals_ValGet(55, 1)[2])[0]

    def Signals_ValGet56(self):
        return (self.n.Signals_ValGet(56, 1)[2])[0]

    def Signals_ValGet57(self):
        return (self.n.Signals_ValGet(57, 1)[2])[0]

    def Signals_ValGet58(self):
        return (self.n.Signals_ValGet(58, 1)[2])[0]

    def Signals_ValGet59(self):
        return (self.n.Signals_ValGet(59, 1)[2])[0]

    def Signals_ValGet60(self):
        return (self.n.Signals_ValGet(60, 1)[2])[0]

    def Signals_ValGet61(self):
        return (self.n.Signals_ValGet(61, 1)[2])[0]

    def Signals_ValGet62(self):
        return (self.n.Signals_ValGet(62, 1)[2])[0]

    def Signals_ValGet63(self):
        return (self.n.Signals_ValGet(63, 1)[2])[0]

    def Signals_ValGet64(self):
        return (self.n.Signals_ValGet(64, 1)[2])[0]

    def Signals_ValGet65(self):
        return (self.n.Signals_ValGet(65, 1)[2])[0]

    def Signals_ValGet66(self):
        return (self.n.Signals_ValGet(66, 1)[2])[0]

    def Signals_ValGet67(self):
        return (self.n.Signals_ValGet(67, 1)[2])[0]

    def Signals_ValGet68(self):
        return (self.n.Signals_ValGet(68, 1)[2])[0]

    def Signals_ValGet69(self):
        return (self.n.Signals_ValGet(69, 1)[2])[0]

    def Signals_ValGet70(self):
        return (self.n.Signals_ValGet(70, 1)[2])[0]

    def Signals_ValGet71(self):
        return (self.n.Signals_ValGet(71, 1)[2])[0]

    def Signals_ValGet72(self):
        return (self.n.Signals_ValGet(72, 1)[2])[0]

    def Signals_ValGet73(self):
        return (self.n.Signals_ValGet(73, 1)[2])[0]

    def Signals_ValGet84(self):
        return (self.n.Signals_ValGet(84, 1)[2])[0]

    def Signals_ValGet85(self):
        return (self.n.Signals_ValGet(85, 1)[2])[0]

    def Signals_ValGet86(self):
        return (self.n.Signals_ValGet(86, 1)[2])[0]

    def Signals_ValGet87(self):
        return (self.n.Signals_ValGet(87, 1)[2])[0]

    def Signals_ValGet88(self):
        return (self.n.Signals_ValGet(88, 1)[2])[0]

    def Signals_ValGet89(self):
        return (self.n.Signals_ValGet(89, 1)[2])[0]

    def Signals_ValGet90(self):
        return (self.n.Signals_ValGet(90, 1)[2])[0]

    def Signals_ValGet91(self):
        return (self.n.Signals_ValGet(91, 1)[2])[0]

    def Signals_ValGet92(self):
        return (self.n.Signals_ValGet(92, 1)[2])[0]

    def Signals_ValGet93(self):
        return (self.n.Signals_ValGet(93, 1)[2])[0]

    def Signals_ValGet94(self):
        return (self.n.Signals_ValGet(94, 1)[2])[0]

    def Signals_ValGet95(self):
        return (self.n.Signals_ValGet(95, 1)[2])[0]

    def Signals_ValGet103(self):
        return (self.n.Signals_ValGet(103, 1)[2])[0]

    def Signals_ValGet104(self):
        return (self.n.Signals_ValGet(104, 1)[2])[0]

    def Signals_ValGet105(self):
        return (self.n.Signals_ValGet(105, 1)[2])[0]

    def Signals_ValGet106(self):
        return (self.n.Signals_ValGet(106, 1)[2])[0]

    def Signals_ValGet107(self):
        return (self.n.Signals_ValGet(107, 1)[2])[0]

    def Signals_ValGet108(self):
        return (self.n.Signals_ValGet(108, 1)[2])[0]

    def Signals_ValGet109(self):
        return (self.n.Signals_ValGet(109, 1)[2])[0]

    def Signals_ValGet110(self):
        return (self.n.Signals_ValGet(110, 1)[2])[0]

    def Signals_ValGet111(self):
        return (self.n.Signals_ValGet(111, 1)[2])[0]

    def Signals_ValGet112(self):
        return (self.n.Signals_ValGet(112, 1)[2])[0]

    def Signals_ValGet113(self):
        return (self.n.Signals_ValGet(113, 1)[2])[0]

    ###############################################################################
    ###############################################################################
    ###############################################################################

    def UserOut_ValSet1(self, Output_value:np.float32):
        self.n.UserOut_ValSet(1, Output_value)

    def UserOut_ValSet2(self, Output_value:np.float32):
        self.n.UserOut_ValSet(2, Output_value)

    def UserOut_ValSet3(self, Output_value:np.float32):
        self.n.UserOut_ValSet(3, Output_value)

    def UserOut_ValSet4(self, Output_value:np.float32):
        self.n.UserOut_ValSet(4, Output_value)

    def UserOut_ValSet5(self, Output_value:np.float32):
        self.n.UserOut_ValSet(5, Output_value)

    def UserOut_ValSet6(self, Output_value: np.float32):
        self.n.UserOut_ValSet(6, Output_value)

    def UserOut_ValSet7(self, Output_value: np.float32):
        self.n.UserOut_ValSet(7, Output_value)

    def UserOut_ValSet8(self, Output_value: np.float32):
        self.n.UserOut_ValSet(8, Output_value)

    def UserOut_ValSet9(self, Output_value: np.float32):
        self.n.UserOut_ValSet(9, Output_value)

    def UserOut_ValSet10(self, Output_value: np.float32):
        self.n.UserOut_ValSet(10, Output_value)

    def UserOut_ValSet11(self, Output_value: np.float32):
        self.n.UserOut_ValSet(11, Output_value)

    def UserOut_ValSet12(self, Output_value: np.float32):
        self.n.UserOut_ValSet(12, Output_value)

    def UserOut_ValSet13(self, Output_value: np.float32):
        self.n.UserOut_ValSet(13, Output_value)

    def UserOut_ValSet14(self, Output_value: np.float32):
        self.n.UserOut_ValSet(14, Output_value)

    def UserOut_ValSet15(self, Output_value: np.float32):
        self.n.UserOut_ValSet(15, Output_value)

    def UserOut_ValSet16(self, Output_value: np.float32):
        self.n.UserOut_ValSet(16, Output_value)

    def UserOut_ValSet17(self, Output_value: np.float32):
        self.n.UserOut_ValSet(17, Output_value)

    def UserOut_ValSet18(self, Output_value: np.float32):
        self.n.UserOut_ValSet(18, Output_value)

    def UserOut_ValSet19(self, Output_value: np.float32):
        self.n.UserOut_ValSet(19, Output_value)

    def UserOut_ValSet20(self, Output_value: np.float32):
        self.n.UserOut_ValSet(20, Output_value)

    def UserOut_ValSet21(self, Output_value: np.float32):
        self.n.UserOut_ValSet(21, Output_value)

    def UserOut_ValSet22(self, Output_value: np.float32):
        self.n.UserOut_ValSet(22, Output_value)

    def UserOut_ValSet23(self, Output_value: np.float32):
        self.n.UserOut_ValSet(23, Output_value)

    def UserOut_ValSet24(self, Output_value: np.float32):
        self.n.UserOut_ValSet(24, Output_value)

    def UserOut_ValSet25(self, Output_value: np.float32):
        self.n.UserOut_ValSet(25, Output_value)

    def UserOut_ValSet26(self, Output_value: np.float32):
        self.n.UserOut_ValSet(26, Output_value)

    def UserOut_ValSet27(self, Output_value: np.float32):
        self.n.UserOut_ValSet(27, Output_value)

    def UserOut_ValSet28(self, Output_value: np.float32):
        self.n.UserOut_ValSet(28, Output_value)

    def UserOut_ValSet29(self, Output_value: np.float32):
        self.n.UserOut_ValSet(29, Output_value)

    def UserOut_ValSet30(self, Output_value: np.float32):
        self.n.UserOut_ValSet(30, Output_value)

    def UserOut_ValSet31(self, Output_value: np.float32):
        self.n.UserOut_ValSet(31, Output_value)

    def UserOut_ValSet32(self, Output_value: np.float32):
        self.n.UserOut_ValSet(32, Output_value)

    def UserOut_ValSet33(self, Output_value: np.float32):
        self.n.UserOut_ValSet(33, Output_value)

    def UserOut_ValSet34(self, Output_value: np.float32):
        self.n.UserOut_ValSet(34, Output_value)

    def UserOut_ValSet35(self, Output_value: np.float32):
        self.n.UserOut_ValSet(35, Output_value)

    def UserOut_ValSet36(self, Output_value: np.float32):
        self.n.UserOut_ValSet(36, Output_value)

    def UserOut_ValSet37(self, Output_value: np.float32):
        self.n.UserOut_ValSet(37, Output_value)

    def UserOut_ValSet38(self, Output_value: np.float32):
        self.n.UserOut_ValSet(38, Output_value)

    def UserOut_ValSet39(self, Output_value: np.float32):
        self.n.UserOut_ValSet(39, Output_value)

    def UserOut_ValSet40(self, Output_value: np.float32):
        self.n.UserOut_ValSet(40, Output_value)

    def UserOut_ValSet41(self, Output_value: np.float32):
        self.n.UserOut_ValSet(41, Output_value)

    def UserOut_ValSet42(self, Output_value: np.float32):
        self.n.UserOut_ValSet(42, Output_value)

    def UserOut_ValSet43(self, Output_value: np.float32):
        self.n.UserOut_ValSet(43, Output_value)

    def UserOut_ValSet44(self, Output_value: np.float32):
        self.n.UserOut_ValSet(44, Output_value)

    def UserOut_ValSet45(self, Output_value: np.float32):
        self.n.UserOut_ValSet(45, Output_value)

    def UserOut_ValSet46(self, Output_value: np.float32):
        self.n.UserOut_ValSet(46, Output_value)

    def UserOut_ValSet47(self, Output_value: np.float32):
        self.n.UserOut_ValSet(47, Output_value)

    def UserOut_ValSet48(self, Output_value: np.float32):
        self.n.UserOut_ValSet(48, Output_value)

    def UserOut_ValSet49(self, Output_value: np.float32):
        self.n.UserOut_ValSet(49, Output_value)

    def UserOut_ValSet50(self, Output_value: np.float32):
        self.n.UserOut_ValSet(50, Output_value)


    ###############################################################################
    ###############################################################################
    ###############################################################################



    def ThreeDSwp_SwpAcqChsSet(self, channelIndexes: np.array(int)):
        return self.n.ThreeDSwp_AcqChsSet(channelIndexes)[2]

    def ThreeDSwp_SwpAcqChsGet(self):
        return self.n.ThreeDSwp_AcqChsGet()[2]

    def ThreeDSwp_SwpSaveOptionsGet(self):
        return self.n.ThreeDSwp_SaveOptionsGet()[2]

    def ThreeDSwp_SwpSaveOptionsSet(self, seriesName: str, createDateandTimeFolder: np.int32, comment: str,
                                    moduleNamesSize: np.int32, moduleNames: np.array(str)):
        return self.n.ThreeDSwp_SaveOptionsSet(seriesName, createDateandTimeFolder, comment, moduleNamesSize, moduleNames)[2]

    def ThreeDSwpStart(self):
        return self.n.ThreeDSwp_Start()[2]

    def ThreeDSwpStop(self):
        return self.n.ThreeDSwp_Stop()[2]

    def ThreeDSwpOpen(self):
        return self.n.ThreeDSwp_Open()[2]

    def ThreeDSwp_SwpStatusGet(self):
        return self.n.ThreeDSwp_StatusGet()[2]

    def ThreeDSwp_SwpChSignalSet(self, sweepChannelIndex: np.int32):
        return self.n.ThreeDSwp_SwpChSignalSet(sweepChannelIndex)[2]

    def ThreeDSwp_SwpChSignalGet(self):
        return self.n.ThreeDSwp_SwpChSignalGet()[2]

    def ThreeDSwp_SwpChLimitsSet(self, start: np.float32, stop: np.float32):
        return self.n.ThreeDSwp_SwpChLimitsSet(start, stop)[2]

    def ThreeDSwp_SwpChLimitsGet(self):
        return self.n.ThreeDSwp_SwpChLimitsGet()[2]

    def ThreeDSwp_SwpChPropsSet(self, noOfPoints: np.int32, noOfSweeps: np.int32, backwardSweep: np.int32,
                                endOfSweepAction: np.int32, endOfSweepArbitraryValue: np.float32, saveAll: np.int32):
        return self.n.ThreeDSwp_SwpChPropsSet(noOfPoints, noOfSweeps, backwardSweep, endOfSweepAction,
                                       endOfSweepArbitraryValue, saveAll)[2]

    def ThreeDSwp_SwpChPropsGet(self):
        return self.n.ThreeDSwp_SwpChPropsGet()[2]

    def ThreeDSwp_SwpChTimingSet(self, InitSettlingTime, SettlingTime, IntegrationTime, EndSettlingTime, MaxSlewRate):
        return self.n.ThreeDSwp_SwpChTimingSet(InitSettlingTime, SettlingTime, IntegrationTime, EndSettlingTime, MaxSlewRate)[2]

    def ThreeDSwp_SwpChTimingGet(self):
        return self.n.ThreeDSwp_SwpChTimingGet()[2]

    def ThreeDSwp_SwpChModeSet(self, Segments_Mode):
        return self.n.ThreeDSwp_SwpChModeSet(Segments_Mode)[2]

    def ThreeDSwp_SwpChModeGet(self):
        return self.n.ThreeDSwp_SwpChModeGet()[2]

    def ThreeDSwp_SwpChMLSSet(self, NumOfSegments, StartVals, StopVals, SettlingTimes, IntegrationTimes, NoOfSteps,
                              LastSegmentArray):
        return self.n.ThreeDSwp_SwpChMLSSet(NumOfSegments, StartVals, StopVals, SettlingTimes, IntegrationTimes, NoOfSteps,
                                     LastSegmentArray)[2]

    def ThreeDSwp_SwpChMLSGet(self):
        return self.n.ThreeDSwp_SwpChMLSGet()[2]

    def ThreeDSwp_StpCh1SignalSet(self, StepChannelOneIndex):
        return self.n.ThreeDSwp_StpCh1SignalSet(StepChannelOneIndex)[2]

    def ThreeDSwp_StpCh1SignalGet(self):
        return self.n.ThreeDSwp_StpCh1SignalGet()[2]

    def ThreeDSwp_StpCh1LimitsSet(self, Start, Stop):
        return self.n.ThreeDSwp_StpCh1LimitsSet(Start, Stop)[2]

    def ThreeDSwp_StpCh1LimitsGet(self):
        return self.n.ThreeDSwp_StpCh1LimitsGet()[2]

    def ThreeDSwp_StpCh1PropsSet(self, NoOfPoints, BwdSweep, EndOfSweep, EndOfSweepVal):
        return self.n.ThreeDSwp_StpCh1PropsSet(NoOfPoints, BwdSweep, EndOfSweep, EndOfSweepVal)[2]

    def ThreeDSwp_StpCh1PropsGet(self):
        return self.n.ThreeDSwp_StpCh1PropsGet()[2]

    def ThreeDSwp_StpCh1TimingSet(self, InitSettlingTime, EndSettlingTime, MaxSlewRate):
        return self.n.ThreeDSwp_StpCh1TimingSet(InitSettlingTime, EndSettlingTime, MaxSlewRate)[2]

    def ThreeDSwp_StpCh1TimingGet(self):
        return self.n.ThreeDSwp_StpCh1TimingGet()[2]

    def ThreeDSwp_StpCh2SignalSet(self, StepChannel2Name):
        return self.n.ThreeDSwp_StpCh2SignalSet(StepChannel2Name)[2]

    def ThreeDSwp_StpCh2SignalGet(self):
        return self.n.ThreeDSwp_StpCh2SignalGet()[2]

    def ThreeDSwp_StpCh2LimitsSet(self, Start, Stop):
        return self.n.ThreeDSwp_StpCh2LimitsSet(Start, Stop)[2]

    def ThreeDSwp_StpCh2LimitsGet(self):
        return self.n.ThreeDSwp_StpCh2LimitsGet()[2]

    def ThreeDSwp_StpCh2PropsSet(self, NumOfPoints, BwdSweep, EndOfSweep, EndOfSweepVal):
        return self.n.ThreeDSwp_StpCh2PropsSet(NumOfPoints, BwdSweep, EndOfSweep, EndOfSweepVal)[2]

    def ThreeDSwp_StpCh2PropsGet(self):
        return self.n.ThreeDSwp_StpCh2PropsGet()[2]

    def ThreeDSwp_StpCh2TimingSet(self, InitSettlingTime, EndSettlingTime, MaxSlewRate):
        return self.n.ThreeDSwp_StpCh2TimingSet(InitSettlingTime, EndSettlingTime, MaxSlewRate)[2]

    def ThreeDSwp_StpCh2TimingGet(self):
        return self.n.ThreeDSwp_StpCh2TimingGet()[2]

    def ThreeDSwp_TimingRowLimitSet(self, RowIndex, MaxTime, ChannelIndex):
        return self.n.ThreeDSwp_TimingRowLimitSet(RowIndex, MaxTime, ChannelIndex)[2]

    def ThreeDSwp_TimingRowLimitGet(self, RowIndex):
        return self.n.ThreeDSwp_TimingRowLimitGet(RowIndex)[2]

    def ThreeDSwp_TimingRowMethodsSet(self, RowIndex, MethodLower, MethodMiddle, MethodUpper, MethodAlt):
        return self.n.ThreeDSwp_TimingRowMethodsSet(RowIndex, MethodLower, MethodMiddle, MethodUpper, MethodAlt)[2]

    def ThreeDSwp_TimingRowMethodsGet(self, RowIndex):
        return self.n.ThreeDSwp_TimingRowMethodsGet(RowIndex)[2]

    def ThreeDSwp_TimingRowValsSet(self, RowIndex, MiddleRangeFrom, LowerRangeVal, MiddleRangeVal, MiddleRangeTo,
                                   UpperRangeVal, AltRangeVal):
        return self.n.ThreeDSwp_TimingRowValsSet(RowIndex, MiddleRangeFrom, LowerRangeVal, MiddleRangeVal, MiddleRangeTo,
                                          UpperRangeVal, AltRangeVal)[2]

    def ThreeDSwp_TimingRowValsGet(self, RowIndex):
        return self.n.ThreeDSwp_TimingRowValsGet(RowIndex)[2]

    def ThreeDSwp_TimingEnable(self, Enable):
        return self.n.ThreeDSwp_TimingEnable(Enable)[2]

    def ThreeDSwp_TimingSend(self):
        return self.n.ThreeDSwp_TimingSend()[2]

    def ThreeDSwp_FilePathsGet(self):
        return self.n.ThreeDSwp_FilePathsGet()[2]

    def OneDSwp_AcqChsSet(self, ChannelIndexes):
        return self.n.OneDSwp_AcqChsSet(ChannelIndexes)[2]

    def OneDSwp_AcqChsGet(self):
        return self.n.OneDSwp_AcqChsGet()[2]

    def OneDSwp_SwpSignalSet(self, SweepChannelName):
        return self.n.OneDSwp_SwpSignalSet(SweepChannelName)[2]

    def OneDSwp_SwpSignalGet(self):
        return self.n.OneDSwp_SwpSignalGet()[2]

    def OneDSwp_LimitsSet(self, LowerLimit, UpperLimit):
        return self.n.OneDSwp_LimitsSet(LowerLimit, UpperLimit)[2]

    def OneDSwp_LimitsGet(self):
        return self.n.OneDSwp_LimitsGet()[2]

    def OneDSwp_PropsSet(self, InitSettlingTime, MaxSlewRate, NoOfSteps, Period, Autosave, SaveDialogBox, SettlingTime):
        return self.n.OneDSwp_PropsSet(InitSettlingTime, MaxSlewRate, NoOfSteps, Period, Autosave, SaveDialogBox, SettlingTime)[2]

    def OneDSwp_PropsGet(self):
        return self.n.OneDSwp_PropsGet()[2]

    def OneDSwp_Start(self, GetData, SweepDirection, SaveBaseName, ResetSignal):
        return self.n.OneDSwp_Start(GetData, SweepDirection, SaveBaseName, ResetSignal)[2]

    def OneDSwp_Stop(self):
        return self.n.OneDSwp_Stop()[2]

    def OneDSwp_Open(self):
        return self.n.OneDSwp_Open()[2]

    def LockIn_ModOnOffSet(self, Modulator_number, Lock_In_OndivOff):
        return self.n.LockIn_ModOnOffSet(Modulator_number, Lock_In_OndivOff)[2]

    def LockIn_ModOnOffGet(self, Modulator_number):
        return self.n.LockIn_ModOnOffGet(Modulator_number)[2]

    def LockIn_ModSignalSet(self, Modulator_number, Modulator_Signal_Index):
        return self.n.LockIn_ModSignalSet(Modulator_number, Modulator_Signal_Index)[2]

    def LockIn_ModSignalGet(self, Modulator_number):
        return self.n.LockIn_ModSignalGet(Modulator_number)[2]

    def LockIn_ModPhasRegSet(self, Modulator_number, Phase_Register_Index):
        return self.n.LockIn_ModPhasRegSet(Modulator_number, Phase_Register_Index)[2]

    def LockIn_ModPhasRegGet(self, Modulator_number):
        return self.n.LockIn_ModPhasRegGet(Modulator_number)[2]

    def LockIn_ModHarmonicSet(self, Modulator_number, Harmonic_):
        return self.n.LockIn_ModHarmonicSet(Modulator_number, Harmonic_)[2]

    def LockIn_ModHarmonicGet(self, Modulator_number):
        return self.n.LockIn_ModHarmonicGet(Modulator_number)[2]

    def LockIn_ModPhasSet(self, Modulator_number, Phase_deg_):
        return self.n.LockIn_ModPhasSet(Modulator_number, Phase_deg_)[2]

    def LockIn_ModPhasGet(self, Modulator_number):
        return self.n.LockIn_ModPhasGet(Modulator_number)[2]

    def LockIn_ModAmpSet(self, Modulator_number, Amplitude_):
        return self.n.LockIn_ModAmpSet(Modulator_number, Amplitude_)[2]

    def LockIn_ModAmpGet(self, Modulator_number):
        return self.n.LockIn_ModAmpGet(Modulator_number)[2]

    def LockIn_ModPhasFreqSet(self, Modulator_number, Frequency_Hz_):
        return self.n.LockIn_ModPhasFreqSet(Modulator_number, Frequency_Hz_)[2]

    def LockIn_ModPhasFreqGet(self, Modulator_number):
        return self.n.LockIn_ModPhasFreqGet(Modulator_number)[2]

    def LockIn_DemodSignalSet(self, Demodulator_number, Demodulator_Signal_Index):
        return self.n.LockIn_DemodSignalSet(Demodulator_number, Demodulator_Signal_Index)[2]

    def LockIn_DemodSignalGet(self, Demodulator_number):
        return self.n.LockIn_DemodSignalGet(Demodulator_number)[2]

    def LockIn_DemodHarmonicSet(self, Demodulator_number, Harmonic_):
        return self.n.LockIn_DemodHarmonicSet(Demodulator_number, Harmonic_)[2]

    def LockIn_DemodHarmonicGet(self, Demodulator_number):
        return self.n.LockIn_DemodHarmonicGet(Demodulator_number)[2]

    def LockIn_DemodHPFilterSet(self, Demodulator_number, HP_Filter_Order, HP_Filter_Cutoff_Frequency_Hz):
        return self.n.LockIn_DemodHPFilterSet(Demodulator_number, HP_Filter_Order, HP_Filter_Cutoff_Frequency_Hz)[2]

    def LockIn_DemodHPFilterGet(self, Demodulator_number):
        return self.n.LockIn_DemodHPFilterGet(Demodulator_number)[2]

    def LockIn_DemodLPFilterSet(self, Demodulator_number, LP_Filter_Order, LP_Filter_Cutoff_Frequency_Hz):
        return self.n.LockIn_DemodLPFilterSet(Demodulator_number, LP_Filter_Order, LP_Filter_Cutoff_Frequency_Hz)[2]

    def LockIn_DemodLPFilterGet(self, Demodulator_number):
        return self.n.LockIn_DemodLPFilterGet(Demodulator_number)[2]

    def LockIn_DemodPhasRegSet(self, Demodulator_number, Phase_Register_Index):
        return self.n.LockIn_DemodPhasRegSet(Demodulator_number, Phase_Register_Index)[2]

    def LockIn_DemodPhasRegGet(self, Demodulator_number):
        return self.n.LockIn_DemodPhasRegGet(Demodulator_number)[2]

    def LockIn_DemodPhasSet(self, Demodulator_number, Phase_deg_):
        return self.n.LockIn_DemodPhasSet(Demodulator_number, Phase_deg_)[2]

    def LockIn_DemodPhasGet(self, Demodulator_number):
        return self.n.LockIn_DemodPhasGet(Demodulator_number)[2]

    def LockIn_DemodSyncFilterSet(self, Demodulator_number, Sync_Filter_):
        return self.n.LockIn_DemodSyncFilterSet(Demodulator_number, Sync_Filter_)[2]

    def LockIn_DemodSyncFilterGet(self, Demodulator_number):
        return self.n.LockIn_DemodSyncFilterGet(Demodulator_number)[2]

    def LockIn_DemodRTSignalsSet(self, Demodulator_number, RT_Signals_):
        return self.n.LockIn_DemodRTSignalsSet(Demodulator_number, RT_Signals_)[2]

    def LockIn_DemodRTSignalsGet(self, Demodulator_number):
        return self.n.LockIn_DemodRTSignalsGet(Demodulator_number)[2]

    def LockInFreqSwp_Open(self):
        return self.n.LockInFreqSwp_Open()[2]

    def LockInFreqSwp_Start(self, Get_Data, Direction):
        return self.n.LockInFreqSwp_Start(Get_Data, Direction)[2]

    def LockInFreqSwp_SignalSet(self, Sweep_signal_index):
        return self.n.LockInFreqSwp_SignalSet(Sweep_signal_index)[2]

    def LockInFreqSwp_SignalGet(self):
        return self.n.LockInFreqSwp_SignalGet()[2]

    def LockInFreqSwp_LimitsSet(self, Lower_limit_Hz, Upper_limit_Hz):
        return self.n.LockInFreqSwp_LimitsSet(Lower_limit_Hz, Upper_limit_Hz)[2]

    def LockInFreqSwp_LimitsGet(self):
        return self.n.LockInFreqSwp_LimitsGet()[2]

    def LockInFreqSwp_PropsSet(self, Number_of_steps, Integration_periods, Minimum_integration_time_s, Settling_periods,
                               Minimum_Settling_time_s, Autosave, Save_dialog, Basename):
        return self.n.LockInFreqSwp_PropsSet(Number_of_steps, Integration_periods, Minimum_integration_time_s,
                                      Settling_periods,
                                      Minimum_Settling_time_s, Autosave, Save_dialog, Basename)[2]

    def LockInFreqSwp_PropsGet(self):
        return self.n.LockInFreqSwp_PropsGet()[2]

    def Script_Load(self, Script_file_path, Load_session):
        return self.n.Script_Load(Script_file_path, Load_session)[2]

    def Script_Save(self, Script_file_path, Save_session):
        return self.n.Script_Save(Script_file_path, Save_session)[2]

    def Script_Deploy(self, Script_index):
        return self.n.Script_Deploy(Script_index)[2]

    def Script_Undeploy(self, Script_index):
        return self.n.Script_Undeploy(Script_index)[2]

    def Script_Run(self, Script_index, Wait_until_script_finishes):
        return self.n.Script_Run(Script_index, Wait_until_script_finishes)[2]

    def Script_Stop(self):
        return self.n.Script_Stop()[2]

    def Script_ChsGet(self, Acquire_buffer):
        return self.n.Script_ChsGet(Acquire_buffer)[2]

    def Script_ChsSet(self, Acquire_buffer, Number_of_channels, Channel_indexes):
        return self.n.Script_ChsSet(Acquire_buffer, Number_of_channels, Channel_indexes)[2]

    def Script_DataGet(self, Acquire_buffer, Sweep_number):
        return self.n.Script_DataGet(Acquire_buffer, Sweep_number)[2]

    def Script_Autosave(self, Acquire_buffer, Sweep_number, All_sweeps_to_same_file):
        return self.n.Script_Autosave(Acquire_buffer, Sweep_number, All_sweeps_to_same_file)[2]

    def Signals_NamesGet(self):
        return self.n.Signals_NamesGet()[2]

    def Signals_InSlotSet(self, Slot, RT_signal_index):
        return self.n.Signals_InSlotSet(Slot, RT_signal_index)[2]

    def Signals_InSlotsGet(self):
        return self.n.Signals_InSlotsGet()[2]

    def Signals_CalibrGet(self, Signal_index):
        return self.n.Signals_CalibrGet(Signal_index)[2]

    def Signals_RangeGet(self, Signal_index):
        return self.n.Signals_RangeGet(Signal_index)[2]



    def Signals_MeasNamesGet(self):
        return self.n.Signals_MeasNamesGet()[2]

    def Signals_AddRTGet(self):
        return self.n.Signals_AddRTGet()[2]

    def Signals_AddRTSet(self, Additional_RT_signal_1, Additional_RT_signal_2):
        return self.n.Signals_AddRTSet(Additional_RT_signal_1, Additional_RT_signal_2)[2]

    def UserIn_CalibrSet(self, Input_index, Calibration_per_volt, Offset_in_physical_units):
        return self.n.UserIn_CalibrSet(Input_index, Calibration_per_volt, Offset_in_physical_units)[2]

    def UserOut_ModeSet(self, Output_index, Output_mode):
        return self.n.UserOut_ModeSet(Output_index, Output_mode)[2]

    def UserOut_ModeGet(self, Output_index):
        return self.n.UserOut_ModeGet(Output_index)[2]

    def UserOut_MonitorChSet(self, Output_index, Monitor_channel_index):
        return self.n.UserOut_MonitorChSet(Output_index, Monitor_channel_index)[2]

    def UserOut_MonitorChGet(self, Output_index):
        return self.n.UserOut_MonitorChGet(Output_index)[2]

    def UserOut_CalibrSet(self, Output_index, Calibration_per_volt, Offset_in_physical_units):
        self.n.UserOut_CalibrSet(Output_index, Calibration_per_volt, Offset_in_physical_units)

    def UserOut_CalcSignalNameSet(self, Output_index, Calculated_signal_name):
        return self.n.UserOut_CalcSignalNameSet(Output_index, Calculated_signal_name)[2]

    def UserOut_CalcSignalNameGet(self, Output_index):
        return self.n.UserOut_CalcSignalNameGet(Output_index)[2]

    def UserOut_CalcSignalConfigSet(self, Output_index, Signal_1, Operation, Signal_2):
        return self.n.UserOut_CalcSignalConfigSet(Output_index, Signal_1, Operation, Signal_2)[2]

    def UserOut_CalcSignalConfigGet(self, Output_index):
        return self.n.UserOut_CalcSignalConfigGet(Output_index)[2]

    def UserOut_LimitsSet(self, Output_index, Upper_limit, Lower_limit):
        return self.n.UserOut_LimitsSet(Output_index, Upper_limit, Lower_limit)[2]

    def UserOut_LimitsGet(self, Output_index):
        return self.n.UserOut_LimitsGet(Output_index)[2]

    def UserOut_SlewRateSet(self, Output_Index, Slew_Rate):
        return self.n.UserOut_SlewRateSet(Output_Index, Slew_Rate)[2]

    def UserOut_SlewRateGet(self):
        return self.n.UserOut_SlewRateGet()[2]

    def DigLines_PropsSet(self, Digital_line, Port, Direction, Polarity):
        return self.n.DigLines_PropsSet(Digital_line, Port, Direction, Polarity)[2]

    def DigLines_OutStatusSet(self, Port, Digital_line, Status):
        return self.n.DigLines_OutStatusSet(Port, Digital_line, Status)[2]

    def DigLines_TTLValGet(self, Port):
        return self.n.DigLines_TTLValGet(Port)[2]

    def DigLines_Pulse(self, Port, Digital_lines, Pulse_width_s, Pulse_pause_s, Number_of_pulses,
                       Wait_until_finished):
        return self.n.DigLines_Pulse(Port, Digital_lines, Pulse_width_s, Pulse_pause_s, Number_of_pulses,
                              Wait_until_finished)[2]

    def DataLog_Open(self):
        return self.n.DataLog_Open()[2]

    def DataLog_Start(self):
        return self.n.DataLog_Start()[2]

    def DataLog_Stop(self):
        return self.n.DataLog_Stop()[2]

    def DataLog_StatusGet(self):
        return self.n.DataLog_StatusGet()[2]

    def DataLog_ChsSet(self, Channel_indexes):
        return self.n.DataLog_ChsSet(Channel_indexes)[2]

    def DataLog_ChsGet(self):
        return self.n.DataLog_ChsGet()[2]

    def DataLog_PropsSet(self, Acquisition_mode, Acquisition_duration_hours, Acquisition_duration_minutes,
                         Acquisition_duration_seconds, Averaging, Basename, Comment, List_of_modules):
        return self.n.DataLog_PropsSet(Acquisition_mode, Acquisition_duration_hours, Acquisition_duration_minutes,
                                Acquisition_duration_seconds, Averaging, Basename, Comment, List_of_modules)[2]

    def DataLog_PropsGet(self):
        return self.n.DataLog_PropsGet()[2]

    def TCPLog_Start(self):
        return self.n.TCPLog_Start()[2]

    def TCPLog_Stop(self):
        return self.n.TCPLog_Stop()[2]

    def TCPLog_ChsSet(self, Channel_indexes):
        return self.n.TCPLog_ChsSet(Channel_indexes)[2]

    def TCPLog_OversamplSet(self, Oversampling_value):
        return self.n.TCPLog_OversamplSet(Oversampling_value)[2]

    def TCPLog_StatusGet(self):
        return self.n.TCPLog_StatusGet()[2]

    def OsciHR_ChSet(self, Channel_index):
        return self.n.OsciHR_ChSet(Channel_index)[2]

    def OsciHR_ChGet(self):
        return self.n.OsciHR_ChGet()[2]

    def OsciHR_OversamplSet(self, Oversampling_index):
        return self.n.OsciHR_OversamplSet(Oversampling_index)[2]

    def OsciHR_OversamplGet(self):
        return self.n.OsciHR_OversamplGet()[2]

    def OsciHR_CalibrModeSet(self, Calibration_mode):
        return self.n.OsciHR_CalibrModeSet(Calibration_mode)[2]

    def OsciHR_CalibrModeGet(self):
        return self.n.OsciHR_CalibrModeGet()[2]

    def OsciHR_SamplesSet(self, Number_of_samples):
        return self.n.OsciHR_SamplesSet(Number_of_samples)[2]

    def OsciHR_SamplesGet(self):
        return self.n.OsciHR_SamplesGet()[2]

    def OsciHR_PreTrigSet(self, Pre_Trigger_samples, Pre_Trigger_s):
        return self.n.OsciHR_PreTrigSet(Pre_Trigger_samples, Pre_Trigger_s)[2]

    def OsciHR_PreTrigGet(self):
        return self.n.OsciHR_PreTrigGet()[2]

    def OsciHR_Run(self):
        return self.n.OsciHR_Run()[2]

    def OsciHR_OsciDataGet(self, Data_to_get, Timeout_s):
        return self.n.OsciHR_OsciDataGet(Data_to_get, Timeout_s)[2]

    def OsciHR_TrigModeSet(self, Trigger_mode):
        return self.n.OsciHR_TrigModeSet(Trigger_mode)[2]

    def OsciHR_TrigModeGet(self):
        return self.n.OsciHR_TrigModeGet()[2]

    def OsciHR_TrigLevChSet(self, Level_trigger_channel_index):
        return self.n.OsciHR_TrigLevChSet(Level_trigger_channel_index)[2]

    def OsciHR_TrigLevChGet(self):
        return self.n.OsciHR_TrigLevChGet()[2]

    def OsciHR_TrigLevValSet(self, Level_trigger_value):
        return self.n.OsciHR_TrigLevValSet(Level_trigger_value)[2]

    def OsciHR_TrigLevValGet(self):
        return self.n.OsciHR_TrigLevValGet()[2]

    def OsciHR_TrigLevHystSet(self, Level_trigger_Hysteresis):
        return self.n.OsciHR_TrigLevHystSet(Level_trigger_Hysteresis)[2]

    def OsciHR_TrigLevHystGet(self):
        return self.n.OsciHR_TrigLevHystGet()[2]

    def OsciHR_TrigLevSlopeSet(self, Level_trigger_slope):
        return self.n.OsciHR_TrigLevSlopeSet(Level_trigger_slope)[2]

    def OsciHR_TrigLevSlopeGet(self):
        return self.n.OsciHR_TrigLevSlopeGet()[2]

    def OsciHR_TrigDigChSet(self, Digital_trigger_channel_index):
        return self.n.OsciHR_TrigDigChSet(Digital_trigger_channel_index)[2]

    def OsciHR_TrigDigChGet(self):
        return self.n.OsciHR_TrigDigChGet()[2]

    def OsciHR_TrigArmModeSet(self, Trigger_arming_mode):
        return self.n.OsciHR_TrigArmModeSet(Trigger_arming_mode)[2]

    def OsciHR_TrigArmModeGet(self):
        return self.n.OsciHR_TrigArmModeGet()[2]

    def OsciHR_TrigDigSlopeSet(self, Digital_trigger_slope):
        return self.n.OsciHR_TrigDigSlopeSet(Digital_trigger_slope)[2]

    def OsciHR_TrigDigSlopeGet(self):
        return self.n.OsciHR_TrigDigSlopeGet()[2]

    def OsciHR_TrigRearm(self):
        return self.n.OsciHR_TrigRearm()[2]

    def OsciHR_PSDShow(self, Show_PSD_section):
        return self.n.OsciHR_PSDShow(Show_PSD_section)[2]

    def OsciHR_PSDWeightSet(self, PSD_Weighting):
        return self.n.OsciHR_PSDWeightSet(PSD_Weighting)[2]

    def OsciHR_PSDWeightGet(self):
        return self.n.OsciHR_PSDWeightGet()[2]

    def OsciHR_PSDWindowSet(self, PSD_window_type):
        return self.n.OsciHR_PSDWindowSet(PSD_window_type)[2]

    def OsciHR_PSDWindowGet(self):
        return self.n.OsciHR_PSDWindowGet()[2]

    def OsciHR_PSDAvrgTypeSet(self, PSD_averaging_type):
        return self.n.OsciHR_PSDAvrgTypeSet(PSD_averaging_type)[2]

    def OsciHR_PSDAvrgTypeGet(self):
        return self.n.OsciHR_PSDAvrgTypeGet()[2]

    def OsciHR_PSDAvrgCountSet(self, PSD_averaging_count):
        return self.n.OsciHR_PSDAvrgCountSet(PSD_averaging_count)[2]

    def OsciHR_PSDAvrgCountGet(self):
        return self.n.OsciHR_PSDAvrgCountGet()[2]

    def OsciHR_PSDAvrgRestart(self):
        return self.n.OsciHR_PSDAvrgRestart()[2]

    def OsciHR_PSDDataGet(self, Data_to_get, Timeout_s):
        return self.n.OsciHR_PSDDataGet(Data_to_get, Timeout_s)[2]

    def Util_SessionPathGet(self):
        return self.n.Util_SessionPathGet()[2]

    def Util_SettingsLoad(self, Settings_file_path, Load_session_settings):
        return self.n.Util_SettingsLoad(Settings_file_path, Load_session_settings)[2]

    def Util_SettingsSave(self, Settings_file_path, Save_session_settings):
        return self.n.Util_SettingsSave(Settings_file_path, Save_session_settings)[2]

    def Util_LayoutLoad(self, Layout_file_path, Load_session_layout):
        return self.n.Util_LayoutLoad(Layout_file_path, Load_session_layout)[2]

    def Util_LayoutSave(self, Layout_file_path, Save_session_layout):
        return self.n.Util_LayoutSave(Layout_file_path, Save_session_layout)[2]

    def Util_Lock(self):
        return self.n.Util_Lock()[2]

    def Util_UnLock(self):
        return self.n.Util_UnLock()[2]

    def Util_RTFreqSet(self, RT_frequency):
        return self.n.Util_RTFreqSet(RT_frequency)[2]

    def Util_RTFreqGet(self):
        return self.n.Util_RTFreqGet()[2]

    def Util_AcqPeriodSet(self, Acquisition_Period_s):
        return self.n.Util_AcqPeriodSet(Acquisition_Period_s)[2]

    def Util_AcqPeriodGet(self):
        return self.n.Util_AcqPeriodGet()[2]

    def Util_RTOversamplSet(self, RT_oversampling):
        return self.n.Util_RTOversamplSet(RT_oversampling)[2]

    def Util_RTOversamplGet(self):
        return self.n.Util_RTOversamplGet()[2]

    def Util_Quit(self, Use_Stored_Values, Settings_Name, Layout_Name, Save_Signals):
        return self.n.Util_Quit(Use_Stored_Values, Settings_Name, Layout_Name, Save_Signals)[2]

    def ReturnDebugInfo(self, returnInfo):
        self.n.returnDebugInfo(returnInfo)

    def OneDSwpOpen(self):
        return self.n.OneDSwp_Open()[2]

    def OneDSwpStart(self, GetData: np.uint32, SweepDirection: np.uint32, SaveBaseName: str, ResetSignal: np.uint32):
        return self.n.OneDSwp_Start(GetData, SweepDirection, SaveBaseName, ResetSignal)[2]
