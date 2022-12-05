from collections import ChainMap
from qcodes.instrument.channel import InstrumentChannel
from qcodes.instrument.instrument_base import InstrumentBase
from qcodes.instrument.visa import VisaInstrument

class SiglentChannel(InstrumentChannel):
    def __init__(self, parent: InstrumentBase, name:str, **kwargs):
        super().__init__(parent, name, kwargs)

class Siglent(VisaInstrument):
    def __init__(self, *args, **kwargs):
        kwargs = ChainMap(kwargs, {"terminator": "\n"}) 
        super().__init__(*args, **kwargs)
