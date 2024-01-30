# -*- coding: utf-8 -*-
import threading
import queue
import sys
from typing import Dict, List, Union, Optional, TypeVar, Callable, Any, cast
import time
import logging
from functools import wraps

import numpy as np

from .SD_Module import keysightSD1, result_parser
from .SD_AWG import SD_AWG
from .memory_manager import MemoryManager


F = TypeVar('F', bound=Callable[..., Any])

def switchable(switch: Callable[[Any], bool], enabled: bool) -> Callable[[F], F]:
    """
    This decorator enables or disables a method depending on the value of an object's method.
    It throws an exception when the invoked method is disabled.
    The wrapped method is enabled when `switch(self) == enabled`.

    Args:
        switch: method indicating switch status.
        enabled: value the switch status must have to enable the wrapped method.

    """

    def switchable_decorator(func):

        @wraps(func)
        def func_wrapper(self, *args, **kwargs):
            if switch(self) != enabled:
                switch_name = f'{type(self).__name__}.{switch.__name__}()'
                raise Exception(f'{func.__name__} is not enabled when {switch_name} == {switch(self)}')
            return func(self, *args, **kwargs)


        return func_wrapper

    return switchable_decorator


class Task:
    """
    Task to be executed asynchronously.

    Args:
        f: function to execute
        instance: object function `f` belongs to
        args: argument list to pass to function
        kwargs: keyword arguments to pass to function
    """

    verbose = False
    ''' Enables verbose logging '''

    def __init__(self, f:F, instance: Any, *args, **kwargs) -> None:
        self._event = threading.Event()
        self._f = f
        self._instance = instance
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        """
        Executes the function. The function result can be retrieved with property `result`.
        """
        start = time.perf_counter()
        if not self._instance._start_time:
            self._instance._start_time = start

        if Task.verbose:
            logging.debug(f'[{self._instance.name}] > {self._f.__name__}')
        self._result = self._f(self._instance, *self._args, **self._kwargs)
        if Task.verbose:
            total = time.perf_counter() - self._instance._start_time
            logging.debug(f'[{self._instance.name}] < {self._f.__name__} ({(time.perf_counter()-start)*1000:5.2f} ms '
                          f'/ {total*1000:5.2f} ms)')
        self._event.set()

    @property
    def result(self) -> Any:
        """
        Returns the result of the executed function.
        Waits till function has been executed.
        """
        self._event.wait()
        return self._result


def threaded(wait: bool = False) -> Callable[[F], F]:
    """
    Decoractor to execute the wrapped method in the background thread.

    Args:
        wait: if True waits till the function has been executed.
    """

    def threaded_decorator(func):

        @wraps(func)
        def func_wrapper(self, *args, **kwargs):

            task = Task(func, self, *args, **kwargs)
            self._task_queue.put(task)
            if wait:
                result = task.result
                self._start_time = None
                return result
            return (None, 'async task')

        return func_wrapper

    return threaded_decorator


class WaveformReference:
    """
    This is a reference to a waveform (being) uploaded to the AWG.

    Args:
        wave_number: number refering to the wave in AWG memory
        awg_name: name of the awg the waveform is uploaded to
    """
    def __init__(self, wave_number: int, awg_name: str) -> None:
        self._wave_number = wave_number
        self._awg_name = awg_name

    @property
    def wave_number(self) -> int:
        """
        Number of the wave in AWG memory.
        """
        return self._wave_number

    @property
    def awg_name(self) -> str:
        """
        Name of the AWG the waveform is uploaded to
        """
        return self._awg_name

    def release(self) -> None:
        """
        Releases the AWG memory for reuse.
        """
        raise NotImplementedError()

    def wait_uploaded(self) -> None:
        """
        Waits till waveform has been loaded.
        Returns immediately if waveform is already uploaded.
        """
        raise NotImplementedError()

    def is_uploaded(self) -> bool:
        """
        Returns True if waveform has been loaded.
        """
        raise NotImplementedError()


