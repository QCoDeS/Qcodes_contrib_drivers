from .private.HMP import _RohdeSchwarzHMP


class RohdeSchwarzHMP4040(_RohdeSchwarzHMP):
    """
    This is the qcodes driver for the Rohde & Schwarz HMP2030 Power Supply
    """
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, model_no=2030, **kwargs)