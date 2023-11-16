import warnings

from .Andor_iDus4xx import AndorIDus4xx


class Andor_DU401(AndorIDus4xx):
    warnings.warn('The Andor_DU401 class name is deprecated. Please use AndorIDus4xx from '
                  'Andor_iDus4xx.py instead', DeprecationWarning)
