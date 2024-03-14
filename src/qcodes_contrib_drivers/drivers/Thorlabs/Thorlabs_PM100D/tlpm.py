from __future__ import annotations

import ctypes
import os
import pathlib
import platform
import sys
from typing import Dict, Mapping, Any

from qcodes import Instrument

vxi_32 = os.environ.get('VXIPNPPATH')
vxi_64 = os.environ.get('VXIPNPPATH64')

if sys.platform == 'win32' and vxi_32 is not None:
    if platform.architecture()[0][:2] == '64' and vxi_64 is not None:
        dll_path = pathlib.Path(vxi_64, 'Win64', 'Bin', 'TLPM_64.dll')
    else:
        dll_path = pathlib.Path(vxi_32, 'WinNT', 'Bin', 'TLPM_32.dll')

    os.add_dll_directory(str(dll_path.parent))
    sys.path.append(str(pathlib.Path(vxi_32, 'WinNT', 'TLPM', 'Examples',
                                     'Python')))

    import TLPM


class ThorlabsPM100D(Instrument):
    """TLPM driver for Thorlabs PM100D power meter.

    This driver wraps the example Python driver bundled with the
    Optical Power Monitor software which can be downloaded `here`_.

    .. _here: https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=OPM

    Args:
        name:
            An identifier for this instrument.
        address (optional):
            The USB address for the device. If omitted, the first
            available device found will be used.
        reset (optional):
            Reset the instrument on connection. Defaults to False.
        thorlabs_tlpm (optional):
            An instance of the :class:`TLPM` class from the power
            monitor software examples.
        metadata (optional):
            Additional static metadata.
        label (optional):
            Nicely formatted name of the instrument.

    Raises:
        FileNotFoundError:
            If the dll is not found.

    """

    def __init__(self, name: str, address: str = '', reset: bool = False,
                 thorlabs_tlpm: TLPM.TLPM | None = None,
                 metadata: Mapping[Any, Any] | None = None,
                 label: str | None = None):
        if sys.platform != 'win32':
            raise NotImplementedError('This driver is only available on '
                                      'Windows.')
        if vxi_32 is None:
            raise FileNotFoundError('IVI VXIPNP path not detected.')

        self.tlpm = thorlabs_tlpm or TLPM.TLPM()
        # NEED to call with IDQuery==True, otherwise the following error is
        # raised: NameError: The given session or object reference does not
        # support this operation.
        self.tlpm.open(address.encode() or self._search_for_device(), True,
                       reset)

        super().__init__(name, metadata, label)

        self.add_parameter('power',
                           get_cmd=self._get_power,
                           label='Power',
                           unit='W')
        self.add_parameter('wavelength',
                           get_cmd=self._get_wavelength,
                           set_cmd=self._set_wavelength,
                           label='Wavelength',
                           unit='nm')
        self.add_parameter('averaging_time',
                           get_cmd=self._get_averaging_time,
                           set_cmd=self._set_averaging_time,
                           label='Averaging time',
                           unit='s')

        self.connect_message()

    def _search_for_device(self) -> ctypes.Array[ctypes.c_char]:
        deviceCount = ctypes.c_uint32()
        resourceName = ctypes.create_string_buffer(1024)

        self.tlpm.findRsrc(ctypes.byref(deviceCount))

        for i in range(0, deviceCount.value):
            self.tlpm.getRsrcName(ctypes.c_int(i), resourceName)
            break
        else:
            raise ValueError('No devices found.')

        return resourceName

    def _get_power(self) -> float:
        power = ctypes.c_double()
        self.tlpm.measPower(ctypes.byref(power))
        return power.value

    def _get_wavelength(self) -> float:
        wavelength = ctypes.c_double()
        self.tlpm.getWavelength(TLPM.TLPM_ATTR_SET_VAL,
                                ctypes.byref(wavelength))
        return wavelength.value

    def _set_wavelength(self, wavelength: float):
        self.tlpm.setWavelength(ctypes.c_double(wavelength))

    def _get_averaging_time(self) -> float:
        avgTime = ctypes.c_double()
        self.tlpm.getAvgTime(TLPM.TLPM_ATTR_SET_VAL, ctypes.byref(avgTime))
        return avgTime.value

    def _set_averaging_time(self, time: float):
        self.tlpm.setAvgTime(ctypes.c_double(time))

    def get_idn(self) -> Dict[str, str | None]:
        manufacturerName = ctypes.create_string_buffer(1024)
        deviceName = ctypes.create_string_buffer(1024)
        serialNumber = ctypes.create_string_buffer(1024)
        firmwareRevision = ctypes.create_string_buffer(1024)

        self.tlpm.identificationQuery(manufacturerName, deviceName,
                                      serialNumber, firmwareRevision)

        return {'vendor': manufacturerName.value.decode(),
                'model': deviceName.value.decode(),
                'serial': serialNumber.value.decode(),
                'firmware': firmwareRevision.value.decode()}

    def close(self):
        self.tlpm.close()
        super().close()
