# USBDevice.py
#
# Contains class definitions for USBDevice and USBDeviceRequest.

from .USB import *
from .USBClass import *
from .USBConfiguration import USBConfiguration

from ..app.core import FacedancerBasicScheduler


import time
import struct

class USBDevice(USBDescribable):
    name = "generic device"

    DESCRIPTOR_TYPE_NUMBER    = 0x01
    DESCRIPTOR_LENGTH         = 0x12

    def __init__(self, phy, device_class=0, device_subclass=0,
            protocol_rel_num=0, max_packet_size_ep0=64, vendor_id=0, product_id=0,
            device_rev=0, manufacturer_string="", product_string="",
            serial_number_string="", configurations=[], descriptors={},
            spec_version=0x0002, verbose=0, quirks=[], usb_class=None, usb_vendor=None, bos=None, scheduler=None):
        super(USBDevice, self).__init__(phy)
        self.phy = phy
        self.verbose = verbose
        descriptors = descriptors if descriptors else {}
        configurations=configurations if configurations else []
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
        self.descriptors = {
            DescriptorType.device: self.get_descriptor,
            DescriptorType.configuration: self.handle_get_configuration_descriptor_request,
            DescriptorType.other_speed_configuration: self.get_other_speed_configuration_descriptor,
            DescriptorType.string: self.handle_get_string_descriptor_request,
            DescriptorType.hub: self.handle_get_hub_descriptor_request,
            DescriptorType.device_qualifier: self.get_device_qualifier_descriptor,
            DescriptorType.bos: self.get_bos_descriptor,
        }
        self.descriptors.update(descriptors)

        self.config_num = -1
        self.configuration = None
        self.configurations = configurations

        self.usb_class = usb_class
        self.usb_vendor = usb_vendor

        self.bos = bos

        for c in self.configurations:
            csi = 0
            if c.configuration_string:
                csi = self.get_string_id(c.configuration_string)
            c.set_configuration_string_index(csi)
            c.set_device(self)
            if self.usb_class is None:
                self.usb_class = c.usb_class
            if self.usb_vendor is None:
                self.usb_vendor = c.usb_vendor

        self.state = State.detached
        self.ready = False

        self.address = 0

        self.setup_request_handlers()

        # If we don't have a scheduler, create a basic scheduler.
        if scheduler:
            self.scheduler = scheduler
        else:
            self.scheduler = FacedancerBasicScheduler()

        # Add our IRQ-servicing task to the scheduler's list of tasks to be serviced.
        self.scheduler.add_task(lambda : self.phy.service_irqs())

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
        self.phy.connect(self)

        # skipping State.attached may not be strictly correct (9.1.1.{1,2})
        self.state = State.powered

    def disconnect(self):
        self.phy.disconnect()

        self.state = State.detached

    def run(self):
        self.scheduler.run()

    def ack_status_stage(self, blocking=False):
        self.phy.ack_status_stage(blocking=blocking)

    def set_address(self, address, defer=False):
        self.phy.set_address(address, defer)

    def get_descriptor(self, index=0, valid=False):
        bLength = 18
        bDescriptorType = 1
        bMaxPacketSize0 = self.max_packet_size_ep0
        d = struct.pack(
            '<BBHBBBBHHHBBBB',
            bLength,
            bDescriptorType,
            self.usb_spec_version,
            self.device_class,
            self.device_subclass,
            self.protocol_rel_num,
            bMaxPacketSize0,
            self.vendor_id,
            self.product_id,
            self.device_rev,
            self.manufacturer_string_id,
            self.product_string_id,
            self.serial_number_string_id,
            len(self.configurations)
        )
        return d

    def get_device_qualifier_descriptor(self, n):
        bDescriptorType = 6
        bNumConfigurations = len(self.configurations)
        bReserved = 0
        bMaxPacketSize0 = self.max_packet_size_ep0

        d = struct.pack(
            '<BHBBBBBB',
            bDescriptorType,
            self.usb_spec_version,
            self.device_class,
            self.device_subclass,
            self.protocol_rel_num,
            bMaxPacketSize0,
            bNumConfigurations,
            bReserved
        )
        d = struct.pack('B', len(d) + 1) + d
        return d
        
    def send_control_message(self, data):
        self.phy.send_on_endpoint(0, data)

    # IRQ handlers
    #####################################################

    def handle_request(self, req):
        if self.verbose > 3:
            print(self.name, "received request", repr(req))

        # figure out the intended recipient
        recipient_type = req.get_recipient()
        recipient = None
        handler_entity = None
        req_type = req.get_type()
        
        if req_type == Request.type_standard:    # for standard requests we lookup the recipient by index
            index = req.get_index()
            if recipient_type == Request.recipient_device:
                recipient = self
            elif recipient_type == Request.recipient_interface:
                index = index & 0xff
                if index < len(self.configuration.interfaces):
                    recipient = self.configuration.interfaces[index]
                else:
                    self.warning('Failed to get interface recipient at index: %d' % index)
            elif recipient_type == Request.recipient_endpoint:
                recipient = self.endpoints.get(index, None)
                if recipient is None:
                    print(self.name, 'Failed to get endpoint recipient at index: %d' % index)
            elif recipient_type == Request.recipient_other:
                recipient = self.configuration.interfaces[0]  # HACK for Hub class
            handler_entity = recipient

        elif req_type == Request.type_class:    # for class requests we take the usb_class handler from the configuration
            index = req.get_index()
            index = index & 0xff
            if (len(self.configurations)!=0):
                if index < len(self.configurations[0].interfaces):
                    handler_entity = self.configurations[0].interfaces[index].usb_class
                else:
                    handler_entity = self.usb_class
            else:
                handler_entity = self.usb_class
        elif req_type == Request.type_vendor:   # for vendor requests we take the usb_vendor handler from the configuration
            handler_entity = self.usb_vendor

        if not handler_entity:
            print(self.name, 'invalid handler entity, stalling')
            self.phy.stall_ep0()
            return

        # if handler_entity == 9:  # HACK: for hub class
        #     handler_entity = recipient

        print(self.name,'req: %s' % req)
        handler = handler_entity.request_handlers.get(req.request, None)

        if not handler:
            print(self.name, 'request not handled: %s' % req)
            print(self.name, 'handler entity type: %s' % (type(handler_entity)))
            print(self.name, 'handler entity: %s' % (handler_entity))
            print(self.name, 'handler_entity.request_handlers: %s' % (handler_entity.request_handlers))
            for k in sorted(handler_entity.request_handlers.keys()):
                self.error('0x%02x: %s' % (k, handler_entity.request_handlers[k]))
            self.error('invalid handler, stalling')
            self.phy.stall_ep0()
        try:
            handler(req)
        except:
            raise

    def handle_data_available(self, ep_num, data):
        if self.state == State.configured and ep_num in self.endpoints:
            endpoint = self.endpoints[ep_num]
            if callable(endpoint.handler):
                endpoint.handler(data)

    def handle_buffer_available(self, ep_num):
        if self.state == State.configured and ep_num in self.endpoints:
            endpoint = self.endpoints[ep_num]
            if callable(endpoint.handler):
                endpoint.handler()

    def handle_nak(self, ep_num):
        if self.state == State.configured and ep_num in self.endpoints:
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
        self.state = State.address

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
            self.phy.verbose += 1
            self.send_control_message(response[:n])

            self.phy.verbose -= 1

            if self.verbose > 5:
                print(self.name, "sent", n, "bytes in response")
        else:
            self.phy.stall_ep0()

    def handle_get_configuration_descriptor_request(self, num):
        if num < len(self.configurations):
            return self.configurations[num].get_descriptor()
        else:
            return self.configurations[0].get_descriptor()

    def get_other_speed_configuration_descriptor(self, num):
        if num < len(self.configurations):
            return self.configurations[num].get_other_speed_descriptor()
        else:
            return self.configurations[0].get_other_speed_descriptor()

    def get_bos_descriptor(self, num):
        if self.bos:
            return self.bos.get_descriptor()
        # no bos? stall ep
        return None

    def get_string0_descriptor(self):
        d = struct.pack(
            '<BBBB',
            4,      # length of descriptor in bytes
            3,      # descriptor type 3 == string
            9,      # language code 0, byte 0
            4       # language code 0, byte 1
        )
        return 

    def get_string_descriptor(self, num):
        print(self.name,'get_string_descriptor: %#x (%#x)' % (num, len(self.strings)))
        s = None
        if num <= len(self.strings):
            s = self.strings[num - 1].encode('utf-16')
        else:
            if self.configuration:
                s = self.configuration.get_string_by_id(num)
        if not s:
            s = self.strings[0].encode('utf-16')
        # Linux doesn't like the leading 2-byte Byte Order Mark (BOM);
        # FreeBSD is okay without it
        s = s[2:]

        d = struct.pack(
            '<BB',
            len(s) + 2,  # length of descriptor in bytes
            3            # descriptor type 3 == string
        )
        return d + s

    def handle_get_string_descriptor_request(self, num):
        if num == 0:
            return self.get_string0_descriptor()
        else:
            return self.get_string_descriptor(num)

    def handle_get_hub_descriptor_request(self, num):
        bLength = 9
        bDescriptorType = 0x29
        bNbrPorts = 4
        wHubCharacteristics = 0xe000
        bPwrOn2PwrGood = 0x32
        bHubContrCurrent = 0x64
        DeviceRemovable = 0
        PortPwrCtrlMask = 0xff

        hub_descriptor = struct.pack(
            '<BBBHBBBB',
            bLength,              # length of descriptor in bytes
            bDescriptorType,      # descriptor type 0x29 == hub
            bNbrPorts,            # number of physical ports
            wHubCharacteristics,  # hub characteristics
            bPwrOn2PwrGood,       # time from power on til power good
            bHubContrCurrent,     # max current required by hub controller
            DeviceRemovable,
            PortPwrCtrlMask
        )

        return hub_descriptor


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

        self.supported_device_class_trigger = True

        # configs are one-based
        if (req.value) > len(self.configurations):
            print(self.name,'Host tries to set invalid configuration: %#x' % (req.value - 1))
            self.config_num = 0
        else:
            self.config_num = req.value - 1

        self.configuration = self.configurations[self.config_num]
        self.state = State.configured

        # collate endpoint numbers
        self.endpoints = { }
        for i in self.configuration.interfaces:
            for e in i.endpoints:
                self.endpoints[e.number] = e

        # HACK: blindly acknowledge request
        self.ack_status_stage()

        # notify the device of the recofiguration, in case
        # it needs to e.g. set up endpoints accordingly
        self.phy.configured(self.configuration)

    # USB 2.0 specification, section 9.4.4 (p 282 of pdf)
    def handle_get_interface_request(self, req):
        print(self.name, "received GET_INTERFACE request")

        if req.index == 0:
            # HACK: currently only support one interface
            self.send_control_message(b'\x00')
        else:
            self.phy.stall_ep0()

    # USB 2.0 specification, section 9.4.10 (p 288 of pdf)
    def handle_set_interface_request(self, req):
        print(self.name, "received SET_INTERFACE request")

    # USB 2.0 specification, section 9.4.11 (p 288 of pdf)
    def handle_synch_frame_request(self, req):
        print(self.name, "received SYNCH_FRAME request")


