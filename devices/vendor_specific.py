'''
Contains class definitions to implement a Vendor Specific USB Device.
'''
from facedancer.usb.USBClass import USBClass
from facedancer.usb.USBDevice import USBDevice, USBDeviceRequest, Request
from facedancer.usb.USBEndpoint import USBEndpoint
from facedancer.usb.USBVendor import USBVendor
from facedancer.usb.USBConfiguration import USBConfiguration
from facedancer.usb.USBInterface import USBInterface
from facedancer.usb.USB import *

import struct


class USBVendorSpecificVendor(USBVendor):
    name = 'VendorSpecificVendor'

    def setup_local_handlers(self):
        self.local_handlers = {
            x: self.handle_generic for x in range(256)
        }

    def handle_generic(self, req):
        self.always('Generic Vendor handler - req: %s' % req)


class USBVendorSpecificClass(USBClass):
    name = 'VendorSpecificClass'

    def setup_local_handlers(self):
        self.local_handlers = {
            x: self.handle_generic for x in range(256)
        }

    def handle_generic(self, req):
        self.always('Generic Class handler - req: %s' % req)


class USBVendorSpecificInterface(USBInterface):
    name = 'VendorSpecificInterface'

    def __init__(self, phy, num=0, interface_alternate=0, endpoints=[]):
        # TODO: un-hardcode string index
        super(USBVendorSpecificInterface, self).__init__(
            phy=phy,
            interface_number=num,
            interface_alternate=interface_alternate,
            interface_class=USBClass.VendorSpecific,
            interface_subclass=1,
            interface_protocol=1,
            interface_string_index=0,
            endpoints=[],
            usb_class=USBVendorSpecificClass(phy),
            usb_vendor=USBVendorSpecificVendor(phy)
        )
        self.virtual_endpoints = endpoints
        self.endpoints = []
        self.setup_request_handlers()

    def handle_buffer_available(self):
        pass

    def handle_data_available(self, data):
        return

    def handle_set_interface_request(self, req):
        self.always('set interface request')
        self.usb_function_supported()

    # Table 9-12 of USB 2.0 spec (pdf page 296)
    def get_descriptor(self, usb_type='fullspeed', valid=False):
        '''
        override the get_descriptor handler - so it would have access to the virtual_endpoints
        '''

        bLength = 9
        bDescriptorType = 4
        bNumEndpoints = len(self.virtual_endpoints)

        d = struct.pack(
            '<BBBBBBBBB',
            bLength,  # length of descriptor in bytes
            bDescriptorType,  # descriptor type 4 == interface
            self.number,
            self.alternate,
            bNumEndpoints,
            self.iclass.class_number,
            self.subclass,
            self.protocol,
            self.string_index
        )

        if self.iclass.class_number:
            iclass_desc_num = interface_class_to_descriptor_type(self.iclass.class_number)
            if iclass_desc_num:
                desc = self.descriptors[iclass_desc_num]
                if callable(desc):
                    desc = desc()
                d += desc

        for e in self.cs_interfaces:
            d += e.get_descriptor(usb_type, valid)

        for e in self.virtual_endpoints:
            d += e.get_descriptor(usb_type, valid)

        return d

    def setup_request_handlers(self):
        self.request_handlers = {
            x: self.handle_generic for x in range(256)
        }

    def handle_generic(self, req):
        self.always('Generic interface handler - req: %s' % req)


