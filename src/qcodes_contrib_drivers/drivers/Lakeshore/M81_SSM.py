import time
import base64
import struct

from qcodes.instrument import VisaInstrument

from qcodes_contrib_drivers.drivers.Lakeshore.modules.vm10 import vm10
from qcodes_contrib_drivers.drivers.Lakeshore.modules.bcs10 import bcs10
from qcodes_contrib_drivers.drivers.Lakeshore.modules.vs10 import vs10
from qcodes_contrib_drivers.drivers.Lakeshore.modules.cm10 import cm10

class M81_SSM(VisaInstrument):
    """
    Driver class for the QCoDeS Lakeshore M81 *** Firmware version >= 2.1 ***
    """      
    def __init__(self, name: str, address: str, **kwargs):

        super().__init__(name, address, terminator='\r\n')

        self.add_parameter(name='keypad_lock',
                        label='keypad lock status',
                        get_cmd='SYSTem:KLOCk?',
                        get_parser = lambda status: True if int(status) == 1 else False,
                        set_cmd='SYSTem:KLOCk {}',
                        val_mapping={True: 1, False: 0}
                        )
        
        # Lock keypad at start up
        self.set('keypad_lock', True)

        self.connect_message()
        self.n_chan = int(self.ask("SOURce:NCHannels?"))
        self.source_module_list = self._get_source_module_list()
        self.sense_module_list = self._get_sense_module_list()

        for module in self.source_module_list:
            parts = str(module).split(':')
            chan = parts[0].strip()
            module_type = parts[1].strip()
            match module_type:
                case '"BCS-10"': self.add_submodule(f'S{chan}', bcs10(self, 'BCS_10', f'S{chan}'))
                case '"VS-10"': self.add_submodule(f'S{chan}', vs10(self, 'VS_10', f'S{chan}'))
                case _: pass #print(f"Unknown source module {type}")

        for module in self.sense_module_list:
            parts = str(module).split(':')
            chan = parts[0].strip()
            module_type = parts[1].strip()
            match module_type:
                case '"CM-10"': self.add_submodule(f'M{chan}', cm10(self, 'CM_10', f'M{chan}'))
                case '"VM-10"': self.add_submodule(f'M{chan}', vm10(self, 'VM_10', f'M{chan}'))
                case _: pass #print(f"Unknown sense module {type}")

    def show_system_info(self):
        print(f"Fitted with {self.n_chan} channel(s)")
        print("Source (S):")
        for module in self.source_module_list:
            print(f"\t{module}")
        print("Sense  (M):")
        for module in self.sense_module_list:
            print(f"\t{module}")
    
    def _get_source_module_list(self):
        full_source_list = []
        for i in range (1, self.n_chan+1):
            full_source_list.append((f"{i} : {self.ask(f'SOURce{i}:MODel?')}"))
        return full_source_list

    def _get_sense_module_list(self):
        full_sense_list = []
        for i in range (1, self.n_chan+1):
            full_sense_list.append((f"{i} : {self.ask(f'SENSe{i}:MODel?')}"))
        return full_sense_list

    data_source_types = {
        'RTIMe': float,
        'SAMPlitude': float,
        'SOFFset': float,
        'SFRequency': float,
        'SRANge': float,
        'SVLimit': lambda s: bool(int(s)),
        'SILimit': lambda s: bool(int(s)),
        'MDC': float,
        'MRMs': float,
        'MPPeak': float,
        'MNPeak': float,
        'MPTPeak': float,
        'MX': float,
        'MY': float,
        'MR': float,
        'MTHeta': float,
        'MRANge': float,
        'MOVerload': lambda s: bool(int(s)),
        'MSETtling': lambda s: bool(int(s)),
        'MUNLock': lambda s: bool(int(s)),
        'MRFRequency': float,
        'GPIStates': int,
        'GPOStates': int,
    }
    
    def _configure_stream_elements(self, data_sources):
        """
        Sets the elements to include in the data stream. Takes a list of pairs of data source mnemonic and channel number. Up to 10 pairs.
        """
        elements = ','.join('{},{}'.format(mnemonic, index) for (mnemonic, index) in data_sources)
        self.write('TRACe:FORMat:ELEMents {}'.format(elements))
        
    def stream_data(self, rate, num_points, *data_sources, transpose_data=True):
        """Generator object to stream data from the instrument.

            Args:
                rate (int): Desired transfer rate in samples/sec. The maximum stream rate is 5000 samples/s.
                num_points (int): Number of points to return. None to stream indefinitely.
                data_sources (str, int): Variable length list of pairs of (DATASOURCE_MNEMONIC, CHANNEL_INDEX).
                transpose_data (bool): transposes the data retured to get an array for each parameter streamed.

            Yields:
                Stream data as a list
        """

        self._configure_stream_elements(data_sources)

        self.write('TRACe:RESEt')

        self.write('TRACe:FORMat:ENCOding B64')

        self.write('TRACe:RATE {}'.format(rate))

        #start streaming
        self.write('TRACe:STARt {}'.format(num_points))
        print('Streaming...')

        # data counter
        count = 0
        while count < num_points:
            time.sleep(1) # or what ever small value
            count = int(self.ask("TRACe:DATA:COUNt?"))
            print(f"\rBuffered points: {count}         ", end="", flush=True)
    
        time.sleep(1)
        print('\r')
        
        # pull data
        string_bytes = base64.b64decode(self.ask('TRACe:DATA:ALL?')).hex()

        format_val = self.ask('TRACe:FORMat:ENCOding:B64:BFORmat?').strip('\"')
        data_format = f"<{format_val}"

        data_list = [] 
        for data in struct.iter_unpack(data_format, bytes.fromhex(string_bytes)):
            data_list.append(data)
                
        if len(data_list)==num_points:
            print('All data collected.')
        elif len(data_list)!=num_points:
            print(f'Only {len(data_list)} data points collected.')

        if transpose_data == True:
            data_list = [list(x) for x in zip(*data_list)]
            
        return data_list

    def close(self) -> None:
        """
        Close connection to device.
        """
        # Unlock keypad on exit
        self.set('keypad_lock', False)

        super().close()
        print('Connection closed to M81.')
        