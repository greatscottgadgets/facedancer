#
# This file is part of FaceDancer.
#

import asyncio, logging, random, sys, time
import unittest
import usb1

#sys.path.append(".")
from base import FacedancerTestCase
from stress_test_device import generate_data, VENDOR_ID, PRODUCT_ID


# This is governed by pygreat::comms_backends::usb1::LIBGREAT_MAX_COMMAND_SIZE
MAX_TRANSFER_LENGTH = 768

# How many consecutive transfers to execute for stress tests
ITERATIONS = 100

# Transfer length for tests
def test_transfer_length():
    return random.randrange(1, MAX_TRANSFER_LENGTH)

# Run tests in random order
#
# Note: if you can't reproduce a failed run check the order of the
#       tests in the failed run!
unittest.TestLoader.sortTestMethodsUsing = lambda self, a, b: random.choice([1, 0, -1])


class TestStressTestDevice(FacedancerTestCase):
    """Tests for stress test device"""

    # - transfer checks -------------------------------------------------------

    def check_out_transfer(self, length, sent_data, bytes_sent):
        # request a copy of the received data to compare against
        received_data = self.get_last_out_transfer_data()

        # did we send the right amount of data?
        self.assertEqual(bytes_sent, length)

        # does the length of the sent data match the length of the received data?
        self.assertEqual(len(sent_data), len(received_data))

        # does the content of the sent data match the content of the received data?
        self.assertEqual(sent_data, received_data)


    def check_in_transfer(self, length, received_data):
        # generate a set of data to compare against
        compare_data = generate_data(length)

        # did we receive the right amount of data?
        self.assertEqual(len(received_data), length)

        # does the content of the received data match the content of our comparison data?
        self.assertEqual(received_data, compare_data)


    # - tests -----------------------------------------------------------------

    def test_stress_unchecked(self):
        def bulk_out_transfer(self, length):
            self.bulk_out_transfer(generate_data(length))
        def bulk_in_transfer(self, length):
            self.bulk_in_transfer(length)
        def control_out_transfer(self, length):
            self.control_out_transfer(generate_data(length))
        def control_in_transfer(self, length):
            self.control_in_transfer(length)

        available_tests = [
            bulk_out_transfer,
            bulk_in_transfer,
            control_out_transfer,
            control_in_transfer,
        ]

        tests = [random.choice(available_tests) for _ in range(ITERATIONS)]
        logging.info(f"Running tests: %s" % ", ".join([test.__name__ for test in tests]))
        failures = 0
        for index, test in enumerate(tests):
            length = test_transfer_length()
            logging.info(f"#{index}: {test.__name__} length: {length} ")
            try:
                test(self, length)
            except Exception as e:
                failures += 1
                logging.error(f"Failed #{index}: {test.__name__} {e}")

        if failures > 0:
            raise RuntimeError(f"Failed {failures} tests.")

    def test_stress_checked(self):
        available_tests = [
            TestStressTestDevice.test_bulk_out_transfer,
            TestStressTestDevice.test_bulk_in_transfer,
            TestStressTestDevice.test_control_out_transfer,
            TestStressTestDevice.test_control_in_transfer,
        ]
        tests = [random.choice(available_tests) for _ in range(ITERATIONS)]
        logging.error(f"Running tests: %s" % ", ".join([test.__name__ for test in tests]))
        for index, test in enumerate(tests):
            logging.info(f"#{index}: {test.__name__}")
            try:
                test(self)
            except Exception as e:
                logging.error(f"Failed #{index}: {test.__name__} {e}")
                raise e


    def test_bulk_out_transfer(self):
        # generate test data
        length = test_transfer_length()
        data = generate_data(length)

        # perform Bulk OUT transfer
        bytes_sent = self.bulk_out_transfer(data)

        # check transfer
        self.check_out_transfer(length, data, bytes_sent)


    def test_bulk_in_transfer(self):
        # set desired IN transfer length
        length = test_transfer_length()
        self.set_in_transfer_length(length)

        # perform Bulk IN transfer
        received_data = self.bulk_in_transfer(length)

        # check transfer
        self.check_in_transfer(length, received_data)


    def test_control_out_transfer(self):
        # generate test data
        length = test_transfer_length()
        data = generate_data(length)

        # perform Control OUT transfer
        bytes_sent = self.control_out_transfer(data)

        # check transfer
        self.check_out_transfer(length, data, bytes_sent)


    def test_control_in_transfer(self):
        # set desired IN transfer length
        length = test_transfer_length()
        self.set_in_transfer_length(length)

        # perform Bulk IN transfer
        received_data = self.control_in_transfer(length)

        # check transfer
        self.check_in_transfer(length, received_data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
