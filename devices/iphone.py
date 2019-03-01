# iPhone.py
#
# Contains class definitions to implement an Apple iPhone.

from facedancer.usb.USB import *
from facedancer.usb.USBDevice import *
from facedancer.usb.USBConfiguration import *
from facedancer.usb.USBInterface import *
from facedancer.usb.USBEndpoint import *
from facedancer.usb.USBVendor import *
from facedancer.fuzz.helpers import mutable

class USBiPhoneVendor(USBVendor):

    def setup_local_handlers(self):
        self.local_handlers = {
            0x40: self.handle_40_request,
            0x45: self.handle_45_request
        }

    @mutable('iphone_handle_40_response')
    def handle_40_request(self, req):
        self.verbose("received handle_40 request")
        return b''

    @mutable('iphone_handle_45_response')
    def handle_45_request(self, req):
        self.verbose("received handle_45 request")
        return b'\x03'

class USBiPhoneClass(USBClass):

    #def __init__(self, phy):
    #   super(USBiPhoneClass, self).__init__(phy)

    def setup_local_handlers(self):
        self.local_handlers = {
            0x20: self.handle_set_line_coding,
            0x22: self.handle_set_control_line_state
        }
        
    @mutable('iphone_set_control_line_state', silent=True)
    def handle_set_control_line_state(self, req):
        return b''

    @mutable('iphone_set_line_coding', silent=True)
    def handle_set_line_coding(self, req):
        return b''

        
class USBiPhoneInterface(USBInterface):
    name = "USB iPhone interface"

    def __init__(self, phy, interface_number, usbclass, sub, proto):
        endpoints0 = [
            USBEndpoint(
                phy=phy,
                number=2,          # endpoint number
                direction=USBEndpoint.direction_out,
                transfer_type=USBEndpoint.transfer_type_bulk,
                sync_type=USBEndpoint.sync_type_none,
                usage_type=USBEndpoint.usage_type_data,
                max_packet_size=0x200,      # max packet size
                interval=0x0a,       # polling interval, see USB 2.0 spec Table 9-13
                handler=self.handle_data_available      # handler function
            ),
            USBEndpoint(
                phy=phy,
                number=1,          # endpoint number
                direction=USBEndpoint.direction_in,
                transfer_type=USBEndpoint.transfer_type_bulk,
                sync_type=USBEndpoint.sync_type_none,
                usage_type=USBEndpoint.usage_type_data,
                max_packet_size=0x200,      # max packet size
                interval=0x0a,       # polling interval, see USB 2.0 spec Table 9-13
                handler=self.handle_buffer_available        # handler function
            ),
            USBEndpoint(
                phy=phy,
                number=3,          # endpoint number
                direction=USBEndpoint.direction_in,
                transfer_type=USBEndpoint.transfer_type_bulk,
                sync_type=USBEndpoint.sync_type_none,
                usage_type=USBEndpoint.usage_type_data,
                max_packet_size=64,         # max packet size
                interval=0,          # polling interval, see USB 2.0 spec Table 9-13
                handler=self.handle_buffer_available        # handler function
            )
        ]
        
        endpoints1 = [
            USBEndpoint(
                phy=phy,
                number=4,          # endpoint number
                direction=USBEndpoint.direction_out,
                transfer_type=USBEndpoint.transfer_type_bulk,
                sync_type=USBEndpoint.sync_type_none,
                usage_type=USBEndpoint.usage_type_data,
                max_packet_size=0x200,      # max packet size
		        interval=0x00,       # polling interval, see USB 2.0 spec Table 9-13
                handler=self.handle_data_available      # handler function
            ),
            USBEndpoint(
                phy=phy,
                number=5,          # endpoint number
                direction=USBEndpoint.direction_in,
                transfer_type=USBEndpoint.transfer_type_bulk,
                sync_type=USBEndpoint.sync_type_none,
                usage_type=USBEndpoint.usage_type_data,
                max_packet_size=0x200,         # max packet size
                interval=0x00,          # polling interval, see USB 2.0 spec Table 9-13
                handler=self.handle_buffer_available        # handler function
            )
        ]
        
        endpoints2 = []
        
        if interface_number== 0:
            endpoints = endpoints0
        elif interface_number == 1:
            endpoints = endpoints1
        else:
            endpoints = endpoints2

        # TODO: un-hardcode string index
        super(USBiPhoneInterface, self).__init__(
                phy=phy,
                interface_number=interface_number,          # interface number
                interface_alternate=0,          # alternate setting
                interface_class=usbclass,       # interface class: vendor-specific
                interface_subclass=sub,       # subclass: vendor-specific
                interface_protocol=proto,       # protocol: vendor-specific
                interface_string_index=0,          # string index
                endpoints=endpoints,
                usb_class=USBiPhoneClass(phy)
        )
        
    def handle_data_available(self, data):
        self.verbose("received data (length: %d)", len(data))

    def handle_buffer_available(self):
        self.verbose("ready to send")
        
class USBiPhoneDevice(USBDevice):
    name = "USB iPhone device"

    def __init__(self, phy, vid=0x05ac, pid=0x12a8, rev=0x0701, **kwargs):
        interface0 = USBiPhoneInterface(phy, 0, 0x06, 0x01, 0x01)
        interface1 = USBiPhoneInterface(phy, 1, 0xff, 0xfe, 0x02)
        interface2 = USBiPhoneInterface(phy, 2, 0xff, 0xfd, 0x01)
        
        config = [
            USBConfiguration(
                phy=phy,
                configuration_index=1,                                          # index
                configuration_string_or_index="iPhone",                                     # string desc
                interfaces=[ interface0, interface1, interface2 ]                               # interfaces
            ),
            USBConfiguration(
                phy=phy,
                configuration_index=2,                                          # index
                configuration_string_or_index="iPhone",                                     # string desc
                interfaces=[ interface0, interface1, interface2 ]                               # interfaces
            ),
            USBConfiguration(
                phy=phy,
                configuration_index=3,                                          # index
                configuration_string_or_index="iPhone",                                     # string desc
                interfaces=[ interface0, interface1, interface2 ]                               # interfaces
            ),
            USBConfiguration(
                phy=phy,
                configuration_index=4,                                          # index
                configuration_string_or_index="iPhone",                                     # string desc
                interfaces=[ interface0, interface1, interface2 ]                               # interfaces
            )
        ]

        super(USBiPhoneDevice, self).__init__(
                phy=phy,
                device_class=USBClass.Unspecified,                      # device class
                device_subclass=0,                      # device subclass
                protocol_rel_num=0,                      # protocol release number
                max_packet_size_ep0=64,                     # max packet size for endpoint 0
                vendor_id=vid,                 # vendor id
                product_id=pid,                 # product id
                device_rev=rev,                 # device revision
                manufacturer_string="Apple Inc.",                # manufacturer string
                product_string="iPhone",               # product string
                serial_number_string="85defb989b29c7ade64353eba48614ad7db7afd1",   # serial number string
                configurations=config,
                usb_vendor = USBiPhoneVendor(phy=phy)
        )