class USBVendorSpecificDevice(USBDevice):
    name = 'VendorSpecificDevice'

    def __init__(self, phy, vid, pid, rev=1, **kwargs):
        self.phy = phy
        super(USBVendorSpecificDevice, self).__init__(
            phy=phy,
            device_class=USBClass.VendorSpecific,
            device_subclass=1,
            protocol_rel_num=1,
            max_packet_size_ep0=64,
            vendor_id=vid,
            product_id=pid,
            device_rev=rev,
            manufacturer_string=('FD. VID:0x%04x' % vid),
            product_string=('FD. PID:0x%04x' % pid),
            serial_number_string='123456',
            configurations=[
                USBConfiguration(
                    phy=phy,
                    configuration_index=1,
                    configuration_string_or_index='Vendor Specific Conf',
                    interfaces=self.get_interfaces(phy),
                    attributes=USBConfiguration.ATTR_SELF_POWERED,
                )
            ],
        )


    def handle_request(self, req):
        self.debug("received request %s" % repr(req))

        # figure out the intended recipient
        req_type = req.get_type()
        recipient_type = req.get_recipient()
        recipient = None
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
            self.usb_function_supported()
            if index == 0:
                recipient = self
            else:
                recipient = self.endpoints.get(index, None)
            if recipient is None:
                self.warning('Failed to get endpoint recipient at index: %d' % index)
        elif recipient_type == Request.recipient_other:
            recipient = self.configuration.interfaces[0]  # HACK for Hub class

        if not recipient:
            self.warning('invalid recipient, stalling')
            self.phy.stall_ep0()
            return
        req_type = req.get_type()
        handler_entity = None
        if req_type == Request.type_standard:    # for standard requests we lookup the recipient by index
            handler_entity = recipient
        elif req_type == Request.type_class:    # for class requests we take the usb_class handler from the configuration
            handler_entity = self.usb_class
        elif req_type == Request.type_vendor:   # for vendor requests we take the usb_vendor handler from the configuration
            handler_entity = self.usb_vendor

        if not handler_entity:
            self.warning("received request %s" % req)
            self.warning('invalid handler entity, stalling')
            self.phy.stall_ep0()
            return

        # if handler_entity == 9:  # HACK: for hub class
        #     handler_entity = recipient

        self.debug('req: %s' % req)
        handler = handler_entity.request_handlers.get(req.request, None)

        if not handler:
            self.error('request not handled: %s' % req)
            self.error('handler entity type: %s' % (type(handler_entity)))
            self.error('handler entity: %s' % (handler_entity))
            self.error('handler_entity.request_handlers: %s' % (handler_entity.request_handlers))
            for k in sorted(handler_entity.request_handlers.keys()):
                self.error('0x%02x: %s' % (k, handler_entity.request_handlers[k]))
            self.error('invalid handler, stalling')
            self.phy.stall_ep0()
        try:
            handler(req)
        except:
            #traceback.print_exc()
            raise

    '''        
    def handle_request(self, req):
    '''
        #override the handle_request - in case a request is directed to an endpoint - we mark as supported
    '''

        # figure out the intended recipient
        req_type = req.get_type()
        recipient_type = req.get_recipient()

        if req_type == Request.type_standard:    # for standard requests we lookup the recipient by index
            if recipient_type == Request.recipient_endpoint:
                self.usb_function_supported()
                #self.phy.stall_ep0()
                return

        return req
    '''

    def handle_data_available(self, ep_num, data):
        '''
        override the ep handler as we are working with virtual endpoints - if data is available for the ep - we mark as supported
        '''
        self.usb_function_supported()

    def get_endpoint(self, phy, num, direction, transfer_type, max_packet_size=0x40):
        return USBEndpoint(
            phy=self.phy,
            number=num,
            direction=direction,
            transfer_type=transfer_type,
            sync_type=USBEndpoint.sync_type_none,
            usage_type=USBEndpoint.usage_type_data,
            max_packet_size=max_packet_size,
            interval=1,
            handler=self.global_handler,
            usb_class=USBVendorSpecificClass(self.phy),
            usb_vendor=USBVendorSpecificVendor(self.phy)
        )

    def get_interfaces(self, phy):
        self.phy=phy
        return [USBVendorSpecificInterface(self.phy, num=0,
                endpoints=[
                    self.get_endpoint(phy,1, USBEndpoint.direction_in, USBEndpoint.transfer_type_interrupt),
                    self.get_endpoint(phy,1, USBEndpoint.direction_out, USBEndpoint.transfer_type_interrupt),
                    self.get_endpoint(phy,2, USBEndpoint.direction_in, USBEndpoint.transfer_type_bulk),
                    self.get_endpoint(phy,2, USBEndpoint.direction_out, USBEndpoint.transfer_type_bulk),
                    self.get_endpoint(phy,3, USBEndpoint.direction_in, USBEndpoint.transfer_type_isochronous),
                    self.get_endpoint(phy,3, USBEndpoint.direction_out, USBEndpoint.transfer_type_isochronous),
                    self.get_endpoint(phy,4, USBEndpoint.direction_in, USBEndpoint.transfer_type_bulk),
                    self.get_endpoint(phy,4, USBEndpoint.direction_out, USBEndpoint.transfer_type_bulk),
                    self.get_endpoint(phy,5, USBEndpoint.direction_in, USBEndpoint.transfer_type_isochronous, max_packet_size=0x10),
                    self.get_endpoint(phy,5, USBEndpoint.direction_out, USBEndpoint.transfer_type_bulk, max_packet_size=0x20),
                    self.get_endpoint(phy,6, USBEndpoint.direction_in, USBEndpoint.transfer_type_isochronous, max_packet_size=0x20),
                    self.get_endpoint(phy,6, USBEndpoint.direction_out, USBEndpoint.transfer_type_bulk, max_packet_size=0x10),
                    self.get_endpoint(phy,7, USBEndpoint.direction_in, USBEndpoint.transfer_type_isochronous, max_packet_size=0x30),
                    self.get_endpoint(phy,7, USBEndpoint.direction_out, USBEndpoint.transfer_type_bulk, max_packet_size=0x30),
                    self.get_endpoint(phy,8, USBEndpoint.direction_in, USBEndpoint.transfer_type_isochronous, max_packet_size=0xff),
                    self.get_endpoint(phy,8, USBEndpoint.direction_out, USBEndpoint.transfer_type_bulk, max_packet_size=0xff),
                ]),
                USBVendorSpecificInterface(self.phy, num=1,
                endpoints=[
                    self.get_endpoint(phy,1, USBEndpoint.direction_in, USBEndpoint.transfer_type_interrupt),
                    self.get_endpoint(phy,1, USBEndpoint.direction_out, USBEndpoint.transfer_type_interrupt),
                    self.get_endpoint(phy,2, USBEndpoint.direction_in, USBEndpoint.transfer_type_bulk),
                    self.get_endpoint(phy,2, USBEndpoint.direction_out, USBEndpoint.transfer_type_bulk),
                    self.get_endpoint(phy,3, USBEndpoint.direction_in, USBEndpoint.transfer_type_isochronous),
                    self.get_endpoint(phy,3, USBEndpoint.direction_out, USBEndpoint.transfer_type_isochronous),
                    self.get_endpoint(phy,4, USBEndpoint.direction_in, USBEndpoint.transfer_type_bulk),
                    self.get_endpoint(phy,4, USBEndpoint.direction_out, USBEndpoint.transfer_type_bulk),
                    self.get_endpoint(phy,5, USBEndpoint.direction_in, USBEndpoint.transfer_type_isochronous, max_packet_size=0x10),
                    self.get_endpoint(phy,5, USBEndpoint.direction_out, USBEndpoint.transfer_type_bulk, max_packet_size=0x20),
                ]),
                ]

    def global_handler(self, data=None):
        if data is not None:
            self.usb_function_supported()


usb_device = USBVendorSpecificDevice
