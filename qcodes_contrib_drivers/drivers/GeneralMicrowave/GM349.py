# -*- coding: UTF-8 -*-
# Tongyu Zhao <ty.zhao.work@gmail.com> summer 2022
"""
Driver for Kratos General Microwave Series 349 and 349H Attenuators.

These attenuators are passive devices that adjust attenuation
based on digital signals supplied to their J3 connector.
This driver serves as a simple wrapper to connect the
attenuators with the digital output device(s) used to drive them.

Device specification:
(https://www.kratosmed.com/gmcatalog/microwave-attenuators/
series-349-and-349h-octave-band-11-bit-digital-pin-diode-attenuators)
"""

import numpy as np

from qcodes import Instrument
from qcodes.instrument.parameter import Parameter
from qcodes.utils.validators import Numbers

class GM349Attenuation(Parameter):
    """Attenuation of GM349 attenuator.

    Parameters
    ----------
    name : string, default = 'attenuation'
        The name of the parameter.
    driver_dev : qcodes.Instrument
        The digital device used to drive the attenuator. This is usually a group of
        digital lines of a physical device.
    """
    def __init__(self, name: str, driver_dev: Instrument, **kwargs) -> None:
        super().__init__(name, **kwargs)
        self._attenuation = np.nan
        self._driver_dev = driver_dev
    
    def set_raw(self, attenuation: float):
        """Communicate with the driver device and change attenuation.

        Parameters
        ----------
        attenuation : float
            Desired attenuation, with in range (-63.97, 0).
        """
        atten_scaled = np.array([np.round(abs(attenuation)*32, 0)], dtype=np.uint16)
        atten_binary = np.unpackbits(atten_scaled.view(dtype=np.uint8), bitorder='little')[0:11]
        state = list(atten_binary == 1)

        self._driver_dev.state(state)

        self._attenuation = attenuation

    def get_raw(self):
        """Return the last set attenuation

        Returns
        -------
        float
            The last set attenuation.
        """
        return self._attenuation
        

class GM349(Instrument):
    """_summary_

    Parameters
    ----------
    name : string
        The name of the attenuator.
    driver_dev : qcodes.Instrument
        The digital device used to drive the attenuator. This is usually a group of
        digital lines of a physical device.
    """
    def __init__(self, name: str, driver_dev: Instrument, **kwargs) -> None:
        super().__init__(name, **kwargs)
        self._driver_dev = driver_dev

        if len(self._driver_dev.lines) != 11:
            raise ValueError("Driving device must have 11 digital lines!")

        pin_index = (15, 1, 2, 5, 6, 7, 8, 9, 10, 11, 12) # J3 pin index
        self._pin_map = dict(zip(pin_index, self._driver_dev.lines))

        self.add_parameter(
            name='attenuation',
            driver_dev=self._driver_dev,
            label='Attenuation',
            unit='dB',
            parameter_class=GM349Attenuation,
            vals=Numbers(min_value=-63.97,
                         max_value=0)
        )
    
    def pin_map(self):
        """Mapping between GM349 J3 connector pins and physical lines of the driver device.

        Returns
        -------
        dictionary
            A dictionary of the pin-to-digital-line mapping. The format is
            {J3 pin index: digital line}.
        """
        return self._pin_map
