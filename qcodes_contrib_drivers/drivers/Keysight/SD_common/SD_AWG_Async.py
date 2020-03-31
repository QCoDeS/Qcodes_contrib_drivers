# -*- coding: utf-8 -*-
import threading
import queue
import sys
from dataclasses import dataclass
from typing import List, Union
import time
import logging

import numpy as np

from .SD_Module import keysightSD1, result_parser
from .SD_AWG import SD_AWG
from .memory_manager import MemoryManager


def method_unavailable(func):
    """
    Decorator marking a method as unavailable.
    It throws an exception when the method is called.

    This decorator can be used to hide methods in a derived class.
    """
    def func_wrapper(self, *args, **kwargs):
        raise Exception(f"{func.__name__} is not available in '{self.__class__.__name__}'")

    return func_wrapper


class WaveformReference:
    """
    This is a reference to a waveform (being) uploaded to the AWG.

    Attributes:
        wave_number: number refering to the wave in AWG memory
        awg_name: name of the awg the waveform is uploaded to
    """
    def __init__(self, wave_number: int, awg_name: str):
        self._wave_number = wave_number
        self._awg_name = awg_name

    @property
    def wave_number(self):
        """
        Number of the wave in AWG memory.
        """
        return self._wave_number

    @property
    def awg_name(self):
        """
        Name of the AWG the waveform is uploaded to
        """
        return self._awg_name

    def release(self):
        """
        Releases the AWG memory for reuse.
        """
        raise NotImplementedError()

    def wait_uploaded(self):
        """
        Waits till waveform has been loaded.
        Returns immediately if waveform is already uploaded.
        """
        raise NotImplementedError()

    def is_uploaded(self):
        """
        Returns True if waveform has been loaded.
        """
        raise NotImplementedError()


class _WaveformReferenceInternal(WaveformReference):

    def __init__(self, allocated_slot: MemoryManager.AllocatedSlot, awg_name: str):
        super().__init__(allocated_slot.number, awg_name)
        self._allocated_slot = allocated_slot
        self._uploaded = threading.Event()
        self._upload_error: str = None
        self._released: bool = False


    def release(self):
        """
        Releases the memory for reuse.
        """
        if self._released:
            raise Exception('Reference already released')

        self._allocated_slot.release()
        self._released = True


    def wait_uploaded(self):
        """
        Waits till waveform is loaded.
        Returns immediately if waveform is already uploaded.
        """
        if self._released:
            raise Exception('Reference already released')

        # complete memory of AWG can be written in ~ 15 seconds
        ready = self._uploaded.wait(timeout=30.0)
        if not ready:
            raise Exception(f'Timeout loading wave')

        if self._upload_error:
            raise Exception(f'Error loading wave: {self.upload_error}')


    def is_uploaded(self):
        """
        Returns True if waveform has been loaded.
        """
        return self._uploaded.is_set()


    def __del__(self):
        if not self._released:
            logging.warn(f'WaveformReference was not released ({self.awg_name}:{self.wave_number}). '
                         'Automatic release in destructor.')
            self.release()


