# USBFtdi.py
#
# Contains class definitions to implement a USB FTDI chip.

from facedancer.usb.USBDevice import *
from facedancer.usb.USBConfiguration import *
from facedancer.usb.USBInterface import *
from facedancer.usb.USBEndpoint import *
from facedancer.usb.USBVendor import *
from facedancer.fuzz.helpers import mutable
from six.moves.queue import Queue

class USBFtdiVendor(USBVendor):
    name = 'FtdiVendor'

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
            0x03: self.handle_set_baud_rate,
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
        return b''

    @mutable('ftdi_modem_ctrl_response')
    def handle_modem_ctrl(self, req):
        self.dtr = req.value & 0x0001
        self.rts = (req.value & 0x0002) >> 1
        self.dtren = (req.value & 0x0100) >> 8
        self.rtsen = (req.value & 0x0200) >> 9
        if self.dtren:
            self.info('DTR is enabled, value %d' % self.dtr)
        if self.rtsen:
            self.info('RTS is enabled, value %d' % self.rts)
        return b''

    @mutable('ftdi_set_flow_ctrl_response')
    def handle_set_flow_ctrl(self, req):
        self.flow_control = req.value
        if req.value == 0x000:
            self.info('SET_FLOW_CTRL to no handshaking')
        if req.value & 0x0001:
            self.info('SET_FLOW_CTRL for RTS/CTS handshaking')
        if req.value & 0x0002:
            self.info('SET_FLOW_CTRL for DTR/DSR handshaking')
        if req.value & 0x0004:
            self.info('SET_FLOW_CTRL for XON/XOFF handshaking')
        return b''

    @mutable('ftdi_set_baud_rate_response')
    def handle_set_baud_rate(self, req):
        self.dtr = req.value & 0x0001
        self.baudrate = req.value
        self.info('baudrate set to: %#x dtr set to: %#x' % (self.baudrate, self.dtr))
        return b''

    @mutable('ftdi_set_data_response')
    def handle_set_data(self, req):
        self.data = req.value
        return b''

    @mutable('ftdi_get_modem_status_response')
    def handle_get_modem_status(self, req):
        return b'\x00' * req.length

    @mutable('ftdi_set_event_char_response')
    def handle_set_event_char(self, req):
        return b''

    @mutable('ftdi_set_error_char_response')
    def handle_set_error_char(self, req):
        return b''

    @mutable('ftdi_set_latency_timer_response')
    def handle_set_latency_timer(self, req):
        self.latency_timer = req.value & 0xff
        return b''

    @mutable('ftdi_get_latency_timer_response')
    def handle_get_latency_timer(self, req):
        return struct.pack('B', self.latency_timer)

    @mutable('ftdi_read_ee_response')
    def handle_read_ee(self, req):
        return b'\x31\x60'
        

class USBFtdiInterface(USBInterface):
    name = 'FtdiInterface'

    def __init__(self, phy, interface_number):
        super(USBFtdiInterface, self).__init__(
            phy=phy,
            interface_number=interface_number,
            interface_alternate=0,
            interface_class=USBClass.VendorSpecific,
            interface_subclass=0xff,
            interface_protocol=0xff,
            interface_string_index=0,
            endpoints=[
                USBEndpoint(
                    phy=phy,
                    number=1,
                    direction=USBEndpoint.direction_out,
                    transfer_type=USBEndpoint.transfer_type_bulk,
                    sync_type=USBEndpoint.sync_type_none,
                    usage_type=USBEndpoint.usage_type_data,
                    max_packet_size=0x40,
                    interval=0,
                    handler=self.handle_data_available
                ),
                USBEndpoint(
                    phy=phy,
                    number=3,
                    direction=USBEndpoint.direction_in,
                    transfer_type=USBEndpoint.transfer_type_bulk,
                    sync_type=USBEndpoint.sync_type_none,
                    usage_type=USBEndpoint.usage_type_data,
                    max_packet_size=0x40,
                    interval=0,
                    handler=self.handle_ep3_buffer_available  # at this point, we don't send data to the host
                )
            ],
        )
        self.txq = Queue()

    def handle_data_available(self, data):
        self.debug('received string (%d): %s' % (len(data), data))
        reply = b'\x01\x00' + data
        self.txq.put(reply)

    def handle_ep3_buffer_available(self):
        if not self.txq.empty():
            self.send_on_endpoint(3, self.txq.get())


class USBFtdiDevice(USBDevice):
    name = 'Ftdi device'

    def __init__(self, phy, vid=0x0403, pid=0x6001, rev=0x0100, **kwargs):
        super(USBFtdiDevice, self).__init__(
            phy=phy,
            device_class=USBClass.Unspecified,
            device_subclass=0,
            protocol_rel_num=0,
            max_packet_size_ep0=0x40,
            vendor_id=0x0403,
            product_id=0x6001,
            device_rev=0x0600,
            manufacturer_string='Future Technology Devices International, Ltd',
            product_string='FT232 Serial (UART) IC',
            serial_number_string='FTGQOTV+',
            configurations=[
                USBConfiguration(
                    phy=phy,
                    configuration_index=1,
                    configuration_string_or_index='FTDI',
                    interfaces=[
                        USBFtdiInterface(phy, 0)
                    ],
                    attributes=USBConfiguration.ATTR_BASE,
                    max_power=0x2d,
                )
            ],
            usb_vendor=USBFtdiVendor(phy=phy)
        )


usb_device = USBFtdiDevice

#self.device_vendor = USBFtdiVendor(phy)
#self.device_vendor.set_device(self)

