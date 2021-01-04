'''
Test AWG memory manager:
* default initialization
* allocate / release
'''
from qcodes_contrib_drivers.drivers.Keysight.SD_common.memory_manager import MemoryManager

import unittest
import logging

SMALL_SIZE = 5_000
MEDIUM_SIZE = 50_000
LARGE_SIZE = 500_000
VERY_LARGE_SIZE = 10_000_000
EXTREMELY_LARGE_SIZE = 100_000_000

N_SMALL = 400
N_MEDIUM = 100
N_LARGE = 20
N_VERY_LARGE = 8
N_EXTREMELY_LARGE = 4


class TestMemoryManager(unittest.TestCase):

    def test_allocate_release(self):
        mm = MemoryManager(logging)

        # cycle through slots
        for i in range(1001):
            allocated_slot = mm.allocate(LARGE_SIZE)
            allocated_slot.release()

        # allocate all large slots
        slots = [mm.allocate(LARGE_SIZE) for i in range(N_LARGE)]

        with self.assertRaises(Exception):
            # no more slots available
            allocated_slot = mm.allocate(LARGE_SIZE)

        for allocated_slot in slots:
            allocated_slot.release()


    def test_allocate_big(self):
        mm = MemoryManager(logging)

        with self.assertRaises(Exception):
            allocated_slot = mm.allocate(VERY_LARGE_SIZE)

        mm.set_waveform_limit(VERY_LARGE_SIZE)
        allocated_slot = mm.allocate(VERY_LARGE_SIZE)
        allocated_slot.release()

        with self.assertRaises(Exception):
            allocated_slot = mm.allocate(EXTREMELY_LARGE_SIZE)

        mm.set_waveform_limit(EXTREMELY_LARGE_SIZE)
        allocated_slot = mm.allocate(EXTREMELY_LARGE_SIZE)
        allocated_slot.release()


    def test_allocate_all_small(self):
        mm = MemoryManager(logging)

        # allocate all slots by requesting small sizes
        slots = [mm.allocate(SMALL_SIZE) for i in range(N_SMALL + N_MEDIUM + N_LARGE)]

        with self.assertRaises(Exception):
            # no more slots available
            allocated_slot = mm.allocate(SMALL_SIZE)

        for allocated_slot in slots:
            allocated_slot.release()


    def test_uninitialized(self):
        mm = MemoryManager(logging, SMALL_SIZE)

        new_slots = mm.get_uninitialized_slots()
        self.assertEqual(len(new_slots), N_SMALL)

        mm.set_waveform_limit(LARGE_SIZE)
        new_slots = mm.get_uninitialized_slots()
        self.assertEqual(len(new_slots), N_MEDIUM + N_LARGE)

        new_slots = mm.get_uninitialized_slots()
        self.assertEqual(len(new_slots), 0)

        mm.set_waveform_limit(LARGE_SIZE)
        new_slots = mm.get_uninitialized_slots()
        self.assertEqual(len(new_slots), 0)

        mm.set_waveform_limit(VERY_LARGE_SIZE)
        new_slots = mm.get_uninitialized_slots()
        self.assertEqual(len(new_slots), N_VERY_LARGE)
