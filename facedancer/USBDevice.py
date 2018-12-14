# USBDevice.py
#
# Contains class definitions for USBDevice and USBDeviceRequest.

from .USB import *
from .USBClass import *
from .USBConfiguration import USBConfiguration



import time
import struct

class USBDevice(USBDescribable):
    name = "generic device"

    DESCRIPTOR_TYPE_NUMBER    = 0x01
    DESCRIPTOR_LENGTH         = 0x12

    def __init__(self, maxusb_app, device_class=0, device_subclass=0,
            protocol_rel_num=0, max_packet_size_ep0=64, vendor_id=0, product_id=0,
            device_rev=0, manufacturer_string="", product_string="",
            serial_number_string="", configurations=[], descriptors={},
            spec_version=0x0002, verbose=0, quirks=[], scheduler=None):
        self.maxusb_app = maxusb_app
        self.verbose = verbose

        self.quirks = quirks[:]
        self.correct_set_address = ('fast_set_address' not in quirks)

        self.strings = [ ]

        self.usb_spec_version           = spec_version

        # FIXME: Accept Class objects rather than raw numbers!!
        self.device_class               = device_class
        self.device_subclass            = device_subclass
        self.protocol_rel_num           = protocol_rel_num
        self.max_packet_size_ep0        = max_packet_size_ep0
        self.vendor_id                  = vendor_id
        self.product_id                 = product_id
        self.device_rev                 = device_rev
        self.manufacturer_string_id     = self.get_string_id(manufacturer_string)
        self.product_string_id          = self.get_string_id(product_string)

        if serial_number_string is not None:
            self.serial_number_string_id = self.get_string_id(serial_number_string)
        else:
            self.serial_number_string_id = 0


        # maps from USB.desc_type_* to bytearray OR callable
        self.descriptors = descriptors
        self.descriptors[USB.desc_type_device] = lambda _ : self.get_descriptor()
        self.descriptors[USB.desc_type_configuration] = self.handle_get_configuration_descriptor_request
        self.descriptors[USB.desc_type_string] = self.handle_get_string_descriptor_request

        self.config_num = -1
        self.configuration = None
        self.configurations = configurations

        for c in self.configurations:
            csi = 0
            if c.configuration_string:
                csi = self.get_string_id(c.configuration_string)
            c.set_configuration_string_index(csi)
            c.set_device(self)

        self.state = USB.state_detached
        self.ready = False

        self.address = 0

        self.setup_request_handlers()

        # If we don't have a scheduler, create a basic scheduler.
        if scheduler:
            self.scheduler = scheduler
        else:
            from .core import FacedancerBasicScheduler
            self.scheduler = FacedancerBasicScheduler()

        # Add our IRQ-servicing task to the scheduler's list of tasks to be serviced.
        self.scheduler.add_task(lambda : self.maxusb_app.service_irqs())




    @classmethod
    def from_binary_descriptor(cls, data):
        """
        Creates a USBDevice object from its descriptor.
        """

        # Pad the descriptor out with zeroes to the full length of a configuration descriptor.
        if len(data) < cls.DESCRIPTOR_LENGTH:
            padding_necessary = cls.DESCRIPTOR_LENGTH - len(data)
            data.extend([0] * padding_necessary)

        # Parse the core descriptor into its components...
        spec_version_msb, spec_version_lsb, device_class, device_subclass, device_protocol, \
                max_packet_size_ep0, vendor_id, product_id, device_rev_msb, device_rev_lsb, \
                manufacturer_string_index, product_string_index, \
                serial_number_string_index, num_configurations = struct.unpack("<xxBBBBBBHHBBBBBB", data)

        # FIXME: generate better placeholder configurations
        configurations  = [USBConfiguration()] * num_configurations

        # Generate our BCD arguments.
        spec_version = (spec_version_msb << 8) | spec_version_lsb
        device_rev = (device_rev_msb << 8) | device_rev_lsb

        return cls(None, device_class, device_subclass, device_protocol, max_packet_size_ep0,
                   vendor_id, product_id, device_rev, manufacturer_string_index, product_string_index,
                   serial_number_string_index, configurations, spec_version=spec_version)



    def get_string_id(self, s):

        # If we already have an index, leave it alone...
        if isinstance(s, int):
            return s

        # Otherwise, add the string to our list of strings and
        # report the index we assigned it.
        try:
            i = self.strings.index(s)
        except ValueError:
            # string descriptors start at index 1
            self.strings.append(s)
            i = len(self.strings)

        return i

    def setup_request_handlers(self):
        # see table 9-4 of USB 2.0 spec, page 279
        self.request_handlers = {
             0 : self.handle_get_status_request,
             1 : self.handle_clear_feature_request,
             3 : self.handle_set_feature_request,
             5 : self.handle_set_address_request,
             6 : self.handle_get_descriptor_request,
             7 : self.handle_set_descriptor_request,
             8 : self.handle_get_configuration_request,
             9 : self.handle_set_configuration_request,
            10 : self.handle_get_interface_request,
            11 : self.handle_set_interface_request,
            12 : self.handle_synch_frame_request
        }

    def connect(self):
        self.maxusb_app.connect(self)

        # skipping USB.state_attached may not be strictly correct (9.1.1.{1,2})
        self.state = USB.state_powered

    def disconnect(self):
        self.maxusb_app.disconnect()

        self.state = USB.state_detached

    def run(self):
        self.scheduler.run()
    
    def stop(self):
        self.scheduler.stop()

    def ack_status_stage(self, blocking=False):
        self.maxusb_app.ack_status_stage(blocking=blocking)

    def set_address(self, address, defer=False):
        self.maxusb_app.set_address(address, defer)

    def get_descriptor(self, n=0x12):
        d = bytearray([
            18,         # length of descriptor in bytes
            1,          # descriptor type 1 == device
            (self.usb_spec_version >> 8) & 0xff,
            self.usb_spec_version & 0xff,
            self.device_class,
            self.device_subclass,
            self.protocol_rel_num,
            self.max_packet_size_ep0,
            self.vendor_id & 0xff,
            (self.vendor_id >> 8) & 0xff,
            self.product_id & 0xff,
            (self.product_id >> 8) & 0xff,
            (self.device_rev >> 8) & 0xff,
            self.device_rev & 0xff,
            self.manufacturer_string_id,
            self.product_string_id,
            self.serial_number_string_id,
            len(self.configurations)
        ])
        return d[:n]

    def send_control_message(self, data):
        self.maxusb_app.send_on_endpoint(0, data)

    # IRQ handlers
    #####################################################

    def handle_request(self, req):
        if self.verbose > 3:
            print(self.name, "received request", repr(req))

        # figure out the intended recipient
        recipient_type = req.get_recipient()
        recipient = None
        index = req.get_index()
        if recipient_type == USB.request_recipient_device:
            recipient = self
        elif recipient_type == USB.request_recipient_interface:
            if index < len(self.configuration.interfaces):
                recipient = self.configuration.interfaces[index]
        elif recipient_type == USB.request_recipient_endpoint:
            if index == 0:
                recipient = self
            else:
                recipient = self.endpoints.get(index, None)

        if not recipient:
            print(self.name, "invalid recipient, stalling")
            self.maxusb_app.stall_ep0()
            return

        # and then the type
        req_type = req.get_type()
        handler_entity = None
        if req_type == USB.request_type_standard:
            handler_entity = recipient
        elif req_type == USB.request_type_class:
            handler_entity = recipient.device_class
        elif req_type == USB.request_type_vendor:
            handler_entity = recipient.device_vendor

        if not handler_entity:
            print(self.name, "invalid handler entity, stalling: {}".format(req))
            self.maxusb_app.stall_ep0()
            return

        handler = handler_entity.request_handlers.get(req.request, None)

        if not handler:
            print(self.name, "received unhandled EP0 control request; stallling:\n {}".format(repr(req)))
            self.maxusb_app.stall_ep0()
            return

        handler(req)

    def handle_data_available(self, ep_num, data):
        if self.state == USB.state_configured and ep_num in self.endpoints:
            endpoint = self.endpoints[ep_num]
            if callable(endpoint.handler):
                endpoint.handler(data)

    def handle_buffer_available(self, ep_num):
        if self.state == USB.state_configured and ep_num in self.endpoints:
            endpoint = self.endpoints[ep_num]
            if callable(endpoint.handler):
                endpoint.handler()

    def handle_nak(self, ep_num):
        if self.state == USB.state_configured and ep_num in self.endpoints:
            endpoint = self.endpoints[ep_num]
            if callable(endpoint.nak_callback):
                endpoint.nak_callback()


    # standard request handlers
    #####################################################

    # USB 2.0 specification, section 9.4.5 (p 282 of pdf)
    def handle_get_status_request(self, req):
        print(self.name, "received GET_STATUS request")

        # self-powered and remote-wakeup (USB 2.0 Spec section 9.4.5)
        response = b'\x03\x00'
        self.send_control_message(response)

    # USB 2.0 specification, section 9.4.1 (p 280 of pdf)
    def handle_clear_feature_request(self, req):
        print(self.name, "received CLEAR_FEATURE request with type 0x%02x and value 0x%02x" \
                % (req.request_type, req.value))
        self.ack_status_stage()

    # USB 2.0 specification, section 9.4.9 (p 286 of pdf)
    def handle_set_feature_request(self, req):
        print(self.name, "received SET_FEATURE request")

    # USB 2.0 specification, section 9.4.6 (p 284 of pdf)
    def handle_set_address_request(self, req):
        self.address = req.value
        self.state = USB.state_address

        # Quirk: if the "fast_set_address" quirk is on, don't enforce
        # correct set_address ordering. This speeds up set_address for
        # targets that need it.
        self.ack_status_stage(blocking=self.correct_set_address)

        # This print really shouldn't be here-- this is the critical path!
        #if self.verbose > 2:
        #    print(self.name, "received SET_ADDRESS request for address",
        #            self.address)

        self.set_address(self.address)

    # USB 2.0 specification, section 9.4.3 (p 281 of pdf)
    def handle_get_descriptor_request(self, req):
        dtype  = (req.value >> 8) & 0xff
        dindex = req.value & 0xff
        lang   = req.index
        n      = req.length

        response = None

        if self.verbose > 2:
            print(self.name, ("received GET_DESCRIPTOR req %d, index %d, " \
                    + "language 0x%04x, length %d") \
                    % (dtype, dindex, lang, n))

        response = self.descriptors.get(dtype, None)
        if callable(response):
            response = response(dindex)

        if response:
            n = min(n, len(response))
            self.maxusb_app.verbose += 1
            self.send_control_message(response[:n])

            self.maxusb_app.verbose -= 1

            if self.verbose > 5:
                print(self.name, "sent", n, "bytes in response")
        else:
            self.maxusb_app.stall_ep0()

    def handle_get_configuration_descriptor_request(self, num):
        return self.configurations[num].get_descriptor()

    def handle_get_string_descriptor_request(self, num):
        if num == 0:
            # HACK: hard-coding baaaaad
            d = bytes([
                    4,      # length of descriptor in bytes
                    3,      # descriptor type 3 == string
                    9,      # language code 0, byte 0
                    4       # language code 0, byte 1
            ])
        else:
            # string descriptors start at 1
            s = self.strings[num-1].encode('utf-16')

            # Linux doesn't like the leading 2-byte Byte Order Mark (BOM);
            # FreeBSD is okay without it
            s = s[2:]

            d = bytearray([
                    len(s) + 2,     # length of descriptor in bytes
                    3               # descriptor type 3 == string
            ])
            d += s

        return d

    # USB 2.0 specification, section 9.4.8 (p 285 of pdf)
    def handle_set_descriptor_request(self, req):
        print(self.name, "received SET_DESCRIPTOR request")

    # USB 2.0 specification, section 9.4.2 (p 281 of pdf)
    def handle_get_configuration_request(self, req):
        if self.verbose > 2:
            print(self.name, "received GET_CONFIGURATION request with data 0x%02x" \
                    % req.value)

        # If we haven't yet been configured, send back a zero configuration value.
        if self.configuration is None:
            self.send_control_message(b'\x00')
        # Otherwise, return the index for our configuration.
        else:
            config_index = self.configuration.configuration_index
            self.send_control_message(config_index.to_bytes(1, byteorder='little'))

    # USB 2.0 specification, section 9.4.7 (p 285 of pdf)
    def handle_set_configuration_request(self, req):
        print(self.name, "received SET_CONFIGURATION request")

        # configs are one-based
        self.config_num = req.value - 1
        self.configuration = self.configurations[self.config_num]
        self.state = USB.state_configured

        # collate endpoint numbers
        self.endpoints = { }
        for i in self.configuration.interfaces:
            for e in i.endpoints:
                self.endpoints[e.number] = e

        # HACK: blindly acknowledge request
        self.ack_status_stage()

        # notify the device of the recofiguration, in case
        # it needs to e.g. set up endpoints accordingly
        self.maxusb_app.configured(self.configuration)

    # USB 2.0 specification, section 9.4.4 (p 282 of pdf)
    def handle_get_interface_request(self, req):
        print(self.name, "received GET_INTERFACE request")

        if req.index == 0:
            # HACK: currently only support one interface
            self.send_control_message(b'\x00')
        else:
            self.maxusb_app.stall_ep0()

    # USB 2.0 specification, section 9.4.10 (p 288 of pdf)
    def handle_set_interface_request(self, req):
        print(self.name, "received SET_INTERFACE request")

    # USB 2.0 specification, section 9.4.11 (p 288 of pdf)
    def handle_synch_frame_request(self, req):
        print(self.name, "received SYNCH_FRAME request")

    def __repr__(self):
        return "<USBDevice object; vid=0x{:04x}, pid=0x{:04x}>".format(self.vendor_id, self.product_id)


