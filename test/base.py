#
# This file is part of FaceDancer.
#

import logging
import unittest
import usb1

from facedancer.errors import DeviceNotFoundError


VENDOR_ID  = 0x1209
PRODUCT_ID = 0x0001

OUT_ENDPOINT = 0x01
IN_ENDPOINT  = 0x82

# This is constrained by pygreat::comms_backends::usb1::LIBGREAT_MAX_COMMAND_SIZE
# and is board dependent.
MAX_TRANSFER_LENGTH = 768


class FacedancerTestCase(unittest.TestCase):

    # - life-cycle ------------------------------------------------------------

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.INFO)
        cls.context = usb1.USBContext().open()
        cls.device_handle = cls.context.openByVendorIDAndProductID(VENDOR_ID, PRODUCT_ID)
        if cls.device_handle is None:
            raise Exception("device not found")
        cls.device_handle.claimInterface(0)


    @classmethod
    def tearDownClass(cls):
        cls.context.close()



    # - transfers -------------------------------------------------------------

    def bulk_out_transfer(self, data):
        logging.debug("Testing bulk OUT endpoint")
        response = self.device_handle.bulkWrite(
            endpoint = 0x01,
            data     = data,
            timeout  = 1000,
        )
        logging.debug(f"sent {response} bytes\n")
        return response

    def bulk_in_transfer(self, length):
        logging.debug("Testing bulk IN endpoint")
        response = self.device_handle.bulkRead(
            endpoint = 0x82,
            length   = length,
            timeout  = 1000,
        )
        logging.debug(f"[host] received '{len(response)}' bytes from bulk endpoint")
        return response

    def control_out_transfer(self, data):
        logging.debug("Testing OUT control transfer")
        hi, lo = len(data).to_bytes(2, byteorder="big")
        response = self.device_handle.controlWrite(
            request_type = usb1.TYPE_VENDOR | usb1.RECIPIENT_DEVICE,
            request      = 10,
            index        = hi,
            value        = lo,
            data         = data,
            timeout      = 1000,
        )
        logging.debug(f"sent {response} bytes\n")
        return response

    def control_in_transfer(self, length):
        logging.debug("Testing IN control transfer")
        hi, lo = length.to_bytes(2, byteorder="big")
        response = self.device_handle.controlRead(
            request_type = usb1.TYPE_VENDOR | usb1.RECIPIENT_DEVICE,
            request      = 20,
            index        = hi,
            value        = lo,
            length       = length,
            timeout      = 1000,
        )
        logging.debug(f"[host] received '{len(response)}' bytes from control endpoint")
        return response

    # - device control ------------------------------------------------------------

    def set_in_transfer_length(self, length):
        hi, lo = length.to_bytes(2, byteorder="big")
        logging.debug(f"Setting transfer length to {length} bytes")
        response = self.device_handle.controlWrite(
            request_type = usb1.TYPE_VENDOR | usb1.RECIPIENT_DEVICE,
            request      = 1,
            index        = hi,
            value        = lo,
            data         = [],
            timeout      = 1000,
        )
        return response

    def get_last_out_transfer_data(self):
        logging.debug("Getting last OUT transfer data")
        response = self.device_handle.controlRead(
            request_type = usb1.TYPE_VENDOR | usb1.RECIPIENT_DEVICE,
            request      = 2,
            index        = 0,
            value        = 0,
            length       = MAX_TRANSFER_LENGTH,
            timeout      = 1000,
        )
        logging.debug(f"[host] sent '{len(response)}' bytes with last out transfer")
        return response

    def reset_device_state(self):
        logging.debug(f"Resetting stress test device state")
        response = self.device_handle.controlWrite(
            request_type = usb1.TYPE_VENDOR | usb1.RECIPIENT_DEVICE,
            request      = 3,
            index        = 0,
            value        = 0,
            data         = [],
            timeout      = 1000,
        )
        return response
