# USBEndpoint.py
#
# Contains class definition for USBEndpoint.

class USBEndpoint:
    direction_out               = 0x00
    direction_in                = 0x01

    transfer_type_control       = 0x00
    transfer_type_isochronous   = 0x01
    transfer_type_bulk          = 0x02
    transfer_type_interrupt     = 0x03

    sync_type_none              = 0x00
    sync_type_async             = 0x01
    sync_type_adaptive          = 0x02
    sync_type_synchronous       = 0x03

    usage_type_data             = 0x00
    usage_type_feedback         = 0x01
    usage_type_implicit_feedback = 0x02

    def __init__(self, number, direction, transfer_type, sync_type,
            usage_type, max_packet_size, interval, handler):

        self.number             = number
        self.direction          = direction
        self.transfer_type      = transfer_type
        self.sync_type          = sync_type
        self.usage_type         = usage_type
        self.max_packet_size    = max_packet_size
        self.interval           = interval
        self.handler            = handler

        self.interface          = None

        self.request_handlers   = {
                1 : self.handle_clear_feature_request
        }

    def handle_clear_feature_request(self, req):
        print("received CLEAR_FEATURE request for endpoint", self.number,
                "with value", req.value)
        self.interface.configuration.device.maxusb_app.send_on_endpoint(0, b'')

    def set_interface(self, interface):
        self.interface = interface

    # see Table 9-13 of USB 2.0 spec (pdf page 297)
    def get_descriptor(self):
        address = (self.number & 0x0f) | (self.direction << 7) 
        attributes = (self.transfer_type & 0x03) \
                   | ((self.sync_type & 0x03) << 2) \
                   | ((self.usage_type & 0x03) << 4)

        d = bytearray([
                7,          # length of descriptor in bytes
                5,          # descriptor type 5 == endpoint
                address,
                attributes,
                self.max_packet_size & 0xff,
                (self.max_packet_size >> 8) & 0xff,
                self.interval
        ])

        return d

    def send(self, data):
        dev = self.interface.configuration.device
        dev.maxusb_app.send_on_endpoint(self.number, data)

    def recv(self):
        dev = self.interface.configuration.device
        data = dev.maxusb_app.read_from_endpoint(self.number)
        return data

