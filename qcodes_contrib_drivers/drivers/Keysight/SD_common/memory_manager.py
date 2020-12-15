# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import List, Dict
import logging


class MemoryManager:
    """
    Memory manager for AWG memory.

    AWG memory is reserved in slots of sizes from 1e4 till 1e8 samples.
    Allocation of memory takes time. So, only request a high maximum waveform size when it is needed.

    Memory slots (number: size):
        400: 1e4 samples
        100: 1e5 samples
        20: 1e6 samples
        8: 1e7 samples
        4: 1e8 samples

    Args:
        waveform_size_limit: maximum waveform size to support.
    """

    @dataclass
    class AllocatedSlot:
        number: int
        allocation_ref: int
        memory_manager: 'MemoryManager'

        def release(self) -> None:
            self.memory_manager.release(self)

    @dataclass
    class _MemorySlot:
        number: int
        size: int
        allocated: bool
        initialized: bool
        allocation_ref: int
        '''Unique reference value when allocated.
        Used to check for incorrect or missing release calls.
        '''

    # Note (M3202A): size must be multiples of 10 and >= 2000
    memory_sizes = [
            (int(1e4), 400),
            (int(1e5), 100),
            (int(1e6), 20),
            (int(1e7), 8), # Uploading 8e7 samples takes 1.5s.
            (int(1e8), 4) # Uploading 4e8 samples takes 7.3s.
            ]

    def __init__(self, log, waveform_size_limit: int = int(1e6)) -> None:
        self._log = log
        self._allocation_ref_count: int = 0
        self._created_size: int = 0
        self._max_waveform_size: int = 0

        self._free_memory_slots: Dict[int, List[int]] = {}
        self._slots: List[MemoryManager._MemorySlot] = []
        self._slot_sizes = sorted([size for size, _ in
                                   MemoryManager.memory_sizes])

        self.set_waveform_limit(waveform_size_limit)

    def set_waveform_limit(self, waveform_size_limit: int) -> None:
        """
        Increases the maximum size of waveforms that can be uploaded.

        Additional memory will be reserved in the AWG.
        Limit can not be reduced, because reservation cannot be undone.

        Args:
            waveform_size_limit: maximum size of waveform that can be uploaded
        """
        if waveform_size_limit > max(self._slot_sizes):
            raise Exception(f'Requested waveform size {waveform_size_limit} '
                            f'is too big')

        self._max_waveform_size = waveform_size_limit
        self._create_memory_slots(waveform_size_limit)

    def get_uninitialized_slots(self) -> List[_MemorySlot]:
        """
        Returns list of slots that must be initialized (reserved in AWG)
        """
        new_slots = []

        slots = self._slots.copy()
        for slot in slots:
            if not slot.initialized:
                new_slots.append(slot)
                slot.initialized = True

        return new_slots

    def allocate(self, wave_size: int) -> AllocatedSlot:
        """
        Allocates a memory slot with at least the specified wave size.

        Args:
            wave_size: number of samples of the waveform
        Returns:
            allocated slot
        """
        if wave_size > self._max_waveform_size:
            raise Exception(f'AWG wave with {wave_size} samples is too long. '
                            f'Max size={self._max_waveform_size}. Increase '
                            f'waveform size limit with set_waveform_limit().')

        for slot_size in self._slot_sizes:
            if wave_size > slot_size:
                continue
            if slot_size > self._created_size:
                # slots of this size are not initialized.
                break
            if len(self._free_memory_slots[slot_size]) > 0:
                slot = self._free_memory_slots[slot_size].pop(0)
                self._allocation_ref_count += 1
                self._slots[slot].allocation_ref = self._allocation_ref_count
                self._slots[slot].allocated = True
                self._log.debug(f'Allocated slot {slot}')
                return MemoryManager.AllocatedSlot(slot, self._slots[slot].allocation_ref, self)

        raise Exception(f'No free memory slots left for waveform with'
                        f' {wave_size} samples.')

    def release(self, allocated_slot: AllocatedSlot) -> None:
        """
        Releases the `allocated_slot`.
        """
        slot_number = allocated_slot.number
        slot = self._slots[slot_number]

        if not slot.allocated:
            raise Exception(f'memory slot {slot_number} not in use')

        if slot.allocation_ref != allocated_slot.allocation_ref:
            raise Exception(f'memory slot {slot_number} allocation reference '
                            f'mismatch:{slot.allocation_ref} is not equal to '
                            f'{allocated_slot.allocation_ref}')

        slot.allocated = False
        slot.allocation_ref = 0
        self._free_memory_slots[slot.size].append(slot_number)

        try:
            self._log.debug(f'Released slot {slot_number}')
        except:
            # self._log throws exception when instrument has been closed.
            logging.debug(f'Released slot {slot_number}')

    def _create_memory_slots(self, max_size: int) -> None:

        creation_limit = self._get_slot_size(max_size)

        free_slots = self._free_memory_slots
        slots = self._slots

        for size, amount in sorted(MemoryManager.memory_sizes):
            if size > creation_limit:
                break
            if size <= self._created_size:
                continue

            free_slots[size] = []
            for i in range(amount):
                number = len(slots)
                free_slots[size].append(number)
                slots.append(MemoryManager._MemorySlot(number, size, False, False, 0))

        self._free_memory_slots = free_slots
        self._slots = slots
        self._created_size = creation_limit

    def _get_slot_size(self, size: int) -> int:
        for slot_size in self._slot_sizes:
            if slot_size >= size:
                return slot_size

        raise Exception(f'Requested waveform size {size} is too big')
