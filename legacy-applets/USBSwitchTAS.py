# USBKeyboard.py
#
# Contains class definitions to implement a USB keyboard.

import greatfet
import random

from facedancer.USB import *
from facedancer.USBDevice import *
from facedancer.USBConfiguration import *
from facedancer.USBInterface import *
from facedancer.USBEndpoint import *

class USBSwitchTASInterface(USBInterface):
    name = "Switch TAS Interface"

    input = [b'\x00\x00\x0f\x80\x80\x80\x80\x00',
    b'\x00\x00\x0f\x80\x80\x80\x80\x00',
    b'\x00\x00\x0f\x80\x80\x80\x80\x00',
    b'\x00\x00\x0f\x80\x80\x80\x80\x00',
    b'\x00\x00\x0f\x80\x80\x80\x80\x00',
    b'\x00\x00\x0f\x80\x80\x80\x80\x00',
    b'\x00\x00\x0f\x80\x80\x80\x80\x00',
    b'\x00\x00\x0f\x80\x80\x80\x80\x00']

    # copied from the horipad
    hid_descriptor = b'\x09\x21\x11\x01\x00\x01\x22\x50\x00'
    report_descriptor = b'\x05\x01\t\x05\xa1\x01\x15\x00%\x015\x00E\x01u\x01\x95\x0e\x05\t\x19\x01)\x0e\x81\x02\x95\x02\x81\x01\x05\x01%\x07F;\x01u\x04\x95\x01e\x14\t9\x81Be\x00\x95\x01\x81\x01&\xff\x00F\xff\x00\t0\t1\t2\t5u\x08\x95\x04\x81\x02u\x08\x95\x01\x81\x01\xc0'

    def __init__(self, verbose=0):
        descriptors = { 
                USB.desc_type_hid    : self.hid_descriptor,
                USB.desc_type_report : self.report_descriptor
        }

        self.out_endpoint = USBEndpoint(
                2,          # endpoint number
                USBEndpoint.direction_out,
                USBEndpoint.transfer_type_interrupt,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                64,       # max packet size
                5,         # polling interval, see USB 2.0 spec Table 9-13
                self.handle_out_data    # handler function
        )

        self.endpoint = USBEndpoint(
                1,          # endpoint number
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_interrupt,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                64,       # max packet size
                5,         # polling interval, see USB 2.0 spec Table 9-13
                self.handle_buffer_available    # handler function
        )

        # TODO: un-hardcode string index (last arg before "verbose")
        USBInterface.__init__(
                self,
                0,          # interface number
                0,          # alternate setting
                3,          # interface class
                0,          # subclass
                0,          # protocol
                0,          # string index
                verbose,
                [ self.out_endpoint, self.endpoint ],
                descriptors
        )

        self.packets_to_send = self.input


    def handle_buffer_available(self):
        # two bytes buttons
        # hat switch
        # four joysticks
        # one byte padding
        #random_dir_raw = random.randint(0, 255)
        #random_dir = random_dir_raw.to_bytes(1, byteorder='little')

        if self.packets_to_send:
            to_send = self.packets_to_send.pop(0)
            self.endpoint.send(to_send)

        #self.endpoint.send(b'\x00\x00\x0f' + random_dir + b'\x80\x80\x80\x00')



    def handle_out_data(self, data):
        print("??? Got out data! {}".format(data))


class USBSwitchTASDevice(USBDevice):
    name = "USB keyboard device"

    def __init__(self, maxusb_app, verbose=0):
        config = USBConfiguration(
                1,                                          # index
                None,                                       # string desc
                [ USBSwitchTASInterface() ],                 # interfaces
                0x80, # attributes
                250 # power
        )

        USBDevice.__init__(
                self,
                maxusb_app,
                0,                      # device class
                0,                      # device subclass
                0,                      # protocol release number
                64,                     # max packet size for endpoint 0
                0x0f0d,                 # vendor id
                0x00c1,                 # product id
                0x0572,                 # device revision
                "HORI CO.,LTD.",        # manufacturer string
                "HORIPAD S",            # product string
                None,                   # serial number string
                [ config ],
                verbose=verbose
        )

