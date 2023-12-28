import re
import numpy as np
import pandas as pd
from typing import Any, Dict, Optional
from qcodes import VisaInstrument, InstrumentChannel
from qcodes.utils.validators import Enum, Ints
from qcodes.utils.helpers import create_on_off_val_mapping
from pathlib import Path

class M8190AChannel(InstrumentChannel):
    def __init__(self, parent: VisaInstrument, name: str, channel: str) -> Any:
        super().__init__(parent, name)
        self._channel = channel

        self.add_parameter(name="sample_clock_source",
                           docstring="Set or query the selected clock source for a channel.",
                           get_cmd=f":FREQ:RAST:SOUR{self._channel}?",
                           set_cmd=f":FREQ:RAST:SOUR{self._channel} "+"{}",
                           vals=Enum("INT", "EXT"))

        self.add_parameter(name="output_mode",
                           docstring="Set or get the waveform output mode.",
                           get_cmd=f":TRAC{self._channel}:DWID?",
                           set_cmd=f":TRAC{self._channel}:DWID "+"{}",
                           vals=Enum(*self.parent._waveform_mode_list))

        self.add_parameter(name="output_path",
                           docstring="Set or query the output path.",
                           get_cmd=f":OUTP{self._channel}:ROUT?",
                           set_cmd=f":OUTP{self._channel}:ROUT "+"{}",
                           vals=Enum("DAC", "DC", "AC"))

        self.add_parameter(name="output_format",
                           docstring="Set or query the DAC format mode.",
                           get_cmd=self._get_format,
                           set_cmd=self._set_format,
                           vals=Enum("RZ", "DNRZ", "NRZ", "DOUB"))

        self.add_parameter(name="output_amplitude",
                           unit="V",
                           docstring="Set or query the output amplitude.",
                           get_cmd=self._get_amplitude,
                           set_cmd=self._set_amplitude)

        self.add_parameter(name="output_offset",
                           unit="V",
                           docstring="Set or query the output offset.",
                           get_cmd=self._get_offset,
                           set_cmd=self._set_offset)

        self.add_parameter(name="differential_offset",
                           docstring="Specifies an offset adjustment to compensate for small offset differences between normal and complement output.",
                           get_cmd=f":OUTP{self._channel}:DIOF?",
                           set_cmd=f":OUTP{self._channel}:DIOF "+"{}")

        self.add_parameter(name="fine_delay",
                           docstring="Set or query the fine delay settings. The unit is in picoseconds.",
                           unit="ps",
                           get_cmd=f":ARM:DEL{self._channel}?",
                           set_cmd=self._set_fine_delay,
                           get_parser=lambda x : float(x)*1e12)

        self.add_parameter(name="corse_delay",
                           docstring="Set or query the corse delay settings. The unit is in picoseconds.",
                           unit="ps",
                           get_cmd=f":ARM:CDEL{self._channel}?",
                           set_cmd=self._set_corse_delay,
                           get_parser=lambda x : float(x)*1e12)

        self.add_parameter(name="reduced_noise_floor",
                           docstring="Set or query the state of the “Reduced Noise Floor” feature.",
                           get_cmd=f":ARM:RNO{self._channel}?",
                           set_cmd=f":ARM:RNO{self._channel} "+"{}",
                           val_mapping=create_on_off_val_mapping(on_val="1", off_val="0"))

        self.add_parameter(name="normal_output",
                           docstring="Switch (normal) output on or off.",
                           get_cmd=f":OUTP{self._channel}:NORM?",
                           set_cmd=f":OUTP{self._channel}:NORM "+"{}",
                           val_mapping=create_on_off_val_mapping(on_val="1", off_val="0"))

        self.add_parameter(name="complement_output",
                           docstring="Switch complement output on or off.",
                           get_cmd=f":OUTP{self._channel}:COMP?",
                           set_cmd=f":OUTP{self._channel}:COMP "+"{}",
                           val_mapping=create_on_off_val_mapping(on_val="1", off_val="0"))

        self.add_parameter(name="termination_voltage",
                           docstring="Set or query the termination voltage level.",
                           unit="V",
                           get_cmd=self._get_termination_voltage,
                           set_cmd=self._set_termination_voltage)

        # trigger/advance/enable hardware disabled state
        self.add_parameter(name="disable_trigger_hardware_input",
                           docstring="Set or query the hardware input disable state for the trigger function.",
                           get_cmd=f":TRIG:BEG{self._channel}:HWD?",
                           set_cmd=f":TRIG:BEG{self._channel}:HWD "+"{}",
                           val_mapping=create_on_off_val_mapping(on_val="1", off_val="0"))

        self.add_parameter(name="disable_advancement_hardware_input",
                           docstring="Set or query the hardware input disable state for the advancement function.",
                           get_cmd=f":TRIG:ADV{self._channel}:HWD?",
                           set_cmd=f":TRIG:ADV{self._channel}:HWD "+"{}",
                           val_mapping=create_on_off_val_mapping(on_val="1", off_val="0"))

        self.add_parameter(name="disable_enable_hardware_input",
                           docstring="Set or query the hardware input disable state for the enable function.",
                           get_cmd=f":TRIG:ENAB{self._channel}:HWD?",
                           set_cmd=f":TRIG:ENAB{self._channel}:HWD "+"{}",
                           val_mapping=create_on_off_val_mapping(on_val="1", off_val="0"))

        # marker settings
        self.add_parameter(name="sync_marker_amplitude",
                           unit="V",
                           docstring="Set or query the output amplitude for sync marker.",
                           get_cmd=self._get_sync_marker_amplitude,
                           set_cmd=self._set_sync_marker_amplitude)

        self.add_parameter(name="sync_marker_offset",
                           unit="V",
                           docstring="Set or query the output offset for sync marker.",
                           get_cmd=self._get_sync_marker_offset,
                           set_cmd=self._set_sync_marker_offset)

        self.add_parameter(name="sample_marker_amplitude",
                           unit="V",
                           docstring="Set or query the output amplitude for sample marker.",
                           get_cmd=self._get_sample_marker_amplitude,
                           set_cmd=self._set_sample_marker_amplitude)

        self.add_parameter(name="sample_marker_offset",
                           unit="V",
                           docstring="Set or query the output offset for sample marker.",
                           get_cmd=self._get_sample_marker_offset,
                           set_cmd=self._set_sample_marker_offset)

        self.add_parameter(name="trigger_mode",
                           docstring="Set or query the trigger mode of current channel.",
                           get_cmd=self._get_trigger_mode,
                           set_cmd=self._set_trigger_mode,
                           vals=Enum("Continuous", "Gated", "Triggered"))

        self.add_parameter(name="gate_state",
                           docstring="In gated mode send a 'gate open' or 'gate close' to current channel.",
                           get_cmd=self._get_gate_state,
                           set_cmd=self._set_gate_state,
                           val_mapping=create_on_off_val_mapping(on_val="1", off_val="0"))

        self.add_parameter(name="sequencing_mode",
                           docstring="Set or query the type of waveform that will be generated.",
                           get_cmd=f":FUNC{self._channel}:MODE?",
                           set_cmd=f":FUNC{self._channel}:MODE "+"{}",
                           val_mapping={"arbitrary": "ARB",
                                        "sequence": "STS",
                                        "scenario": "STSC"})

        self.add_parameter(name="arm_mode",
                           docstring="Set or query the arming mode.",
                           get_cmd=f":INIT:CONT{self._channel}:ENAB?",
                           set_cmd=f":INIT:CONT{self._channel}:ENAB "+"{}",
                           vals=Enum("ARM", "SELF"))

        self.add_parameter(name="dynamic_control",
                           docstring="Enable or disable dynamic mode.",
                           get_cmd=f":STAB{self._channel}:DYN?",
                           set_cmd=f":STAB{self._channel}:DYN "+"{}",
                           val_mapping=create_on_off_val_mapping(on_val="1", off_val="0"))

        # selected segment properties
        self.add_parameter(name="select_segment",
                           docstring="Selects the segment, which is output by the instrument in arbitrary function mode.\n\n"+
                                     "In dynamic segment selection mode it selects the segment that is played "+
                                     "before the first segment is dynamically selected.",
                           get_cmd=self._selected_segment,
                           set_cmd=self._select_segment,
                           vals=Ints(min_value=1, max_value=self.parent._segment_limit))

        self.add_parameter(name="segment_advance_mode",
                           docstring="Set or query the advancement mode for the selected segment.",
                           get_cmd=f":TRAC{self._channel}:ADV?",
                           set_cmd=self._set_segment_advance_mode,
                           val_mapping={"Auto": "AUTO",
                                        "Conditional": "COND",
                                        "Repeat": "REP",
                                        "Single": "SING"})

        self.add_parameter(name="segment_loop_count",
                           docstring="Set or query the loop count for the selected segment.",
                           get_cmd=f":TRAC{self._channel}:COUN?",
                           set_cmd=self._set_segment_loop_count,
                           get_parser=int)

        self.add_parameter(name="segment_marker",
                           docstring="Set or query the marker state for the selected segment.",
                           get_cmd=f":TRAC{self._channel}:MARK?",
                           set_cmd=self._set_segment_marker,
                           val_mapping=create_on_off_val_mapping(on_val="1", off_val="0"))

        self.add_parameter(name="select_sequence",
                           docstring="Selects the sequence, which is output by the instrument in sequence function mode.\n\n"+
                                     "In dynamic segment selection mode it selects the sequence that is played "+
                                     "before the first sequence is dynamically selected.",
                           get_cmd=self._selected_sequence,
                           set_cmd=self._select_sequence,
                           vals=Ints(min_value=1))

    def check_error(func):
        def check(*args, **kwargs):
            rtn = func(*args, **kwargs)
            status = args[0].parent.error()
            if status["error code"] != 0:
                raise RuntimeError(status["error message"])
            return rtn
        return check

    @check_error
    def abort(self):
        """Stops signal generation on channel. If channels are coupled, both channels are stopped.
        """
        self.parent.write(f":ABOR{self._channel}")
        return None

    @check_error
    def force_enable(self):
        """Send the enable event to current channel.
        """
        self.parent.write(f":TRIG:ENAB{self._channel}")
        return None

    @check_error
    def force_event(self):
        """Send the enable event to current channel.
        """
        self.parent.write(f":TRIG:ADV{self._channel}")
        return None

    @check_error
    def force_trigger(self):
        """In triggered mode send the start/begin event to current channel.
        """
        if self.trigger_mode() != "Triggered":
            raise ValueError("The channel is not in Triggered mode.")

        self.parent.write(f":TRIG:BEG{self._channel}")
        return None

    @check_error
    def run(self):
        """Start signal generation on current channel. If channels are coupled, both channels are started.
        """
        self.parent.write(f":INIT:IMM{self._channel}")
        return None

    @check_error
    def import_csv(self, file_path: str, segment_id: int):
        """Import .CSV waveform file.

        Parameters
        ----------
        file_path : str
            full path to the wavform data file
        segment_id : int
            the number of the segment, into which the data will be written
        """
        if segment_id > self.parent._segment_limit:
            raise ValueError("Segment_ID is out of range!")

        path = Path(file_path)
        cmd_string = f':TRAC{self._channel}:IQIM {segment_id}, "{str(path)}", CSV, IONLY, ON, ALEN'
        self.parent.write(cmd_string)

        return None

    @check_error
    def create_segment(self, segment_id: int, length: int, init_value=0):
        """Create a waveform memory segment.

        Parameters
        ----------
        segment_id : int
            id of the segment, 1~512k for option SEQ, 1 if not installed
        length : int
            length of the segment in samples for direct modes
        init_value : int, optional
            optional initialization value, by default 0

        Raises
        ------
        ValueError
            If segment ID is not allowed.
        """
        if (segment_id < 1) or (segment_id > self._parent._segment_limit):
            raise ValueError("Segment ID is out of range!")

        output_mode = self.output_mode()

        if output_mode == "WPR":
            vector_size = 48
            min_seg_size = 240
        elif output_mode == "WSP":
            vector_size = 64
            min_seg_size = 320
        else:
            vector_size = 24
            min_seg_size = 120

        length = max(int(np.ceil(length/vector_size)*vector_size), min_seg_size)

        self.parent.write(f":TRAC{self._channel}:DEF {segment_id},{length},{init_value}")

        return None

    @check_error
    def create_new_segment(self, length: int, init_value=0):
        """Create a new waveform memory segment and return the segment ID.

        Parameters
        ----------
        length : int
            length of the segment in samples for direct modes
        init_value : int, optional
            optional initialization value, by default 0

        Return
        ------
        int
            ID of the newly created segment
        """
        segment_id = self.parent.ask(f":TRAC{self._channel}:DEF:NEW? {length},{init_value}")

        return int(segment_id)

    @check_error
    def delete_segment(self, segment_id: int):
        """Delete a segment.

        Parameters
        ----------
        segment_id : int
            ID of the segment to be deleted
        """
        self.parent.write(f":TRAC{self._channel}:DEL {segment_id}")

        return None

    @check_error
    def delete_all_segments(self):
        """Delete all segments
        """
        self.parent.write(f":TRAC{self._channel}:DEL:ALL")
        return None

    @check_error
    def write_list_to_segment(self, segment_id: int, data: list, sample_markers: list, sync_markers: list, offset: int=0):
        """Write data from a list to a waveform memory segment.

        Parameters
        ----------
        data : list
            list of data to write, ranging [-1, 1]
        """
        if (max(data) > 1) or (min(data) < -1):
            raise ValueError("Data list has value out of range [-1, 1]!")

        output_mode = self.output_mode()

        if output_mode == "WPR":
            resolution = 14
            vector_size = 48
            min_seg_size = 240
        elif output_mode == "WSP":
            resolution = 12
            vector_size = 64
            min_seg_size = 320
        else:
            resolution = 15
            vector_size = 24
            min_seg_size = 120

        # back pad data list with zeros such that len(data) is integer multiple
        # of vector_size and not less than min_seg_size
        if output_mode in ["WPR", "WSP"]:
            length = int(np.ceil(len(data)/vector_size)*vector_size)
            if length < min_seg_size:
                length = min_seg_size
            data_padded = data + (length - len(data))*[0]
            synm_padded = sync_markers + (length - len(data))*[0]
            smpm_padded = sample_markers + (length - len(data))*[0]
        else:
            length = int(np.ceil(len(data[0])/vector_size)*vector_size)
            if length < min_seg_size:
                length = min_seg_size
            data_padded = [i + (length - len(i))*[0] for i in data]
            synm_padded = sync_markers + (length - len(data[0]))*[0]
            smpm_padded = sample_markers + (length - len(data[0]))*[0]

        # translate data to 16-bit unsigned integer
        min_val = -2**(resolution-1)
        max_val = 2**(resolution-1) - 1
        if output_mode == "WPR":
            data_bitstring = [f"{self.scale2int(x, min_val, max_val)-min_val:b}".zfill(resolution)+f"{int(y)}"+f"{int(z)}" for x, y, z in zip(data_padded, synm_padded, smpm_padded)]
        elif output_mode == "WSP":
            data_bitstring = [f"{self.scale2int(x, min_val, max_val)-min_val:b}".zfill(resolution)+"00"+f"{int(y)}"+f"{int(z)}" for x, y, z in zip(data_padded, synm_padded, smpm_padded)]

        data_translated = [int(s, 2)-2**15 for s in data_bitstring]

        numeric_value = f"{data_translated[0]}"
        for val in data_translated[1:]:
            numeric_value += f",{val}"

        self.parent.write(f":TRAC{self._channel}:DATA {segment_id},{offset},{numeric_value}")

        return None
    
    @check_error
    def write_list_to_binary(self, file: Path, data: list, sample_markers: list, sync_markers: list):
        """Write data from a list to a binary file.

        Parameters
        ----------
        data : list
            list of data to write, ranging [-1, 1]
        """
        if (max(data) > 1) or (min(data) < -1):
            raise ValueError("Data list has value out of range [-1, 1]!")

        output_mode = self.output_mode()

        if output_mode == "WPR":
            resolution = 14
            vector_size = 48
            min_seg_size = 240
        elif output_mode == "WSP":
            resolution = 12
            vector_size = 64
            min_seg_size = 320
        else:
            resolution = 15
            vector_size = 24
            min_seg_size = 120

        # back pad data list with zeros such that len(data) is integer multiple
        # of vector_size and not less than min_seg_size
        if output_mode in ["WPR", "WSP"]:
            length = int(np.ceil(len(data)/vector_size)*vector_size)
            if length < min_seg_size:
                length = min_seg_size
            data_padded = data + (length - len(data))*[0]
            synm_padded = sync_markers + (length - len(data))*[0]
            smpm_padded = sample_markers + (length - len(data))*[0]
        else:
            length = int(np.ceil(len(data[0])/vector_size)*vector_size)
            if length < min_seg_size:
                length = min_seg_size
            data_padded = [i + (length - len(i))*[0] for i in data]
            synm_padded = sync_markers + (length - len(data[0]))*[0]
            smpm_padded = sample_markers + (length - len(data[0]))*[0]

        # translate data to 16-bit unsigned integer
        min_val = -2**(resolution-1)
        max_val = 2**(resolution-1) - 1
        if output_mode == "WPR":
            data_bitstring = [f"{self.scale2int(x, min_val, max_val)-min_val:b}".zfill(resolution)+f"{int(y)}"+f"{int(z)}" for x, y, z in zip(data_padded, synm_padded, smpm_padded)]
        elif output_mode == "WSP":
            data_bitstring = [f"{self.scale2int(x, min_val, max_val)-min_val:b}".zfill(resolution)+"00"+f"{int(y)}"+f"{int(z)}" for x, y, z in zip(data_padded, synm_padded, smpm_padded)]

        data_translated = [int(s, 2)-2**15 for s in data_bitstring]

        byte_list = [x.to_bytes(2, 'little', signed=True) for x in data_translated]
        data = b''.join(byte_list)

        with open(file, "wb") as binary_file:
        
            # Write bytes to file
            binary_file.write(data)

        return None
    
    @check_error
    def load_binary_file(self, file: Path, segment_id: int):
        """Load a .bin file.

        Parameters
        ----------
        """
        self.parent.write(f':TRAC{self._channel}:IQIM {segment_id}, "{str(file)}", BIN, IONLY, ON, ALEN')
        return None

    @check_error
    def segment_list(self):
        """Returns a list of segment-ids that are defined and the length of each segment

        Returns
        -------
        pandas.DataFrame
            a pandas DataFrame of segment-ids and the length of each segment
        """
        l = self.parent.ask(f":TRAC{self._channel}:CAT?")

        segments = {"segment_idx": [int(x) for x in l.split(",")[0::2]],
                    "segment_length": [int(x) for x in l.split(",")[1::2]]}

        df = pd.DataFrame(segments)
        df = df.set_index(df.columns[0])

        return df

    @check_error
    def create_new_sequence(self, length: int):
        sequence_id = self.parent.ask(f":SEQ{self._channel}:DEF:NEW? {length}")

        return int(sequence_id)

    @check_error
    def sequence_list(self):
        """Returns a list of sequence-ids that are defined and the length of each sequence

        Returns
        -------
        pandas.DataFrame
            a pandas DataFrame of sequence-ids and the length of each sequence
        """
        l = self.parent.ask(f":SEQ{self._channel}:CAT?")

        sequences = {"sequence_idx": [int(x) for x in l.split(",")[0::2]],
                     "sequence_length": [int(x) for x in l.split(",")[1::2]]}

        df = pd.DataFrame(sequences)
        df = df.set_index(df.columns[0])

        return df

    @check_error
    def sequence_table(self, sequence_id: int, sequence_length: int):
        """Returns a tabel of sequence properties

        Returns
        -------
        pandas.DataFrame
            a pandas DataFrame of sequence properties
        """
        s = self.parent.ask(f":STAB{self._channel}:DATA? {sequence_id}, {6*sequence_length}")

        property_list = self.parse_stable_query(s)

        column_names = ["Entry Type", "Segment Number",
                        "Segment Loop Count", "Segment Start Offset",
                        "Segment End Offset", "Segment Advancement",
                        "Marker Enabled", "New Sequence", "End Sequence",
                        "Sequence Loop Count", "Sequence Advancement",
                        "Idle Delay", "Idle Sample"]

        df = pd.DataFrame(index=range(sequence_id, sequence_id+sequence_length), columns=column_names)

        advancement_mode_dict = {0: "Auto",
                                 1: "Conditional",
                                 2: "Repeat",
                                 3: "Single"}

        for idx, seq in enumerate(property_list):
            idx += sequence_id
            if seq[0] == 0:
                df.loc[idx, "Entry Type"] = "Data"
                df.loc[idx, "Segment Number"] = seq[-3]
                df.loc[idx, "Segment Loop Count"] = seq[-4]
                df.loc[idx, "Segment Start Offset"] = seq[-2]
                df.loc[idx, "Segment End Offset"] = seq[-1]
                df.loc[idx, "Segment Advancement"] = advancement_mode_dict[seq[6]]
                df.loc[idx, "Marker Enabled"] = bool(seq[4])
                df.loc[idx, "New Sequence"] = bool(seq[3])
                df.loc[idx, "End Sequence"] = bool(seq[1])
                if seq[3]:
                    df.loc[idx, "Sequence Loop Count"] = seq[-5]
                    df.loc[idx, "Sequence Advancement"] = advancement_mode_dict[seq[5]]
            elif seq[-4] == 1:
                df.loc[idx, "Entry Type"] = "Config"
                df.loc[idx, "Segment Number"] = seq[-3]
                df.loc[idx, "Segment Start Offset"] = seq[-2]
                df.loc[idx, "Segment End Offset"] = seq[-1]
                df.loc[idx, "Segment Advancement"] = advancement_mode_dict[seq[6]]
                df.loc[idx, "Marker Enabled"] = bool(seq[4])
                df.loc[idx, "New Sequence"] = bool(seq[3])
                df.loc[idx, "End Sequence"] = bool(seq[1])
                if seq[3]:
                    df.loc[idx, "Sequence Loop Count"] = seq[-5]
                    df.loc[idx, "Sequence Advancement"] = advancement_mode_dict[seq[5]]
            elif seq[-2] == 192:
                df.loc[idx, "Entry Type"] = "Empty"
                df.loc[idx, "Idle Delay"] = seq[-2]
            else:
                df.loc[idx, "Entry Type"] = "Idle"
                df.loc[idx, "Idle Sample"] = seq[-3]
                df.loc[idx, "Idle Delay"] = seq[-2]
                df.loc[idx, "New Sequence"] = bool(seq[3])
                df.loc[idx, "End Sequence"] = bool(seq[1])
                if seq[3]:
                    df.loc[idx, "Sequence Loop Count"] = seq[-5]
                    df.loc[idx, "Sequence Advancement"] = advancement_mode_dict[seq[5]]

        return df

    def initialize_sequence_table(self, sequence_id: int, sequence_length: int):
        column_names = ["Entry Type", "Segment Number",
                        "Segment Loop Count", "Segment Start Offset",
                        "Segment End Offset", "Segment Advancement",
                        "Marker Enabled", "New Sequence", "End Sequence",
                        "Sequence Loop Count", "Sequence Advancement",
                        "Idle Delay", "Idle Sample"]

        df = pd.DataFrame(index=range(sequence_id, sequence_id+sequence_length),
                          columns=column_names)

        return df

    @check_error
    def write_df_to_seq_table(self, df: pd.DataFrame, sequence_id: int, sequence_length: int):
        advancement_mode_dict = {"Auto": 0,
                                "Conditional": 1,
                                "Repeat": 2,
                                "Single": 3}

        property_list = []

        for idx in range(sequence_length):
            idx += sequence_id
            seq = [0]*16
            if df.loc[idx, "Entry Type"] == "Data":
                seq[0] = 0
                seq[-3] = df.loc[idx, "Segment Number"]
                seq[-4] = df.loc[idx, "Segment Loop Count"]
                seq[-2] = df.loc[idx, "Segment Start Offset"]
                seq[-1] = df.loc[idx, "Segment End Offset"]
                seq[6] = advancement_mode_dict[df.loc[idx, "Segment Advancement"]]
                seq[4] = int(df.loc[idx, "Marker Enabled"])
                seq[3] = int(df.loc[idx, "New Sequence"])
                seq[1] = int(df.loc[idx, "End Sequence"])
                if seq[3]:
                    seq[-5] = df.loc[idx, "Sequence Loop Count"]
                    seq[5] = advancement_mode_dict[df.loc[idx, "Sequence Advancement"]]
                else:
                    seq[-5] = 1        
            elif df.loc[idx, "Entry Type"] == "Config":
                seq[0] = 1
                seq[-4] = 1
                seq[-3] = df.loc[idx, "Segment Number"]
                seq[-2] = df.loc[idx, "Segment Start Offset"]
                seq[-1] = df.loc[idx, "Segment End Offset"]
                seq[6] = advancement_mode_dict[df.loc[idx, "Segment Advancement"]]
                seq[4] = int(df.loc[idx, "Marker Enabled"])
                seq[3] = int(df.loc[idx, "New Sequence"])
                seq[1] = int(df.loc[idx, "End Sequence"])
                if seq[3]:
                    seq[-5] = df.loc[idx, "Sequence Loop Count"]
                    seq[5] = advancement_mode_dict[df.loc[idx, "Sequence Advancement"]]
                else:
                    seq[-5] = 1
            elif df.loc[idx, "Entry Type"] == "Empty":
                seq[0] = 1
                seq[-4] = 0
                seq[-2] = 192
                seq[-2] = df.loc[idx, "Idle Delay"]
            else:
                seq[0] = 1
                seq[-4] = 0
                seq[-3] = df.loc[idx, "Idle Sample"]
                seq[-2] = df.loc[idx, "Idle Delay"]
                seq[3] = int(df.loc[idx, "New Sequence"])
                seq[1] = int(df.loc[idx, "End Sequence"])
                if seq[3]:
                    seq[-5] = df.loc[idx, "Sequence Loop Count"]
                    seq[5] = advancement_mode_dict[df.loc[idx, "Sequence Advancement"]]
                else:
                    seq[-5] = 1
                    
            property_list.append(seq)

        l = [[str(x) for x in seq] for seq in property_list]
        for idx, seq in enumerate(l):
            seq.insert(11, "0"*12)
            seq.insert(4, "000")
            seq[6] = f"{int(seq[6]):b}".zfill(4)
            seq[7] = f"{int(seq[7]):b}".zfill(4)

            if seq[-1] == "-1":
                seq[-1] = "#hFFFFFFFF"

            l[idx] = [str(int("".join(seq[0:13]), 2))] + seq[13:]

        s = ",".join([",".join(x) for x in l])

        self.parent.write(f":STAB{self._channel}:DATA {sequence_id},{s}")

        return None

    @check_error
    def reset_sequence_table(self):
        self.parent.write(f":STAB{self._channel}:RES")

        return None

    @check_error
    def delete_sequence(self, sequence_id: int):
        """Delete a sequence.

        Parameters
        ----------
        sequence_id : int
            ID of the sequence to be deleted
        """
        self.parent.write(f":SEQ{self._channel}:DEL {sequence_id}")

        return None

    @check_error
    def delete_all_sequences(self):
        """Delete all sequences
        """
        self.parent.write(f":SEQ{self._channel}:DEL:ALL")
        return None

    @check_error
    def _set_gate_state(self, state):
        if self.trigger_mode() != "Gated":
            raise ValueError("The channel is not in Gated mode.")

        self.parent.write(f":TRIG:BEG{self._channel}:GATE {state}")
        return None

    @check_error
    def _get_gate_state(self):
        if self.trigger_mode() != "Gated":
            raise ValueError("The channel is not in Gated mode.")

        string = self.parent.ask(f":TRIG:BEG{self._channel}:GATE?")
        return string

    @check_error
    def _get_format(self):
        string = self.parent.ask(f":{self.output_path()}{self._channel}:FORM?")
        return string

    @check_error
    def _set_format(self, format: str):
        self.parent.write(f":{self.output_path()}{self._channel}:FORM {format}")
        return None

    @check_error
    def _get_amplitude(self):
        string = self.parent.ask(f":{self.output_path()}{self._channel}:VOLT:AMPL?")
        return float(string)

    @check_error
    def _set_amplitude(self, amplitude: float):
        if self.output_path() == "DAC":
            min_lim = 0.1
            max_lim = 0.7
        elif self.output_path() == "DC":
            min_lim = 0.15
            max_lim = 1
        else:
            min_lim = 0.1
            max_lim = 2

        clipped_amplitude = np.clip(amplitude, min_lim, max_lim)

        if amplitude > max_lim:
            print(f"Input value is greater than allowed range. Clipped to upper bound {max_lim}V.")
        elif amplitude < min_lim:
            print(f"Input value is smaller than allowed range. Clipped to lower bound {min_lim}V.")
        self.parent.write(f":{self.output_path()}{self._channel}:VOLT:AMPL {clipped_amplitude}")
        return None

    @check_error
    def _get_offset(self):
        if self.output_path() not in ["DC", "DAC"]:
            raise ValueError("Only DAC or DC output path has offset setting.")

        string = self.parent.ask(f":{self.output_path()}{self._channel}:VOLT:OFFS?")
        return float(string)

    @check_error
    def _set_offset(self, offset: float):
        if self.output_path() not in ["DC", "DAC"]:
            raise ValueError("Only DAC or DC output path has offset setting.")

        if self.output_path() == "DAC":
            min_lim = -0.02
            max_lim = 0.02
        else:
            min_lim = max(-0.925, self.termination_voltage()-1)
            max_lim = min(3.225, self.termination_voltage()+1)

        clipped_offset = np.clip(offset, min_lim, max_lim)
        if offset > max_lim:
            print(f"Input value is greater than allowed range. Clipped to upper bound {max_lim}V.")
        elif offset < min_lim:
            print(f"Input value is smaller than allowed range. Clipped to lower bound {min_lim}V.")
        self.parent.write(f":{self.output_path()}{self._channel}:VOLT:OFFS {clipped_offset}")
        return None

    @check_error
    def _get_termination_voltage(self):
        if self.output_path() not in ["DC"]:
            raise ValueError("Only DC output path has termination voltage setting.")

        string = self.parent.ask(f":{self.output_path()}{self._channel}:VOLT:TERM?")
        return float(string)

    @check_error
    def _set_termination_voltage(self, termination_offset: float):
        if self.output_path() not in ["DC"]:
            raise ValueError("Only DC output path has termination voltage setting.")

        min_lim = max(-1.5, self.output_offset()-1)
        max_lim = min(3.5, self.output_offset()+1)

        clipped_termination_offset = np.clip(termination_offset, min_lim, max_lim)
        if termination_offset > max_lim:
            print(f"Input value is greater than allowed range. Clipped to upper bound {max_lim}V.")
        elif termination_offset < min_lim:
            print(f"Input value is smaller than allowed range. Clipped to lower bound {min_lim}V.")
        self.parent.write(f":{self.output_path()}{self._channel}:VOLT:TERM {clipped_termination_offset}")
        return None

    @check_error
    def _set_fine_delay(self, fine_delay: float):
        if self.reduced_noise_floor():
            raise ValueError("Not able to set fine or corse delay while Reduced Noise Floor is enabled.")

        if self.sample_clock_source() == "INT":
            sampling_rate = self.parent.internal_sample_frequency()
        else:
            sampling_rate = self.parent.external_sample_frequency()

        min_lim = 0
        if sampling_rate >= 6.25e9:
            max_lim = 30
        elif sampling_rate >= 2.5e9:
            max_lim = 60
        else:
            max_lim = 150

        clipped_fine_delay = np.clip(fine_delay, min_lim, max_lim)
        self.parent.write(f":ARM:DEL{self._channel} {clipped_fine_delay/1e12:.2e}")
        if fine_delay > max_lim:
            print(f"Input value is greater than allowed range. Clipped to upper bound {max}ps.")
        elif fine_delay < min_lim:
            print(f"Input value is smaller than allowed range. Clipped to lower bound {min}ps.")

        return None

    @check_error
    def _set_corse_delay(self, corse_delay: float):
        if self.reduced_noise_floor():
            raise ValueError("Not able to set fine or corse delay while Reduced Noise Floor is enabled.")

        clipped_corse_delay = np.clip(corse_delay, 0, 10000)
        self.parent.write(f":ARM:CDEL{self._channel} {clipped_corse_delay/1e12}")
        if corse_delay > 10000:
            print(f"Input value is greater than allowed range. Clipped to upper bound {max}ps.")
        elif corse_delay < 0:
            print(f"Input value is smaller than allowed range. Clipped to lower bound {min}ps.")

        return None

    @check_error
    def _get_sync_marker_amplitude(self):
        string = self.parent.ask(f":MARK{self._channel}:SYNC:VOLT:AMPL?")
        return float(string)

    @check_error
    def _set_sync_marker_amplitude(self, amplitude: float):

        offset = self.sync_marker_offset()
        min_lim = 0
        max_lim = min(1+2*offset, 2*(1.75-offset))

        clipped_amplitude = np.clip(amplitude, min_lim, max_lim)

        if amplitude > max_lim:
            print(f"Input value is greater than allowed range. Clipped to upper bound {max_lim}V.")
        elif amplitude < min_lim:
            print(f"Input value is smaller than allowed range. Clipped to lower bound {min_lim}V.")
        self.parent.write(f":MARK{self._channel}:SYNC:VOLT:AMPL {clipped_amplitude}")
        return None

    @check_error
    def _get_sync_marker_offset(self):
        string = self.parent.ask(f":MARK{self._channel}:SYNC:VOLT:OFFS?")
        return float(string)

    @check_error
    def _set_sync_marker_offset(self, offset: float):

        amplitude = self.sync_marker_amplitude()
        min_lim = round(200*(-0.5+amplitude/2))/200
        max_lim = round(100*(1.75-amplitude/2))/100

        clipped_offset = np.clip(offset, min_lim, max_lim)

        if offset > max_lim:
            print(f"Input value is greater than allowed range. Clipped to upper bound {max_lim}V.")
        elif offset < min_lim:
            print(f"Input value is smaller than allowed range. Clipped to lower bound {min_lim}V.")
        self.parent.write(f":MARK{self._channel}:SYNC:VOLT:OFFS {clipped_offset}")
        return None

    @check_error
    def _get_sample_marker_amplitude(self):
        string = self.parent.ask(f":MARK{self._channel}:SAMP:VOLT:AMPL?")
        return float(string)

    @check_error
    def _set_sample_marker_amplitude(self, amplitude: float):

        offset = self.sample_marker_offset()
        min_lim = 0
        max_lim = min(1+2*offset, 2*(1.75-offset))

        clipped_amplitude = np.clip(amplitude, min_lim, max_lim)

        if amplitude > max_lim:
            print(f"Input value is greater than allowed range. Clipped to upper bound {max_lim}V.")
        elif amplitude < min_lim:
            print(f"Input value is smaller than allowed range. Clipped to lower bound {min_lim}V.")
        self.parent.write(f":MARK{self._channel}:SAMP:VOLT:AMPL {clipped_amplitude}")
        return None

    @check_error
    def _get_sample_marker_offset(self):
        string = self.parent.ask(f":MARK{self._channel}:SAMP:VOLT:OFFS?")
        return float(string)

    @check_error
    def _set_sample_marker_offset(self, offset: float):
        amplitude = self.sample_marker_amplitude()
        min_lim = round(200*(-0.5+amplitude/2))/200
        max_lim = round(100*(1.75-amplitude/2))/100

        clipped_offset = np.clip(offset, min_lim, max_lim)

        if offset > max_lim:
            print(f"Input value is greater than allowed range. Clipped to upper bound {max_lim}V.")
        elif offset < min_lim:
            print(f"Input value is smaller than allowed range. Clipped to lower bound {min_lim}V.")
        self.parent.write(f":MARK{self._channel}:SAMP:VOLT:OFFS {clipped_offset}")
        return None

    @check_error
    def _get_trigger_mode(self):
        is_continuous_mode = int(self.parent.ask(f":INIT:CONT{self._channel}:STAT?"))
        is_gate_mode = int(self.parent.ask(f":INIT:GATE{self._channel}:STAT?"))

        if is_continuous_mode:
            return "Continuous"
        elif is_gate_mode:
            return "Gated"
        else:
            return "Triggered"

    @check_error
    def _set_trigger_mode(self, mode: str):
        if mode == "Continuous":
            self.parent.write(f":INIT:CONT{self._channel}:STAT ON")
        elif mode == "Gated":
            self.parent.write(f":INIT:CONT{self._channel}:STAT OFF")
            self.parent.write(f":INIT:GATE{self._channel}:STAT ON")
        else:
            self.parent.write(f":INIT:CONT{self._channel}:STAT OFF")
            self.parent.write(f":INIT:GATE{self._channel}:STAT OFF")

        return None

    @check_error
    def _set_segment_advance_mode(self, mode: str):
        if self.sequencing_mode() != "arbitrary":
            raise ValueError("This setting is only valid when the segment is played in arbitrary mode.")
        
        self.parent.write(f":TRAC{self._channel}:ADV {mode}")

        return None

    @check_error
    def _set_segment_loop_count(self, count: int):
        if self.sequencing_mode() != "arbitrary":
            raise ValueError("This setting is only valid when the segment is played in arbitrary mode.")
        
        self.parent.write(f":TRAC{self._channel}:COUN {count}")

        return None

    @check_error
    def _set_segment_marker(self, state: str):
        self.parent.write(f":TRAC{self._channel}:MARK {state}")

        return None

    @check_error
    def _select_segment(self, segment_id: int):
        if self.sequencing_mode() != "arbitrary":
            raise ValueError("This setting only applies when current channel is in Arbitrary sequencing mode.")

        self.parent.write(f":TRAC{self._channel}:SEL {segment_id}")
        return None

    @check_error
    def _selected_segment(self):
        if self.sequencing_mode() != "arbitrary":
            raise ValueError("This setting only applies when current channel is in Arbitrary sequencing mode.")

        segment_id = self.parent.ask(f":TRAC{self._channel}:SEL?")
        return int(segment_id)

    @check_error
    def _select_sequence(self, sequence_id: int):
        if self.sequencing_mode() != "sequence":
            raise ValueError("This setting only applies when current channel is in Sequence sequencing mode.")

        self.parent.write(f":STAB{self._channel}:SEQ:SEL {sequence_id}")
        return None

    @check_error
    def _selected_sequence(self):
        if self.sequencing_mode() != "sequence":
            raise ValueError("This setting only applies when current channel is in Sequence sequencing mode.")

        sequence_id = self.parent.ask(f":STAB{self._channel}:SEQ:SEL?")
        return int(sequence_id)

    @staticmethod
    def scale2int(x: float, min: int, max: int):
        return round((max-min)/2*x+(max+min)/2)

    @staticmethod
    def parse_control_parameter(control_string: str):
        bit_string = f"{int(control_string):b}".zfill(32)

        pattern = '(\d)(\d)(\d)(\d)(\d{3})(\d)(\d{4})(\d{4})(\d)(\d)(\d)(\d)(\d*)'
        matched_string = list(re.match(pattern, bit_string).groups())

        # delete unused bits
        del matched_string[4]
        del matched_string[-1]

        return [int(x, 2) for x in matched_string]

    @staticmethod
    def parse_stable_query(query_return: str):
        list_splitted = query_return.split(',')
        num_seq = int(len(list_splitted)/6)
        grouped_list = [[] for _ in range(num_seq)]
        for idx, item in enumerate(list_splitted):
            grouped_list[idx // 6].append(item)

        #parse the elements
        l = [M8190AChannel.parse_control_parameter(x[0]) + list(map(int, x[1:])) for x in grouped_list]

        return l

class M8190A(VisaInstrument):
    """
    This is the qcodes driver for Keysight/Agilent M8190A.
    """

    def __init__(self, name: str, address: str, **kwargs: Any):
        super().__init__(name, address, terminator='\n', **kwargs)

        # Query the instrument for installed options
        self._options = self.ask('*OPT?').split(',')

        if "001" in self._options: # Number of channels option
            self._num_of_channel = 1
        else:
            self._num_of_channel = 2

        self._waveform_mode_list = []
        if "14B" in self._options: # high precision option
            self._waveform_mode_list.append("WPR")
        if "12G" in self._options: # high speed option
            self._waveform_mode_list.append("WSP")
        if "DUC" in self._options: # interpolate option
            self._waveform_mode_list += ["INTX3", "INTX12", "INTX24", "INTX48"]

        if "SEQ" in self._options:
            self._segment_limit = 512000
        else:
            self._segment_limit = 1

        for chan in range(self._num_of_channel):
            channel = M8190AChannel(self, f"Ch{chan+1}", channel=chan+1)
            self.add_submodule(f"Ch{chan+1}", channel)

        # clock settings
        self.add_parameter(name="reference_clock_source",
                           docstring="Set or query the reference clock source.",
                           get_cmd=":ROSC:SOUR?",
                           set_cmd=":ROSC:SOUR {}",
                           vals=Enum("EXT", "INT", "AXI"))

        self.add_parameter(name="reference_clock_frequency",
                           docstring="Set or query the expected reference clock frequency, if the external reference clock source is selected.",
                           unit="Hz",
                           get_cmd=":ROSC:FREQ?",
                           set_cmd=":ROSC:FREQ {}")

        self.add_parameter(name="internal_sample_frequency",
                           unit="Hz",
                           docstring="Set or query the internal sample frequency.",
                           get_cmd=":FREQ:RAST?",
                           set_cmd=":FREQ:RAST {}",
                           get_parser=float)

        self.add_parameter(name="external_sample_frequency",
                           unit="Hz",
                           docstring="Set or query the external sample frequency.",
                           get_cmd=":FREQ:RAST:EXT?",
                           set_cmd=":FREQ:RAST:EXT {}",
                           get_parser=float)

        self.add_parameter(name="sample_clock_output",
                           docstring="Select which clock source is routed to the SCLK output",
                           get_cmd=":OUTP:SCLK:SOUR?",
                           set_cmd=":OUTP:SCLK:SOUR {}",
                           vals=Enum("EXT", "INT"))

        self.add_parameter(name="channel_coupling",
                           docstring="Switch coupling on/off.",
                           get_cmd=":INST:COUP:STAT?",
                           set_cmd=":INST:COUP:STAT {}",
                           val_mapping=create_on_off_val_mapping(on_val="1", off_val="0"))

        # trigger settings
        self.add_parameter(name="advancement_event",
                           docstring="Set or query the source for the advancement event.",
                           get_cmd=":TRIG:SOUR:ADV?",
                           set_cmd=":TRIG:SOUR:ADV {}",
                           vals=Enum("TRIG", "EVEN", "INT"))

        self.add_parameter(name="enable_event",
                           docstring="Set or query the source for the enable event.",
                           get_cmd=":TRIG:SOUR:ENAB?",
                           set_cmd=":TRIG:SOUR:ENAB {}",
                           vals=Enum("TRIG", "EVEN"))

        self.add_parameter(name="trigger_source",
                           docstring="Set or query the source for the trigger function.",
                           get_cmd=":ARM:TRIG:SOUR?",
                           set_cmd=":ARM:TRIG:SOUR {}",
                           vals=Enum("EXT", "INT"))

        self.add_parameter(name="trigger_input_threshold",
                           unit="V",
                           docstring="Set or query the trigger input threshold level.",
                           get_cmd=":ARM:TRIG:LEV?",
                           set_cmd=":ARM:TRIG:LEV {}",
                           get_parser=float)

        self.add_parameter(name="trigger_input_polarity",
                           docstring="Set or query the trigger input slope.",
                           get_cmd=":ARM:TRIG:SLOP?",
                           set_cmd=":ARM:TRIG:SLOP {}",
                           vals=Enum("POS", "NEG", "EITH"))

        self.add_parameter(name="trigger_input_impedance",
                           docstring="Set or query the trigger input impedance.",
                           get_cmd=":ARM:TRIG:IMP?",
                           set_cmd=":ARM:TRIG:IMP {}",
                           vals=Enum("LOW", "HIGH"))

        self.add_parameter(name="internal_trigger_frequency",
                           unit="Hz",
                           docstring="Set or query the frequency of the internal trigger generator.",
                           get_cmd=":ARM:TRIG:FREQ?",
                           set_cmd=":ARM:TRIG:FREQ {}",
                           get_parser=float)

        self.add_parameter(name="event_input_threshold",
                           unit="V",
                           docstring="Set or query the event input threshold level.",
                           get_cmd=":ARM:EVEN:LEV?",
                           set_cmd=":ARM:EVEN:LEV {}",
                           get_parser=float)

        self.add_parameter(name="event_input_polarity",
                           docstring="Set or query the event input slope.",
                           get_cmd=":ARM:EVEN:SLOP?",
                           set_cmd=":ARM:EVEN:SLOP {}",
                           vals=Enum("POS", "NEG", "EITH"))

        self.add_parameter(name="event_input_impedance",
                           docstring="Set or query the event input impedance.",
                           get_cmd=":ARM:EVEN:IMP?",
                           set_cmd=":ARM:EVEN:IMP {}",
                           vals=Enum("LOW", "HIGH"))

        self.add_parameter(name="valid_bits",
                           docstring="Set or query the number of valid bits of the dynamic control input.",
                           get_cmd=":ARM:DYNP:WIDT?",
                           set_cmd=":ARM:DYNP:WIDT {}",
                           val_mapping={"AllBits": "ALLB",
                                        "LowerBits": "LOW"})

    def check_error(func):
        def check(*args, **kwargs):
            func(*args, **kwargs)
            status = args[0].error()
            if status["error code"] != 0:
                raise RuntimeError(status["error message"])
        return check

    @check_error
    def reset(self):
        """Reset instrument to its factory default state.
        """
        self.write("*RST")

        return None

    def error(self):
        string = self.ask(":SYST:ERR?")
        matched_string = re.match('([-\d]*),"(.*)"', string).groups()

        return {"error code": int(matched_string[0]), "error message": matched_string[1]}

    @check_error
    def get_idn(self) -> Dict[str, Optional[str]]:
        IDN_str = self.ask_raw('*IDN?')
        vendor, model, serial, firmware = map(str.strip, IDN_str.split(','))
        IDN: Dict[str, Optional[str]] = {
            'vendor': vendor, 'model': model,
            'serial': serial, 'firmware': firmware}
        return IDN
