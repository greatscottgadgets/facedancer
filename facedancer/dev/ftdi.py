# USBFtdi.py
#
# Contains class definitions to implement a USB FTDI chip.

from facedancer.usb.USB import *
from facedancer.usb.USBDevice import *
from facedancer.usb.USBConfiguration import *
from facedancer.usb.USBInterface import *
from facedancer.usb.USBEndpoint import *
from facedancer.usb.USBVendor import *
from facedancer.fuzz.helpers import mutable

class USBFtdiVendor(USBVendor):
    name = "USB FTDI vendor"

    def __init__(self, phy):
        super(USBFtdiVendor, self).__init__(phy)
        self.latency_timer = 0x01
        self.data = 0x00
        self.baudrate = 0x00
        self.dtr = 0x00
        self.flow_control = 0x00
        self.rts = 0x00
        self.dtren = 0x00
        self.rtsen = 0x00 
        
    def setup_local_handlers(self):
        self.local_handlers = {
            0x00: self.handle_reset,
            0x01: self.handle_modem_ctrl,
            0x02: self.handle_set_flow_ctrl,
            0x03: self.handle_set_baud_rate_request,
            0x04: self.handle_set_data,
            0x05: self.handle_get_modem_status,
            0x06: self.handle_set_event_char,
            0x07: self.handle_set_error_char,
            0x09: self.handle_set_latency_timer,
            0x0a: self.handle_get_latency_timer,
            0x90: self.handle_read_ee,
        } 

    @mutable('ftdi_reset_response')
    def handle_reset(self, req):
        self.verbose("received reset request")
        return b''

    @mutable('ftdi_modem_ctrl_response')
    def handle_modem_ctrl(self, req):
        self.verbose("received modem_ctrl request")

        dtr = req.value & 0x0001
        rts = (req.value & 0x0002) >> 1
        dtren = (req.value & 0x0100) >> 8
        rtsen = (req.value & 0x0200) >> 9

        if dtren:
            print("DTR is enabled, value", dtr)
        if rtsen:
            print("RTS is enabled, value", rts)

        return b''

    @mutable('ftdi_set_flow_ctrl_response')
    def handle_set_flow_ctrl(self, req):
        self.verbose("received set_flow_ctrl request")

        if req.value == 0x000:
            print("SET_FLOW_CTRL to no handshaking")
        if req.value & 0x0001:
            print("SET_FLOW_CTRL for RTS/CTS handshaking")
        if req.value & 0x0002:
            print("SET_FLOW_CTRL for DTR/DSR handshaking")
        if req.value & 0x0004:
            print("SET_FLOW_CTRL for XON/XOFF handshaking")

        return b''

    @mutable('ftdi_set_baud_rate_response')
    def handle_set_baud_rate_request(self, req):
        self.verbose("received set_baud_rate request")

        dtr = req.value & 0x0001
        print("baud rate set to", dtr)

        return b''

    @mutable('ftdi_set_data_response')
    def handle_set_data(self, req):
        self.verbose("received set_data request")

        return b''

    @mutable('ftdi_get_modem_status_response')
    def handle_get_modem_status(self, req):
        self.verbose("received get_status request")

        return b''

    @mutable('ftdi_set_event_char_response')
    def handle_set_event_char(self, req):
        self.verbose("received set_event_char request")

        return b''

    @mutable('ftdi_set_error_char_response')
    def handle_set_error_char(self, req):
        self.verbose("received set_error_char request")

        return b''

    @mutable('ftdi_set_latency_timer_response')
    def handle_set_latency_timer(self, req):
        self.verbose("received set_latency_timer request")

        return b''

    @mutable('ftdi_get_latency_timer_response')
    def handle_get_latency_timer(self, req):
        self.verbose("received get_latency_timer request")

        # bullshit value
        return struct.pack('B', self.latency_timer)

    @mutable('ftdi_read_ee_response')
    def handle_read_ee(self, req):
        return b'\x31\x60'
        

class USBFtdiInterface(USBInterface):
    name = "USB FTDI interface"

    def __init__(self, phy, interface_number):
        descriptors = { }
        self.phy=phy
        endpoints = [
            USBEndpoint(
                phy,
                1,          # endpoint number
                USBEndpoint.direction_out,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                64,      # max packet size
                0,          # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available      # handler function
            ),
            USBEndpoint(
                phy,
                3,          # endpoint number
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                64,      # max packet size
                0,          # polling interval, see USB 2.0 spec Table 9-13
                None        # handler function
            )
        ]

        # TODO: un-hardcode string index (last arg before "verbose")
        USBInterface.__init__(
                self,
                phy=self.phy,
                interface_number=0,          # interface number
                interface_alternate=0,          # alternate setting
                interface_class=0xff,       # interface class: vendor-specific
                interface_subclass=0xff,       # subclass: vendor-specific
                interface_protocol=0xff,       # protocol: vendor-specific
                interface_string_index=0,          # string index
                endpoints=endpoints,
                descriptors=descriptors
        )

    def handle_data_available(self, data):
        s = data[1:]
        self.verbose("received string", s)

        s = s.replace(b'\r', b'\r\n')

        reply = b'\x01\x00' + s

        self.phy.send_on_endpoint(3, reply)


class USBFtdiDevice(USBDevice):
    name = "USB FTDI device"

    def __init__(self, phy):
        interface = USBFtdiInterface(phy,0)

        config = USBConfiguration(
                phy=phy,
                configuration_index=1,                                          # index
                configuration_string_or_index="FTDI",                                     # string desc
                interfaces=[ interface ]                               # interfaces
        )

        USBDevice.__init__(
                self,
                phy,
                0,                      # device class
                0,                      # device subclass
                0,                      # protocol release number
                64,                     # max packet size for endpoint 0
                0x0403,                 # vendor id: FTDI
                0x6001,                 # product id: FT232 USB-Serial (UART) IC
                0x0001,                 # device revision
                "Future Technology Devices International, Ltd",              # manufacturer string
                "FT232 Serial (UART) IC",        # product string
                "FTGQOTV+",             # serial number string
                [ config ]
        )

        self.device_vendor = USBFtdiVendor(phy)
        self.device_vendor.set_device(self)