class USBDeviceRequest:

    _type_descriptions = {
        0:  'standard',
        1:  'class',
        2:  'vendor',
        3:  'INVALID',
    }

    _recipent_descriptions = {
        0: 'device',
        1: 'interface',
        2: 'endpoint',
        3: 'other',
    }

    # TODO: split me up by recipient
    _standard_req_descriptions = {
        0: 'GET_STATUS',
        1: 'CLEAR_FEATURE',
        3: 'SET_FEATURE',
        5: 'SET_ADDRESS',
        6: 'GET_DESCRIPTOR',
        7: 'SET_DESCRIPTOR',
        8: 'GET_CONFIGRUATION',
        9: 'SET_CONFIGURATION',
        10: 'GET_INTERFACE',
        11: 'SET_INTERFACE',
        12: 'SYNCH_FRAME'
    }

    _descriptor_number_description = {
        1: 'DEVICE',
        2: 'CONFIGURATION',
        3: 'STRING',
        4: 'INTERFACE',
        5: 'ENDPOINT',
        6: 'DEVICE_QUALIFIER',
        7: 'OTHER_SPEED_CONFIG',
        8: 'POWER',
        33: 'HID',
        34: 'REPORT',
    }

    def __init__(self, raw_bytes):
        """Expects raw 8-byte setup data request packet"""

        self.request_type   = raw_bytes[0]
        self.request        = raw_bytes[1]
        self.value          = (raw_bytes[3] << 8) | raw_bytes[2]
        self.index          = (raw_bytes[5] << 8) | raw_bytes[4]
        self.length         = (raw_bytes[7] << 8) | raw_bytes[6]
        self.data           = raw_bytes[8:]

    def __str__(self):
        s = "dir=%d, type=%x, rec=%x, r=%x, v=%x, i=%x, l=%d" \
                % (self.get_direction(), self.get_type(), self.get_recipient(),
                   self.request, self.value, self.index, self.length)
        return s


    def __repr__(self):
        direction_marker = "<" if self.get_direction() == 1 else ">"

        # Pretty print, where possible.
        type = self.get_type_string()
        recipient = self.get_recipient_string()
        request = self.get_request_number_string()
        value = self.get_value_string()

        s = "%s, %s request to %s (%s: value=%s, index=%x, length=%d)" \
                % (direction_marker, type, recipient, request,
                   value, self.index, self.length)
        return s


    def get_type_string(self):
        return self._type_descriptions[self.get_type()]

    def get_recipient_string(self):
        return self._recipent_descriptions[self.get_type()]

    def get_request_number_string(self):
        if self.get_type() == 0:
            return self._get_standard_request_number_string()
        else:
            type = self.get_type_string()
            return "{} request {}".format(type, self.request)

    def _get_standard_request_number_string(self):
        if self.request in self._standard_req_descriptions:
            return self._standard_req_descriptions[self.request]
        else:
            return "unknown request {}".format(self.request)

    def get_value_string(self):
        # If this is a GET_DESCRIPTOR request, parse it.
        if self.get_type() == 0 and self.request == 6:
            descriptor_index = self.value & 0xff
            description = self.get_descriptor_number_string()
            return "{} descriptor (index=0x{:02x})".format(description, descriptor_index)
        else:
            return "%x" % self.value

    def get_descriptor_number_string(self):
        try:
            descriptor_index = self.value >> 8
            return self._descriptor_number_description[descriptor_index]
        except KeyError:
            return "unknown descriptor 0x%x" % self.value

    def raw(self):
        """returns request as bytes"""
        b = bytes([ self.request_type, self.request,
                    self.value  & 0xff, (self.value  >> 8) & 0xff,
                    self.index  & 0xff, (self.index  >> 8) & 0xff,
                    self.length & 0xff, (self.length >> 8) & 0xff
                  ])
        return b

    def get_direction(self):
        return (self.request_type >> 7) & 0x01

    def get_type(self):
        return (self.request_type >> 5) & 0x03

    def get_recipient(self):
        return self.request_type & 0x1f

    # meaning of bits in wIndex changes whether we're talking about an
    # interface or an endpoint (see USB 2.0 spec section 9.3.4)
    def get_index(self):
        rec = self.get_recipient()
        if rec == 1:                # interface
            return self.index
        elif rec == 2:              # endpoint
            return self.index & 0x0f


