#
# This file is part of Facedancer.
#

import asyncio, logging, random, sys, time
import unittest
import usb1

from .base   import FacedancerTestCase
from .base   import VENDOR_ID, PRODUCT_ID, MAX_TRANSFER_LENGTH, OUT_ENDPOINT, IN_ENDPOINT, OUT_ALT_ENDPOINT, IN_ALT_ENDPOINT
from .device import generate_data


class TestAlternate(FacedancerTestCase):
    """Test alternate interface settings"""


    def setUp(self):
        # reset test device state between tests
        self.reset_device_state()


    def test_alternate_interfaces(self):
        endpoints = {
            0: (OUT_ENDPOINT, IN_ENDPOINT),
            1: (OUT_ALT_ENDPOINT, IN_ALT_ENDPOINT),
        }

        for alt in (0, 1):
            self.set_interface(0, alt)
            assert(self.get_interface(0) == alt)

            out_ep, in_ep = endpoints[alt]

            # generate test data
            length = 678
            data = generate_data(length)

            # set desired IN transfer length
            self.set_in_transfer_length(length)

            # perform Bulk IN transfer
            received_data = self.bulk_in_transfer(in_ep, length)

            # generate a set of data to compare against
            compare_data = generate_data(length)

            # did we receive the right amount of data?
            self.assertEqual(len(received_data), length)

            # does the content of the received data match the content of our comparison data?
            self.assertEqual(received_data, compare_data)

            # perform Bulk OUT transfer
            bytes_sent = self.bulk_out_transfer(out_ep, data)

            # request a copy of the received data to compare against
            received_data = self.get_last_out_transfer_data()

            # did we send the right amount of data?
            self.assertEqual(bytes_sent, length)

            # does the length of the sent data match the length of the received data?
            self.assertEqual(len(data), len(received_data))

            # does the content of the sent data match the content of the received data?
            self.assertEqual(data, received_data)


if __name__ == "__main__":
    unittest.main(verbosity=1)