class USBDeviceRequest:

    setup_request_types = {
        Request.type_standard: 'standard',
        Request.type_class: 'class',
        Request.type_vendor: 'vendor',
    }
    setup_request_receipients = {
        Request.recipient_device: 'device',
        Request.recipient_interface: 'interface',
        Request.recipient_endpoint: 'endpoint',
        Request.recipient_other: 'other',
    }

    def __init__(self, raw_bytes):
        '''Expects raw 8-byte setup data request packet'''
        (
            self.request_type,
            self.request,
            self.value,
            self.index,
            self.length
        ) = struct.unpack('<BBHHH', raw_bytes[:8])
        self.data = raw_bytes[8:]
        self.raw_bytes = raw_bytes

    def __str__(self):
        s = 'dir=%#x (%s), type=%#x (%s), rec=%#x (%s), req=%#x, val=%#x, idx=%#x, len=%#x' % (
            self.get_direction(),
            'in' if self.get_direction() else 'out',
            self.get_type(),
            self.setup_request_types.get(self.get_type(), 'unknown'),
            self.get_recipient(),
            self.setup_request_receipients.get(self.get_recipient(), 'unknown'),
            self.request,
            self.value,
            self.get_index(),
            self.length
        )
        return s

    def raw(self):
        """returns request as bytes"""
        b = struct.pack(
            '<BBHHH',
            self.request_type,
            self.request,
            self.value >> 8,
            self.index >> 8,
            self.length >> 8,
        )
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
        else:
            return self.index