class SD_AWG_Async(SD_AWG):
    """
    Generic asynchronous driver with waveform memory management for Keysight SD AWG modules.

    This driver is derived from SD_AWG and uses a thread to upload waveforms.
    This class creates reusable memory slots of different sizes in AWG.
    It assigns waveforms to the smallest available memory slot.

    Only one instance of this class per AWG module is allowed.
    By default the maximum size of a waveform is limited to 1e6 samples.
    This limit can be increased up to 1e8 samples at the cost of a longer startup time of the threads.

    Example:
        awg1 = SW_AWG_Async('awg1', 0, 1, channels=4, triggers=8)
        awg2 = SW_AWG_Async('awg2', 0, 2, channels=4, triggers=8)
        awg3 = SW_AWG_Async('awg3', 0, 3, channels=4, triggers=8)

        # the upload to the 3 modules will run concurrently (in background)
        ref_1 = awg1.upload_waveform(wave1)
        ref_2 = awg2.upload_waveform(wave2)
        ref_3 = awg3.upload_waveform(wave3)

        trigger_mode = keysightSD1.SD_TriggerModes.EXTTRIG
        # method awg_queue_waveform blocks until reference waveform has been uploaded.
        awg1.awg_queue_waveform(1, ref_1, trigger_mode, 0, 1, 0)
        awg2.awg_queue_waveform(1, ref_2, trigger_mode, 0, 1, 0)
        awg3.awg_queue_waveform(1, ref_3, trigger_mode, 0, 1, 0)

    Args:
        name (str): an identifier for this instrument, particularly for
            attaching it to a Station.
        chassis (int): identification of the chassis.
        slot (int): slot of the module in the chassis.
        channels (int): number of channels of the module.
        triggers (int): number of triggers of the module.
        legacy_channel_numbering (bool): indicates whether legacy channel number
            should be used. (Legacy numbering starts with channel 0)
        waveform_size_limit (int): maximum size of waveform that can be uploaded
    """

    @dataclass
    class UploadAction:
        action: str
        wave: Union[List[float], List[int], np.ndarray]
        wave_ref: WaveformReference


    _ACTION_STOP = UploadAction('stop', None, None)
    _ACTION_INIT_AWG_MEMORY = UploadAction('init', None, None)

    _uploaders = {}
    """ All uploaders by unique module name. """


    def __init__(self, name, chassis, slot, channels, triggers, waveform_size_limit=1e6,
                 **kwargs):
        super().__init__(name, chassis, slot, channels, triggers, **kwargs)

        module_id = self._get_module_id()
        if module_id in SD_AWG_Async._uploaders:
            raise Exception(f'AWG uploader {module_id} already exists')

        self.module_id = module_id
        SD_AWG_Async._uploaders[self.module_id] = self

        super().flush_waveform()
        self._memory_manager = MemoryManager(self.log, waveform_size_limit)

        self._upload_queue = queue.Queue()
        self._thread = threading.Thread(target=self._run, name=f'uploader-{module_id}')
        self._thread.start()


    #
    # hide synchronous method of parent class, because wave memory is managed by this class.
    #
    @method_unavailable
    def load_waveform(self, *args, **kwargs):
        pass

    @method_unavailable
    def load_waveform_int16(self, *args, **kwargs):
        pass

    @method_unavailable
    def reload_waveform(self, *args, **kwargs):
        pass

    @method_unavailable
    def reload_waveform_int16(self, *args, **kwargs):
        pass

    @method_unavailable
    def flush_waveform(self, *args, **kwargs):
        """
        Not available. Waveform memory is managed by memory manager.
        """
        pass

    @method_unavailable
    def awg_from_file(self, *args, **kwargs):
        pass

    @method_unavailable
    def awg_from_array(self, *args, **kwargs):
        pass


    def awg_queue_waveform(self, awg_number, waveform_ref, trigger_mode, start_delay, cycles, prescaler):
        """
        Enqueus the waveform.

        Args:
            awg_number (int): awg number (channel) where the waveform is queued
            waveform_ref (WaveformReference): reference to a waveform
            trigger_mode (int): trigger method to launch the waveform
                Auto                        :   0
                Software/HVI                :   1
                Software/HVI (per cycle)    :   5
                External trigger            :   2
                External trigger (per cycle):   6
            start_delay (int): defines the delay between trigger and wf launch
                given in multiples of 10ns.
            cycles (int): number of times the waveform is repeated once launched
                zero = infinite repeats
            prescaler (int): waveform prescaler value, to reduce eff. sampling rate
        """
        if waveform_ref.awg_name != self.name:
            raise Exception(f'Waveform not uploaded to this AWG ({self.name}). '
                            f'It is uploaded to {waveform_ref.awg_name}')

        self.log.debug(f'Enqueue {waveform_ref.wave_number}')
        if not waveform_ref.is_uploaded():
            self.log.info('waiting till wave is uploaded')
            waveform_ref.wait_uploaded()

        super().awg_queue_waveform(awg_number, waveform_ref.wave_number, trigger_mode, start_delay, cycles, prescaler)


    def _get_module_id(self):
        """
        Generates a unique name for this module.
        """
        return f'{self.module_name}:{self.chassis_number()}-{self.slot_number()}'


    def set_waveform_limit(self, requested_waveform_size_limit: int):
        """
        Increases the maximum size of waveforms that can be uploaded.

        Additional memory will be reserved in the AWG.
        Limit can not be reduced, because reservation cannot be undone.

        Args:
            requested_waveform_size_limit (int): maximum size of waveform that can be uploaded
        """
        self._memory_manager.set_waveform_limit(requested_waveform_size_limit)
        self._upload_queue.put(SD_AWG_Async._ACTION_INIT_AWG_MEMORY)


    def upload_waveform(self, wave: Union[List[float], List[int], np.ndarray]) -> WaveformReference:
        '''
        Upload the wave using the uploader thread for this AWG.
        Args:
            wave: wave data to upload.
        Returns:
            reference to the wave
        '''
        if len(wave) < 2000:
            raise Exception(f'{len(wave)} is less than 2000 samples required for proper functioning of AWG')

        allocated_slot = self._memory_manager.allocate(len(wave))
        ref = _WaveformReferenceInternal(allocated_slot, self.name)
        self.log.debug(f'upload: {ref.wave_number}')

        entry = SD_AWG_Async.UploadAction('upload', wave, ref)
        self._upload_queue.put(entry)

        return ref


    def close(self):
        """
        Closes the module and stops background thread.
        """
        self.log.info(f'stopping ({self.module_id})')
        self._upload_queue.put(SD_AWG_Async._ACTION_STOP)
        # wait at most 15 seconds. Should be more enough for normal scenarios
        self._thread.join(15)
        if self._thread.is_alive():
            self.log.error(f'AWG upload thread {self.module_id} stop failed. Thread still running.')
        del SD_AWG_Async._uploaders[self.module_id]
        super().close()


    def _init_awg_memory(self):
        '''
        Initialize memory on the AWG by uploading waveforms with all zeros.
        '''
        new_slots = self._memory_manager.get_uninitialized_slots()
        if len(new_slots) > 0:
            self.log.info(f'Reserving awg memory for {len(new_slots)} slots')

        zeros = []
        for slot in new_slots:
            start = time.perf_counter()
            if len(zeros) != slot.size:
                zeros = np.zeros(slot.size, np.float)
                wave = keysightSD1.SD_Wave()
                result_parser(wave.newFromArrayDouble(keysightSD1.SD_WaveformTypes.WAVE_ANALOG, zeros))
            super().load_waveform(wave, slot.number)
            duration = time.perf_counter() - start
            self.log.debug(f'uploaded {slot.size} in {duration*1000:5.2f} ({slot.size/duration/1e6:5.2f} MSa/s)')


    def _run(self):
        self._init_awg_memory()
        self.log.info('Uploader ready')

        while True:
            entry: SD_AWG_Async.UploadItem = self._upload_queue.get()
            if entry == SD_AWG_Async._ACTION_STOP:
                break

            if entry == SD_AWG_Async._ACTION_INIT_AWG_MEMORY:
                self._init_awg_memory()
                continue

            wave_ref = entry.wave_ref
            self.log.debug(f'Uploading {wave_ref.wave_number}')
            try:
                start = time.perf_counter()

                wave = keysightSD1.SD_Wave()
                result_parser(wave.newFromArrayDouble(keysightSD1.SD_WaveformTypes.WAVE_ANALOG, entry.wave))
                super().reload_waveform(wave, wave_ref.wave_number)

                duration = time.perf_counter() - start
                speed = len(entry.wave)/duration
                self.log.debug(f'Uploaded {wave_ref.wave_number} in {duration*1000:5.2f} ms ({speed/1e6:5.2f} MSa/s)')
            except:
                ex = sys.exc_info()
                msg = f'{ex[0].__name__}:{ex[1]}'
                self.log.error(f'Failure load waveform {wave_ref.wave_number}: {msg}' )
                wave_ref._upload_error = msg

            # signal upload done, either successful or with error
            wave_ref._uploaded.set()

        self.log.info('Uploader terminated')
