ConnexionErrors = {
    0x00: 'Success',
    0x01: 'The FTDI functions have not been initialized',
    0x02: 'The device could not be found',
    0x03: 'The device must be opened before it can be accessed',
    0x04: 'An I/O error has occured in the FTDI chip',
    0x05: 'There are insufficient resources to run this application',
    0x06: 'An invalid parameter has been supplied to the device',
    0x07: 'The device is no longer present',
    0x08: 'The device detected does not match that expected',
    0x10: 'The library for this device could not be found',
    0x11: 'No functions available for this device',
    0x12: 'The function is not available for this device',
    0x13: 'Bad function pointer detected',
    0x14: 'The generic function failed to complete successfully',
    0x15: 'The specific function failed to complete succesfully'
}

GeneralErrors = {
    0x20: 'Attempt to open a device that was already open',
    0x21: 'The device has stopped responding',
    0x22: 'This function has not been implemented',
    0x23: 'The device has reported a fault',
    0x24: 'The function could not be completed at this time',
    0x28: 'The function could not be completed because the device is disconnected',
    0x29: 'The firmware has thrown an error',
    0x2A: 'The device has failed to initialize',
    0x2B: 'An invalid channel address was supplied'
}

MotorErrors = {
    0x25: 'The device cannot perform this function until it has been homed',
    0x26: 'The function cannot be performed as it would result in an illegal position',
    0x27: 'An invalid velocity parameter was supplied. The velocity must be greater than zero',
    0x2C: 'This device does not support homing. Check the limit switch parameters are correct',
    0x2D: 'An invalid jog mode was supplied for the jog function',
    0x2E: 'There is no motor parameters available to convert real world units',
    0x2F: 'Command temporarily unavailable, device may be busy.'
}