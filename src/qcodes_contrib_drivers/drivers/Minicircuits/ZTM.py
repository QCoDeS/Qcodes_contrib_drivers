import math
from typing import Optional

from qcodes import validators as vals
from qcodes.instrument import ChannelList, InstrumentChannel, IPInstrument

class MiniCircuitsModule(InstrumentChannel):
    """
    The `MiniCircuitsModule` class is a parent class for all the MiniCircuits modules. It provides the basic functionality for the modules.
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
    The `SPDTModule` class represents a single-pole double-throw (SPDT) switch module. It provides the functionality to get and set the state of the SPDT switch.
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
    The `SP4TModule` class represents a single-pole four-throw (SP4T) switch module. It provides the functionality to get and set the state of the SP4T switch.
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
    The `SP6TModule` class represents a single-pole six-throw (SP6T) switch module. It provides the functionality to get and set the state of the SP6T switch.
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
    The `SP8TModule` class represents a single-pole eight-throw (SP8T) switch module. It provides the functionality to get and set the state of the SP8T switch.
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
    The `DualSPDTModule` class represents a dual single-pole double-throw (SPDT) switch module. It provides the functionality to get and set the state of both SPDT switches.
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
    The `MTSModule` class represents a multi-throw switch (MTS) module. It provides the functionality to get and set the state of the MTS switch.
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
    The `DualMTSModule` class represents a dual multi-throw switch (MTS) module. It provides the functionality to get and set the state of both MTS switches.
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
    The `AmplifierModule` class represents an amplifier module. It provides the functionality to get and set the state of the amplifier.
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
    The `MiniCircuitsModularSystem` class represents a MiniCircuits modular system connected via ethernet. It provides the functionality to initialize the modules based on the configuration received from the instrument.

    Args:
        name: the name of the instrument
        address: ip address ie "10.0.0.1"
        port: port to connect to default Telnet:23

    Example:
        # Import the required module
        from qcodes.instrument_drivers.MiniCircuitsModularSystem import MiniCircuitsModularSystem

        # Initialize the MiniCircuitsModularSystem
        mini_circuits = MiniCircuitsModularSystem('MiniCircuits', '10.0.0.1', 23)

        # Access the SP6T module
        sp6t_module = mini_circuits.module_1  # assuming the SP6T module is the first module

        # Set the state of the SP6T module
        sp6t_module.state(3)  # set the state to 3

        # Get the state of the SP6T module
        print(sp6t_module.state())  # prints the current state of the SP6T module

        # Access the DualMTSModule
        dual_mts_module = mini_circuits.module_2  # assuming the DualMTSModule is the second module

        # Set the state of the DualMTSModule
        dual_mts_module.state_A(1)  # set the state of switch A to 1
        dual_mts_module.state_B(2)  # set the state of switch B to 2

        # Get the state of the DualMTSModule
        print(dual_mts_module.state_A())  # prints the current state of switch A
        print(dual_mts_module.state_B())  # prints the current state of switch B

        # Access the AmplifierModule
        amplifier_module = mini_circuits.module_3  # assuming the AmplifierModule is the third module

        # Set the state of the AmplifierModule
        amplifier_module.state(1)  # turn on the amplifier

        # Get the state of the AmplifierModule
        print(amplifier_module.state())  # prints the current state of the amplifier
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

        module: MiniCircuitsModule  # Declare module variable as MiniCircuitsModule type

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