class _WaveformReferenceInternal(WaveformReference):
    """
    Reference to waveform in AWG memory.

    Args:
        allocated_slot: memory slot containing reference to address in AWG memory.
        awg_name: name of the AWG
    """

    def __init__(self, allocated_slot: MemoryManager.AllocatedSlot, awg_name: str) -> None:
        super().__init__(allocated_slot.number, awg_name)
        self._allocated_slot = allocated_slot
        self._uploaded = threading.Event()
        self._upload_error: Optional[str] = None
        self._released: bool = False
        self._queued_count: int = 0


    def release(self) -> None:
        """
        Releases the memory for reuse.
        """
        if self._released:
            raise Exception('Reference already released')

        self._released = True
        self._try_release_slot()


    def wait_uploaded(self) -> None:
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
            raise Exception(f'Error loading wave: {self._upload_error}')


    def is_uploaded(self) -> bool:
        """
        Returns True if waveform has been loaded.
        """
        if self._upload_error:
            raise Exception(f'Error loading wave: {self._upload_error}')

        return self._uploaded.is_set()


    def enqueued(self) -> None:
        self._queued_count += 1


    def dequeued(self) -> None:
        self._queued_count -= 1
        self._try_release_slot()


    def _try_release_slot(self) -> None:
        if self._released and self._queued_count <= 0:
            self._allocated_slot.release()


    def __del__(self) -> None:
        if not self._released:
            logging.warning(f'WaveformReference was not released '
                            f'({self.awg_name}:{self.wave_number}). Automatic '
                            f'release in destructor.')
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

    The memory manager and asynchronous functionality can be disabled to restore the behavior of
    the parent class. The instrument can then be used with old synchronous code.

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
        asynchronous (bool): if False the memory manager and asynchronous functionality are disabled.
    """

    _modules: Dict[str, 'SD_AWG_Async'] = {}
    """ All async modules by unique module id. """

    def __init__(self, name, chassis, slot, channels, triggers, waveform_size_limit=1e6,
                 asynchronous=True, **kwargs) -> None:
        super().__init__(name, chassis, slot, channels, triggers, **kwargs)

        self._asynchronous = False
        self._waveform_size_limit = waveform_size_limit
        self._start_time = None

        module_id = self._get_module_id()
        if module_id in SD_AWG_Async._modules:
            raise Exception(f'AWG module {module_id} already exists')

        self.module_id = module_id
        SD_AWG_Async._modules[self.module_id] = self

        self.set_asynchronous(asynchronous)


    def asynchronous(self) -> bool:
        ''' Returns True if module is in asynchronous mode. '''
        return self._asynchronous


    def set_asynchronous(self, asynchronous: bool) -> None:
        """
        Enables asynchronous loading and memory manager if `asynchronous` is True.
        Otherwise disables both.

        Args:
            asynchronous: new asynchronous state.
        """
        if asynchronous == self._asynchronous:
            return

        self._asynchronous = asynchronous

        if asynchronous:
            self._start_asynchronous()
        else:
            self._stop_asynchronous()

    #
    # disable synchronous method of parent class, when wave memory is managed by this class.
    #
    @switchable(asynchronous, enabled=False)
    def load_waveform(self, waveform_object: keysightSD1.SD_Wave, waveform_number: int,
                      verbose: bool = False) -> int:
        """
        Loads the specified waveform into the module onboard RAM.
        Waveforms must be created first as an instance of the SD_Wave class.

        Args:
            waveform_object: pointer to the waveform object
            waveform_number: waveform number to identify the waveform in
                subsequent related function calls.
            verbose: boolean indicating verbose mode

        Returns:
            available onboard RAM in waveform points, or negative numbers for
                errors
        """
        return super().load_waveform(waveform_object, waveform_number, verbose)

    @switchable(asynchronous, enabled=False)
    def load_waveform_int16(self, waveform_type: int, data_raw: List[int],
                            waveform_number: int, verbose: bool = False) -> int:
        """
        Loads the specified waveform into the module onboard RAM.
        Waveforms must be created first as an instance of the SD_Wave class.

        Args:
            waveform_type: waveform type
            data_raw: array with waveform points
            waveform_number: waveform number to identify the waveform
                in subsequent related function calls.
            verbose: boolean indicating verbose mode

        Returns:
            available onboard RAM in waveform points, or negative numbers for
                errors
        """
        return super().load_waveform_int16(waveform_type, data_raw, waveform_number, verbose)

    @switchable(asynchronous, enabled=False)
    def reload_waveform(self, waveform_object: keysightSD1.SD_Wave, waveform_number: int,
                        padding_mode: int = 0, verbose: bool = False) -> int:
        """
        Replaces a waveform located in the module onboard RAM.
        The size of the new waveform must be smaller than or
        equal to the existing waveform.

        Args:
            waveform_object: pointer to the waveform object
            waveform_number: waveform number to identify the waveform
                in subsequent related function calls.
            padding_mode:
                0:  the waveform is loaded as it is, zeros are added at the
                    end if the number of points is not a multiple of the number
                    required by the AWG.
                1:  the waveform is loaded n times (using DMA) until the total
                    number of points is multiple of the number required by the
                    AWG. (only works for waveforms with even number of points)
            verbose: boolean indicating verbose mode

        Returns:
            available onboard RAM in waveform points, or negative numbers for
                errors
        """
        return super().reload_waveform(waveform_object, waveform_number, padding_mode, verbose)

    @switchable(asynchronous, enabled=False)
    def reload_waveform_int16(self, waveform_type: int, data_raw: List[int],
                              waveform_number: int, padding_mode: int = 0,
                              verbose: bool = False) -> int:
        """
        Replaces a waveform located in the module onboard RAM.
        The size of the new waveform must be smaller than or
        equal to the existing waveform.

        Args:
            waveform_type: waveform type
            data_raw: array with waveform points
            waveform_number: waveform number to identify the waveform
                in subsequent related function calls.
            padding_mode:
                0:  the waveform is loaded as it is, zeros are added at the
                    end if the number of points is not a multiple of the number
                    required by the AWG.
                1:  the waveform is loaded n times (using DMA) until the total
                    number of points is multiple of the number required by the
                    AWG. (only works for waveforms with even number of points)
            verbose: boolean indicating verbose mode

        Returns:
            available onboard RAM in waveform points, or negative numbers for
                errors
        """
        return super().reload_waveform_int16(waveform_type, data_raw, waveform_number, padding_mode, verbose)

    @switchable(asynchronous, enabled=False)
    def flush_waveform(self, verbose: bool = False) -> None:
        """
        Deletes all waveforms from the module onboard RAM and flushes all the
        AWG queues.
        """
        super().flush_waveform(verbose)

    @switchable(asynchronous, enabled=False)
    def awg_from_file(self, awg_number: int, waveform_file: str,
                      trigger_mode: int, start_delay: int, cycles: int,
                      prescaler: int, padding_mode: int = 0,
                      verbose: bool = False) -> int:
        """
        Provides a one-step method to load, queue and start a single waveform
        in one of the module AWGs.

        Loads a waveform from file.

        Args:
            awg_number: awg number where the waveform is queued
            waveform_file: file containing the waveform points
            trigger_mode: trigger method to launch the waveform
                Auto                        :   0
                Software/HVI                :   1
                Software/HVI (per cycle)    :   5
                External trigger            :   2
                External trigger (per cycle):   6
            start_delay: defines the delay between trigger and wf launch
                given in multiples of 10ns.
            cycles: number of times the waveform is repeated once launched
                zero = infinite repeats
            prescaler: waveform prescaler value, to reduce eff. sampling rate

        Returns:
            available onboard RAM in waveform points, or negative numbers for
                errors
        """
        return super().awg_from_file(awg_number, waveform_file, trigger_mode, start_delay,
                                     cycles, prescaler, padding_mode, verbose)

    @switchable(asynchronous, enabled=False)
    def awg_from_array(self, awg_number: int, trigger_mode: int,
                       start_delay: int, cycles: int, prescaler: int,
                       waveform_type: int,
                       waveform_data_a: List[Union[int, float]],
                       waveform_data_b: Optional[
                           List[Union[int, float]]] = None,
                       padding_mode: int = 0, verbose: bool = False) -> int:
        """
        Provides a one-step method to load, queue and start a single waveform
        in one of the module AWGs.

        Loads a waveform from array.

        Args:
            awg_number: awg number where the waveform is queued
            trigger_mode: trigger method to launch the waveform
                Auto                        :   0
                Software/HVI                :   1
                Software/HVI (per cycle)    :   5
                External trigger            :   2
                External trigger (per cycle):   6
            start_delay: defines the delay between trigger and wf launch
                given in multiples of 10ns.
            cycles: number of times the waveform is repeated once launched
                zero = infinite repeats
            prescaler: waveform prescaler value, to reduce eff. sampling rate
            waveform_type: waveform type
            waveform_data_a: array with waveform points
            waveform_data_b: array with waveform points, only for the waveforms
                                        which have a second component

        Returns:
            available onboard RAM in waveform points, or negative numbers for
                errors
        """
        return super().awg_from_array(awg_number, trigger_mode, start_delay, cycles, prescaler,
                                      waveform_type, waveform_data_a,waveform_data_b, padding_mode, verbose)

    def awg_flush(self, awg_number: int) -> None:
        """
        Empties the queue of the selected AWG.
        Waveforms are not removed from the onboard RAM.
        """
        super().awg_flush(awg_number)
        if self._asynchronous:
            self._release_waverefs_awg(awg_number)

    @threaded(wait=True)
    def uploader_ready(self) -> bool:
        """ Waits until uploader thread is ready with tasks queued before this call. """
        return True

    def awg_queue_waveform(self, awg_number: int,
                           waveform_ref: Union[int, _WaveformReferenceInternal],
                           trigger_mode: int, start_delay: int, cycles: int,
                           prescaler: int) -> None:
        """
        Enqueus the waveform.

        Args:
            awg_number: awg number (channel) where the waveform is queued
            waveform_ref: reference to a waveform
            trigger_mode: trigger method to launch the waveform
                Auto                        :   0
                Software/HVI                :   1
                Software/HVI (per cycle)    :   5
                External trigger            :   2
                External trigger (per cycle):   6
            start_delay: defines the delay between trigger and wf launch
                given in multiples of 10ns.
            cycles (int): number of times the waveform is repeated once launched
                zero = infinite repeats
            prescaler: waveform prescaler value, to reduce eff. sampling rate
        """
        if self.asynchronous():
            waveform_ref = cast(_WaveformReferenceInternal, waveform_ref)
            if waveform_ref.awg_name != self.name:
                raise Exception(f'Waveform not uploaded to this AWG ({self.name}). '
                                f'It is uploaded to {waveform_ref.awg_name}')

            self.log.debug(f'Enqueue {waveform_ref.wave_number}')
            if not waveform_ref.is_uploaded():
                start = time.perf_counter()
                self.log.debug(f'Waiting till wave {waveform_ref.wave_number} is uploaded')
                waveform_ref.wait_uploaded()
                duration = time.perf_counter() - start
                self.log.info(f'Waited {duration*1000:5.1f} ms for upload of wave {waveform_ref.wave_number}')

            waveform_ref.enqueued()
            self._enqueued_waverefs[awg_number].append(waveform_ref)
            wave_number = waveform_ref.wave_number
        else:
            wave_number = cast(int, waveform_ref)

        super().awg_queue_waveform(awg_number, wave_number, trigger_mode, start_delay, cycles, prescaler)


    @switchable(asynchronous, enabled=True)
    def set_waveform_limit(self, requested_waveform_size_limit: int) -> None:
        """
        Increases the maximum size of waveforms that can be uploaded.

        Additional memory will be reserved in the AWG.
        Limit can not be reduced, because reservation cannot be undone.

        Args:
            requested_waveform_size_limit: maximum size of waveform that can be uploaded
        """
        self._memory_manager.set_waveform_limit(requested_waveform_size_limit)
        self._init_awg_memory()


    @switchable(asynchronous, enabled=True)
    def upload_waveform(self, wave: Union[List[float], List[int], np.ndarray]
                        ) -> _WaveformReferenceInternal:
        """
        Upload the wave using the uploader thread for this AWG.
        Args:
            wave: wave data to upload.
        Returns:
            reference to the wave
        """
        if len(wave) < 2000:
            raise Exception(f'{len(wave)} is less than 2000 samples required for proper functioning of AWG')

        allocated_slot = self._memory_manager.allocate(len(wave))
        ref = _WaveformReferenceInternal(allocated_slot, self.name)
        self.log.debug(f'upload: {ref.wave_number}')
        self._upload(wave, ref)
        return ref


    def close(self) -> None:
        """
        Closes the module and stops background thread.
        """
        self.log.info(f'stopping ({self.module_id})')
        if self.asynchronous():
            self._stop_asynchronous()

        del SD_AWG_Async._modules[self.module_id]

        super().close()


    def _get_module_id(self) -> str:
        """
        Generates a unique name for this module.
        """
        return f'{self.module_name}:{self.chassis_number()}-{self.slot_number()}'


    def _start_asynchronous(self) -> None:
        """
        Starts the asynchronous upload thread and memory manager.
        """
        super().flush_waveform()
        self._memory_manager: MemoryManager = MemoryManager(self.log, self._waveform_size_limit)
        self._enqueued_waverefs:Dict[int, List[_WaveformReferenceInternal]] = {}
        for i in range(self.channels):
            self._enqueued_waverefs[i+1] = []

        self._task_queue: queue.Queue = queue.Queue()
        self._init_awg_memory()
        self._thread: threading.Thread = threading.Thread(target=self._run, name=f'uploader-{self.module_id}')
        self._thread.start()


    def _stop_asynchronous(self) -> None:
        """
        Stops the asynchronous upload thread and memory manager.
        """
        if self._task_queue:
            self._task_queue.put('STOP')

        # wait at most 15 seconds. Should be more enough for normal scenarios
        self._thread.join(15)
        if self._thread.is_alive():
            self.log.error(f'AWG upload thread {self.module_id} stop failed. Thread still running.')

        self._release_waverefs()
        del self._memory_manager
        del self._task_queue
        del self._thread


    def _release_waverefs(self) -> None:
        for i in range(self.channels):
            self._release_waverefs_awg(i + 1)


    def _release_waverefs_awg(self, awg_number: int) -> None:
        for waveref in self._enqueued_waverefs[awg_number]:
            waveref.dequeued()
        self._enqueued_waverefs[awg_number] = []


    @threaded()
    def _init_awg_memory(self) -> None:
        """
        Initialize memory on the AWG by uploading waveforms with all zeros.
        """
        new_slots = self._memory_manager.get_uninitialized_slots()
        if len(new_slots) == 0:
            return

        self.log.info(f'Reserving awg memory for {len(new_slots)} slots')

        zeros: np.ndarray = np.zeros(0)
        wave = None
        total_size = 0
        total_duration = 0.0
        for slot in new_slots:
            start = time.perf_counter()
            if len(zeros) != slot.size or wave is None:
                zeros = np.zeros(slot.size, float)
                wave = keysightSD1.SD_Wave()
                result_parser(wave.newFromArrayDouble(keysightSD1.SD_WaveformTypes.WAVE_ANALOG, zeros))
            super().load_waveform(wave, slot.number)
            duration = time.perf_counter() - start
            # self.log.debug(f'uploaded {slot.size} in  {duration*1000:5.2f} ms ({slot.size/duration/1e6:5.2f} MSa/s)')
            total_duration += duration
            total_size += slot.size

        self.log.info(f'Awg memory reserved: {len(new_slots)} slots, {total_size/1e6} MSa in '
                      f'{total_duration*1000:5.2f} ms ({total_size/total_duration/1e6:5.2f} MSa/s)')

    @threaded()
    def _upload(self,
                wave_data: Union[List[float], List[int], np.ndarray],
                wave_ref: _WaveformReferenceInternal) -> None:
        # self.log.debug(f'Uploading {wave_ref.wave_number}')
        try:
            start = time.perf_counter()

            wave = keysightSD1.SD_Wave()
            result_parser(wave.newFromArrayDouble(keysightSD1.SD_WaveformTypes.WAVE_ANALOG, wave_data))
            super().reload_waveform(wave, wave_ref.wave_number)

            duration = time.perf_counter() - start
            speed = len(wave_data)/duration
            self.log.debug(f'Uploaded {wave_ref.wave_number} in {duration*1000:5.2f} ms ({speed/1e6:5.2f} MSa/s)')
        except Exception as ex:
            msg = f'{type(ex).__name__}:{ex}'
            min_value = np.min(wave_data)
            max_value = np.max(wave_data)
            if min_value < -1.0 or max_value > 1.0:
                msg += ': Voltage out of range'
            self.log.error(f'Failure load waveform {wave_ref.wave_number}: {msg}' )
            wave_ref._upload_error = msg

        # signal upload done, either successful or with error
        wave_ref._uploaded.set()


    def _run(self) -> None:
        self.log.info('Uploader ready')

        while True:
            task: Task = self._task_queue.get()
            if task == 'STOP':
                break
            try:
                task.run()
            except:
                logging.error('Task thread error', exc_info=True)
            del task

        self.log.info('Uploader terminated')
