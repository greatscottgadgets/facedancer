# USBKeyboard.py
#
# Contains class definitions to implement a USB keyboard.

import greatfet
import random

from facedancer.usb.USB import *
from facedancer.usb.USBDevice import *
from facedancer.usb.USBConfiguration import *
from facedancer.usb.USBInterface import *
from facedancer.usb.USBEndpoint import *

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

    def __init__(self, phy):

        _descriptors = {
                DescriptorType.hid    : self.hid_descriptor,
                DescriptorType.report : self.report_descriptor
        }

        self.out_endpoint = USBEndpoint(
            phy=phy,
            number=2,  # endpoint number
            direction=USBEndpoint.direction_out,
            transfer_type=USBEndpoint.transfer_type_interrupt,
            sync_type=USBEndpoint.sync_type_none,
            usage_type=USBEndpoint.usage_type_data,
            max_packet_size=64,  # max packet size
            interval=0x05,  # polling interval, see USB 2.0 spec Table 9-13
            handler=self.handle_out_data  # handler function
        )

        self.endpoint = USBEndpoint(
            phy=phy,
            number=1,  # endpoint number
            direction=USBEndpoint.direction_in,
            transfer_type=USBEndpoint.transfer_type_interrupt,
            sync_type=USBEndpoint.sync_type_none,
            usage_type=USBEndpoint.usage_type_data,
            max_packet_size=64,  # max packet size
            interval=0x05,  # polling interval, see USB 2.0 spec Table 9-13
            handler=self.handle_buffer_available  # handler function
        )

        # TODO: un-hardcode string index
        super(USBSwitchTASInterface, self).__init__(
                phy=phy,
                interface_number=0,          # interface number
                interface_alternate=0,          # alternate setting
                interface_class=3,       # interface class: vendor-specific
                interface_subclass=0,       # subclass: vendor-specific
                interface_protocol=0,       # protocol: vendor-specific
                interface_string_index=0,          # string index
                endpoints=[ self.out_endpoint, self.endpoint ],
                descriptors=_descriptors,
                usb_class=HIDClass(phy)
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
    name = "Switch TAS device"


    def __init__(self, phy):
        interface0 = USBSwitchTASInterface(phy)

        config = USBConfiguration(
                phy=phy,
                configuration_index=1,                                          # index
                configuration_string_or_index=None,                                       # string desc
                interfaces=[ interface0 ],                 # interfaces
                attributes=0x80, # attributes
                max_power=250 # power
        )

        super(USBSwitchTASDevice, self).__init__(
                phy=phy,
                device_class=USBClass.Unspecified,                      # device class
                device_subclass=0,                      # device subclass
                protocol_rel_num=0,                      # protocol release number
                max_packet_size_ep0=64,                     # max packet size for endpoint 0
                vendor_id=0x0f0d,                 # vendor id
                product_id=0x00c1,                 # product id
                device_rev=0x0572,                 # device revision
                manufacturer_string="HORI CO.,LTD.",                # manufacturer string
                product_string="HORIPAD S",               # product string
                serial_number_string="",   # serial number string
                configurations=[config]
        )