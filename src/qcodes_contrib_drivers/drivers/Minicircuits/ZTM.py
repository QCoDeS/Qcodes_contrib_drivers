import math
from typing import Optional

from qcodes import validators as vals
from qcodes.instrument import ChannelList, InstrumentChannel, IPInstrument

class MiniCircuitsModule(InstrumentChannel):
    """
    Placeholder for individual module class.
    """
    def __init__(self, parent: IPInstrument, name: str, module_address: int):
        super().__init__(parent, name)
        self.module_address = module_address
        # Additional initialization code and parameters for individual modules go here

    @staticmethod
    def _parse_response(response: str) -> int:
        """
        Parse the response string from the instrument to an integer.

        Args:
            response: response string from the instrument

        Returns:
            Parsed integer value
        """
        return int(response.strip())


class SPDTModule(MiniCircuitsModule):
    """
    SPDT switch module class.
    """
    def __init__(self, parent: IPInstrument, name: str, module_address: int):
        super().__init__(parent, name, module_address)

        self.add_parameter(
            "state",
            get_cmd=":SPDT:{}:STATE?".format(self.module_address),
            set_cmd=":SPDT:{}:STATE:{}".format(self.module_address, "{}"),
            get_parser=self._parse_response,
            vals=vals.Ints(1, 2),
            docstring="State of the SPDT switch",
        )

class SP4TModule(MiniCircuitsModule):
    """
    SP4T switch module class.
    """
    def __init__(self, parent: IPInstrument, name: str, module_address: int):
        super().__init__(parent, name, module_address)

        self.add_parameter(
            "state",
            get_cmd=":SP4T:{}:STATE?".format(self.module_address),
            set_cmd=":SP4T:{}:STATE:{}".format(self.module_address, "{}"),
            get_parser=self._parse_response,
            vals=vals.Ints(0, 4),
            docstring="State of the SP4T switch",
        )

class SP6TModule(MiniCircuitsModule):
    """
    SP6T switch module class.
    """
    def __init__(self, parent: IPInstrument, name: str, module_address: int):
        super().__init__(parent, name, module_address)

        self.add_parameter(
            "state",
            get_cmd=":SP6T:{}:STATE?".format(self.module_address),
            set_cmd=":SP6T:{}:STATE:{}".format(self.module_address, "{}"),
            get_parser=self._parse_response,
            vals=vals.Ints(0, 6),
            docstring="State of the SP6T switch",
        )

class SP8TModule(MiniCircuitsModule):
    """
    SP8T switch module class.
    """
    def __init__(self, parent: IPInstrument, name: str, module_address: int):
        super().__init__(parent, name, module_address)

        self.add_parameter(
            "state",
            get_cmd=":SP8T:{}:STATE?".format(self.module_address),
            set_cmd=":SP8T:{}:STATE:{}".format(self.module_address, "{}"),
            get_parser=self._parse_response,
            vals=vals.Ints(0, 8),
            docstring="State of the SP8T switch",
        )

class DualSPDTModule(MiniCircuitsModule):
    """
    Dual SPDT switch module class.
    """
    def __init__(self, parent: IPInstrument, name: str, module_address: int):
        super().__init__(parent, name, module_address)

        for switch in ['A', 'B']:
            self.add_parameter(
                f"state_{switch}",
                get_cmd=f":SPDT:{self.module_address}{switch}:STATE?",
                set_cmd=f":SPDT:{self.module_address}{switch}:STATE:{{}}",
                get_parser=self._parse_response,
                vals=vals.Ints(1, 2),
                docstring=f"State of the Dual SPDT switch {switch}",
            )

class MTSModule(MiniCircuitsModule):
    """
    MTS switch module class.
    """
    def __init__(self, parent: IPInstrument, name: str, module_address: int):
        super().__init__(parent, name, module_address)

        self.add_parameter(
            "state",
            get_cmd=":MTS:{}:STATE?".format(self.module_address),
            set_cmd=":MTS:{}:STATE:{}".format(self.module_address, "{}"),
            get_parser=self._parse_response,
            vals=vals.Ints(1, 2),
            docstring="State of the MTS switch",
        )

class DualMTSModule(MiniCircuitsModule):
    """
    Dual MTS switch module class.
    """
    def __init__(self, parent: IPInstrument, name: str, module_address: int):
        super().__init__(parent, name, module_address)

        for switch in ['A', 'B']:
            self.add_parameter(
                f"state_{switch}",
                get_cmd=f":MTS:{self.module_address}{switch}:STATE?",
                set_cmd=f":MTS:{self.module_address}{switch}:STATE:{{}}",
                get_parser=self._parse_response,
                vals=vals.Ints(1, 2),
                docstring=f"State of the Dual MTS switch {switch}",
            )

class AmplifierModule(MiniCircuitsModule):
    """
    Amplifier module class.
    """
    def __init__(self, parent: IPInstrument, name: str, module_address: int):
        super().__init__(parent, name, module_address)

        self.add_parameter(
            "state",
            get_cmd=f":AMP:{self.module_address}:STATE?",
            set_cmd=f":AMP:{self.module_address}:STATE:{{}}",
            get_parser=self._parse_response,
            vals=vals.Ints(0, 1),
            docstring="State of the amplifier",
        )

class MiniCircuitsModularSystem(IPInstrument):
    """
    Driver for MiniCircuits modular system connected via ethernet.

    Args:
        name: the name of the instrument
        address: ip address ie "10.0.0.1"
        port: port to connect to default Telnet:23
    """

    def __init__(self, name: str, address: str, port: int = 23):
        super().__init__(name, address, port)
        self.flush_connection()

        modules = ChannelList(
            self, "Modules", MiniCircuitsModule, snapshotable=False
        )

        config = self.ask(":CONFIG:APP?")
        config = config.split("=")[1]
        print(config)
        module_codes = [int(code) for code in config.split(";")]

        for i, module_code in enumerate(module_codes):
            if module_code == 1:
                module = SPDTModule(self, f"module_{i+1}", i+1)
            elif module_code == 3:
                module = DualSPDTModule(self, f"module_{i+1}", i+1)
            elif module_code == 4:
                module = SP4TModule(self, f"module_{i+1}", i+1)
            elif module_code == 5 or module_code == 55:
                module = MTSModule(self, f"module_{i+1}", i+1)
            elif module_code == 7 or module_code == 57:
                module = DualMTSModule(self, f"module_{i+1}", i+1)
            elif module_code == 11 or module_code == 13:
                module = SP6TModule(self, f"module_{i+1}", i+1)
            elif module_code == 12:
                module = SP8TModule(self, f"module_{i+1}", i+1)
            elif module_code == 20:
                module = AmplifierModule(self, f"module_{i+1}", i+1)
            else:
                print('Module type with a code {module_codes} is not implemented.')
                continue
                module = MiniCircuitsModule(self, f"module_{i}", i+1)

            modules.append(module)
            self.add_submodule(f"module_{i}", module)
        self.add_submodule("modules", modules.to_channel_tuple())

        self.connect_message()