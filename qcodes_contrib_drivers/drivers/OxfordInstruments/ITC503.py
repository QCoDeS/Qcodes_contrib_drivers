# This Python file uses the following encoding: utf-8

"""
Created by Paritosh Karnatak <paritosh.karnatak@unibas.ch>, Feb 2019
Updated by Elyjah <elyjah.kiyooka@cea.fr>, Jan 2022

"""

import logging
from qcodes import VisaInstrument
from qcodes import validators as vals
from qcodes.utils.validators import Numbers, Ints, Enum, Strings
from typing import Dict, ClassVar
from time import sleep
import visa


log = logging.getLogger(__name__)

class ITC503(VisaInstrument):
	"""
	The qcodes driver for communication with
    ITC503, "Oxford Instruments Intelligent Temperature Controller"
	"""

	def __init__(self, name: str, address: str, number=1, **kwargs):

		log.debug('Initializing instrument')
		super().__init__(name, address, **kwargs)

		self._address = address
		self._number = number
		self._values = {}

		self.visa_handle.write_termination='\r'
		self.visa_handle.read_termination='\r'

		# Add parameters
		self.add_parameter('temp1',
						   unit='K',
						   get_cmd=self._get_temp1,
						   set_cmd=self._set_temp1
						   )

		self.add_parameter('temp2',
						   unit='K',
						   get_cmd=self._get_temp2,
						   )

		self.add_parameter('temp3',
						   unit='K',
						   get_cmd=self._get_temp3,
						   )

		self.add_parameter('needle_valve',
						   unit='%',
						   get_cmd=self._get_needle_valve,
						   set_cmd=self._set_needle_valve
						   )

	def _execute(self, message):
		"""
		Write a command to the device
		Args:
			message (str) : write command for the device
		"""
		log.info('Send the following command to the device: %s' %
			message)
		self.visa_handle.write('%s' %  message)
		sleep(70e-3)  # wait for the device to be able to respond
		result = self._read()
		if result.find('?') >= 0:
			print("Error: Command %s not recognized" % message)
		else:
			return result

	def _read(self):
		"""
		Reads the total bytes in the buffer and outputs as a string.
		Returns:
			message (str)
		"""
		# bytes_in_buffer = self.visa_handle.bytes_in_buffer
		# with(self.visa_handle.ignore_warning(visa.constants.VI_SUCCESS_MAX_CNT)):
			# mes = self.visa_handle.visalib.read(
				# self.visa_handle.session, bytes_in_buffer)
		# mes = str(mes[0].decode())
		mes = self.visa_handle.read()
		return mes

	def _get_temp1(self):
		"""
		Read temperature for sensor 1
		Returns: result (float) : Temperature in K
		"""
		log.info('Read the temperature')
		result = self._execute('R1')
		return float(result.replace('R', ''))

	def _get_temp2(self):
		"""
		Read temperature for sensor 2
		Returns: result (float) : Temperature in K
		"""
		log.info('Read the temperature')
		result = self._execute('R2')
		return float(result.replace('R', ''))

	def _get_temp3(self):
		"""
		Read temperature for sensor 3
		Returns: result (float) : Temperature in K
		"""
		log.info('Read the temperature')
		result = self._execute('R3')
		return float(result.replace('R', ''))

	def _set_temp1(self, temperature):
		"""
		Set the temperature
		Args:
		current (float) : Temperature in K
		"""
		log.info('Setting target temperature to %s' % temperature)
		#self.remote()
		self._execute('T%s' % temperature)
		#self.local()

	def _get_needle_valve(self):
		"""
		Read Gas Flow/Needle valve value
		GAS FLOW O/P (arbitrary units)
		"""
		log.info('Read the temperature')
		result = self._execute('R7')
		return float(result.replace('R', ''))

	def _set_needle_valve(self, needle_valve):
		"""
		Set the Gas Flow/Needle valve value
		returns percentage to a resolution of 0.1%
		"""
		log.info('Setting Needle valve to %s' % needle_valve)
		self._execute('G%s' % needle_valve)
