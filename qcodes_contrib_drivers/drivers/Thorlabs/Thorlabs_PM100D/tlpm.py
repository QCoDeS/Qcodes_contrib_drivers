from __future__ import annotations

import ctypes
import os
import pathlib
import platform
import sys
from typing import Dict, Mapping, Any

from qcodes import Instrument

_bitness = platform.architecture()[0][:2]
try:
    vxi_32 = os.environ['VXIPNPPATH']
    vxi_64 = os.environ['VXIPNPPATH64']
except KeyError:
    vxi_32 = None
    vxi_64 = None
    raise RuntimeError('IVI VXIPNP path not detected.')

if vxi_32 is not None:
    if _bitness == '64':
        dll_path = pathlib.Path(vxi_64, 'Win64', 'Bin', 'TLPM_64.dll')
    else:
        dll_path = pathlib.Path(vxi_32, 'WinNT', 'Bin', 'TLPM_32.dll')

    os.add_dll_directory(str(dll_path.parent))
    sys.path.append(str(pathlib.Path(vxi_32, 'WinNT', 'TLPM', 'Examples',
                                     'Python')))

    from TLPM import TLPM


class ThorlabsPM100D(Instrument):
    def __init__(self, name: str, addr: str = '', reset: bool = False,
                 thorlabs_tlpm: TLPM | None = None,
                 metadata: Mapping[Any, Any] | None = None,
                 label: str | None = None):
        if vxi_32 is None:
            raise FileNotFoundError('IVI VXIPNP path not detected.')

        self.tlpm = thorlabs_tlpm or TLPM()
        # NEED to call with IDQuery==True, otherwise the following error is
        # raised: NameError: The given session or object reference does not
        # support this operation.
        self.tlpm.open(addr.encode() or self._search_for_device(), True,
                       reset)

        super().__init__(name, metadata, label)

        self.add_parameter('power',
                           get_cmd=self._get_power,
                           label='Power',
                           unit='Watt')
        self.add_parameter('wavelength',
                           get_cmd=self._get_wavelength,
                           set_cmd=self._set_wavelength,
                           label='Wavelength',
                           unit='nm')

        self.connect_message()

    def _search_for_device(self) -> ctypes.Array[ctypes.c_char]:
        deviceCount = ctypes.c_uint32()
        resourceName = ctypes.create_string_buffer(1024)

        self.tlpm.findRsrc(ctypes.byref(deviceCount))

        for i in range(0, deviceCount.value):
            self.tlpm.getRsrcName(ctypes.c_int(i), resourceName)
            break

        return resourceName

    def _get_power(self) -> float:
        power = ctypes.c_double()
        self.tlpm.measPower(ctypes.byref(power))
        return power.value

    def _get_wavelength(self) -> float:
        wavelength = ctypes.c_double()
        self.tlpm.getWavelength(0, ctypes.byref(wavelength))
        return wavelength.value

    def _set_wavelength(self, wavelength: float):
        self.tlpm.setWavelength(ctypes.c_double(wavelength))

    def get_idn(self) -> Dict[str, str]:
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
