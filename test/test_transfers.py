#
# This file is part of Facedancer.
#

import asyncio, logging, random, sys, time
import unittest
import usb1

from .base   import FacedancerTestCase
from .base   import VENDOR_ID, PRODUCT_ID, MAX_TRANSFER_LENGTH, OUT_ENDPOINT, IN_ENDPOINT
from .device import generate_data


# Transfer length for tests
def test_transfer_length():
    return random.randrange(1, MAX_TRANSFER_LENGTH)


# Run tests in random order
#
# Note: if you can't reproduce a failed run check the order of the
#       tests in the failed run!
unittest.TestLoader.sortTestMethodsUsing = lambda self, a, b: random.choice([1, 0, -1])


class TestTransfers(FacedancerTestCase):
    """Transfer tests for test device"""

    # - life-cycle ------------------------------------------------------------

    def setUp(self):
        # select first interface
        self.set_interface(0, 0)

        # reset test device state between tests
        self.reset_device_state()


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

    def test_bulk_out_transfer(self):
        # generate test data
        length = test_transfer_length()
        data = generate_data(length)

        # perform Bulk OUT transfer
        bytes_sent = self.bulk_out_transfer(OUT_ENDPOINT, data)

        # check transfer
        self.check_out_transfer(length, data, bytes_sent)


    def test_bulk_in_transfer(self):
        # set desired IN transfer length
        length = test_transfer_length()
        self.set_in_transfer_length(length)

        # perform Bulk IN transfer
        received_data = self.bulk_in_transfer(IN_ENDPOINT, length)

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
    unittest.main(verbosity=1)
