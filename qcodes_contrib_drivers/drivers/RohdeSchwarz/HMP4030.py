from .private.HMP import _RohdeSchwarzHMP


class RohdeSchwarzHMP4030(_RohdeSchwarzHMP):
    """
    This is the qcodes driver for the Rohde & Schwarz HMP4030 Power Supply
    """
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, model_no=4030, **kwargs)