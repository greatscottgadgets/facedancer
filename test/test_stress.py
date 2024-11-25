#
# This file is part of Facedancer.
#

import asyncio, logging, random, sys, time
import unittest
import usb1

from .base   import FacedancerTestCase
from .base   import VENDOR_ID, PRODUCT_ID, MAX_TRANSFER_LENGTH, OUT_ENDPOINT, IN_ENDPOINT
from .device import generate_data

# How many iterations to run for stress test
ITERATIONS = 100

# Transfer length for tests
def test_transfer_length():
    return random.randrange(1, MAX_TRANSFER_LENGTH)


class TestStress(FacedancerTestCase):
    """Stress tests for test device"""

    # - life-cycle ------------------------------------------------------------

    def setUp(self):
        # select first interface
        self.set_interface(0, 0)

        # reset test device state between tests
        self.reset_device_state()

    def test_stress_test(self):
        def bulk_out_transfer(self, length):
            bytes_sent = self.bulk_out_transfer(OUT_ENDPOINT, generate_data(length))
            self.assertEqual(bytes_sent, length)
        def bulk_in_transfer(self, length):
            received = self.bulk_in_transfer(IN_ENDPOINT, length)
            self.assertEqual(len(received), length)
        def control_out_transfer(self, length):
            bytes_sent = self.control_out_transfer(generate_data(length))
            self.assertEqual(bytes_sent, length)
        def control_in_transfer(self, length):
            received = self.control_in_transfer(length)
            self.assertEqual(len(received), length)

        available_tests = [
            bulk_out_transfer,
            bulk_in_transfer,
            control_out_transfer,
            control_in_transfer,
        ]
        tests = [random.choice(available_tests) for _ in range(ITERATIONS)]

        # pick a random length for transfers
        transfer_length = test_transfer_length()
        self.set_in_transfer_length(transfer_length)

        logging.debug(f"Running stress test with a transfer length of {transfer_length} bytes")
        failures = 0
        for index, test in enumerate(tests):
            logging.debug(f"#{index}: {test.__name__}")
            try:
                test(self, transfer_length)
            except Exception as e:
                failures += 1
                logging.error(f"Failed #{index}: {test.__name__} {e}")

        if failures > 0:
            logging.error(f"Failed {failures} tests.")
            raise RuntimeError(f"Failed {failures} tests.")


def highly_stressed_edition():
    from .test_transfers import TestTransfers

    available_tests = [
        "test_bulk_out_transfer",
        "test_bulk_in_transfer",
        "test_control_out_transfer",
        "test_control_in_transfer",
    ]
    tests = [random.choice(available_tests) for _ in range(ITERATIONS)]

    suite = unittest.TestSuite()
    for test in tests:
        suite.addTest(TestTransfers(test))

    runner = unittest.TextTestRunner()
    runner.run(suite)


if __name__ == "__main__":
    #highly_stressed_edition()
    unittest.main(verbosity=1)
