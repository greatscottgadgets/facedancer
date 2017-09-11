# USBProxy.py

# Contains class definitions to implement a simple USB Serial chip,
# such as the one in the HP48G+ and HP50G graphing calculators.  See
# usb-serial.txt in the Linux documentation for more info.

import facedancer

from facedancer.USB import *
from facedancer.USBDevice import *
from facedancer.USBConfiguration import *
from facedancer.USBInterface import *
from facedancer.USBEndpoint import *
from facedancer.USBVendor import *
from facedancer.errors import *

import usb
from usb.core import USBError


class USBProxyFilter:
    """
    Base class for filters that modify USB data.
    """

    def filter_control_in(self, req, data, stalled):
        return req, data, stalled

    def filter_control_out(self, req, data):
        return req, data

    def filter_in(self, ep_num, data):
        return ep_num, data

    def filter_out(self, ep_num, data):
        return ep_num, data

    def handle_out_request_stall(self, req, data, stalled):
        """
        Handles an OUT request that was stalled by the target.

        req: The request header for the request that stalled.
        data: The data stage for the request that stalled, if appropriate.
        stalled: True iff the request is still considered stalled. This can
            be overridden by previous filters, so it's possible for this to
            be false.
        """
        return req, data, stalled


class USBProxyDevice(USBDevice):
    name = "Proxy'd USB Device"

    filter_list = []

    def __init__(self, maxusb_app, idVendor, idProduct, verbose=0, quirks=[]):
        """
        Sets up a new USBProxy instance.
        """

        # Open a connection to the proxied device...
        self.libusb_device = usb.core.find(idVendor=idVendor, idProduct=idProduct)
        if self.libusb_device is None:
            raise DeviceNotFoundError("Could not find device to proxy!")

        # TODO: detach the right kernel driver every time
        # TODO: do this on configuration so we detach the same interfaces
        try:
            self.libusb_device.detach_kernel_driver(0)
        except:
            pass

        # ... and initialize our base class with a minimal set of parameters.
        # We'll do almost nothing, as we'll be proxying packets by default to the device.
        USBDevice.__init__(self, maxusb_app, verbose=verbose, quirks=quirks)


    def connect(self):
        """
        Initialize this device. We perform a reduced initilaization, as we really
        only want to proxy data.
        """

        max_ep0_packet_size = self.libusb_device.bMaxPacketSize0
        self.maxusb_app.connect(self, max_ep0_packet_size)

        # skipping USB.state_attached may not be strictly correct (9.1.1.{1,2})
        self.state = USB.state_powered


    def configured(self, configuration):
        """
        Callback that handles when the target device becomes configured.
        If you're using the standard filters, this will be called automatically;
        if not, you'll have to call it once you know the device has been configured.

        configuration: The configuration to be applied.
        """

        # Gather the configuration's endpoints for easy access, later...
        self.endpoints = {}
        for interface in configuration.interfaces:
            for endpoint in interface.endpoints:
                self.endpoints[endpoint.number] = endpoint

        # ... and pass our configuration on to the core device.
        self.maxusb_app.configured(configuration)
        configuration.set_device(self)


    def add_filter(self, filter_object, head=False):
        """
        Adds a filter to the USBProxy filter stack.
        """
        if head:
            self.filter_list.insert(0, filter_object)
        else:
            self.filter_list.append(filter_object)


    def handle_request(self, req):
        """
        Proxies EP0 requests between the victim and the target. 
        """
        if req.get_direction() == 1:
            self._proxy_in_request(req)
        else:
            self._proxy_out_request(req)


    def _proxy_in_request(self, req):
        """
        Proxy IN requests, which gather data from the target device and
        forward it to the victim.
        """

        data = []
        stalled = False

        # Read any data from the real device...
        try:
            data = self.libusb_device.ctrl_transfer(req.request_type, req.request,
                                         req.value, req.index, req.length)
        except USBError as e:
            stalled = True

        # Run filters here.
        for f in self.filter_list:
            req, data, stalled = f.filter_control_in(req, data, stalled)

        #... and proxy it to our victim.
        if stalled:
            # TODO: allow stalling of eps other than 0!
            self.maxusb_app.stall_ep0()
        else:
            self.send_control_message(data)


    def _proxy_out_request(self, req):
        """
        Proxy OUT requests, which sends a request from the victim to the
        target device.
        """

        data = req.data

        for f in self.filter_list:
            req, data = f.filter_control_out(req, data)

        # ... forward the request to the real device.
        if req:
            try:
                self.libusb_device.ctrl_transfer(req.request_type, req.request,
                    req.value, req.index, data)
                self.ack_status_stage()

            # Special case: we've stalled, allow the filters to decide what to do.
            except USBError as e:
                stalled = True

                for f in self.filter_list:
                    req, data, stalled = f.handle_out_request_stall(req, data, stalled)

                self.maxusb_app.stall_ep0()


    def handle_data_available(self, ep_num, data):
        """
        Handles the case where data is ready from the Facedancer device
        that needs to be proxied to the target device.
        """

        # Run the data through all of our filters.
        for f in self.filter_list:
            ep_num, data = f.filter_out(ep_num, data)

        # If the data wasn't filtered out, communicate it to the target device.
        if data:
            self.libusb_device.write(ep_num, data)


    def handle_nak(self, ep_num):
        """
        Handles a NAK, which means that the target asked the proxied device
        to participate in a transfer. We use this as our cue to participate
        in communications.
        """

        # TODO: Currently, we use this for _all_ non-control transfers, as we
        # don't e.g. periodically schedule isochronous or interrupt transfers.
        # We probably should set up those to be independently scheduled and
        # then limit this to only bulk endpoints.

        # Get the endpoint object we reference.
        endpoint = self.endpoints[ep_num]

        # Skip handling OUT endpoints, as we handle those in handle_data_available.
        if not endpoint.direction:
            return

        self._proxy_in_transfer(endpoint)


    def _proxy_in_transfer(self, endpoint):
        """
        Proxy OUT requests, which sends a request from the target device to the
        victim, at the target's request.
        """

        # Read the target data from the target device.
        endpoint_address = endpoint.number | 0x80
        data = self.libusb_device.read(endpoint_address, endpoint.max_packet_size)

        # Run the data through all of our filters.
        for f in self.filter_list:
            ep_num, data = f.filter_in(endpoint.number, data)

        # If our data wasn't filtered out, transmit it to the target!
        if data:
            endpoint.send_packet(data)

