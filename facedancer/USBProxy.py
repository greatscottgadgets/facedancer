# USBProxy.py

# Contains class definitions to implement a simple USB Serial chip,
# such as the one in the HP48G+ and HP50G graphing calculators.  See
# usb-serial.txt in the Linux documentation for more info.

import errno
import facedancer

from facedancer.USB import *
from facedancer.USBDevice import *
from facedancer.USBConfiguration import *
from facedancer.USBInterface import *
from facedancer.USBEndpoint import *
from facedancer.USBVendor import *
from facedancer.constants import DeviceSpeed
from facedancer.errors import *

import usb
from usb.core import USBError


class USBProxyFilter:
    """
    Base class for filters that modify USB data.
    """

    def filter_control_in_setup(self, req, stalled):
        """
        Filters a SETUP stage for an IN control request. This allows us to modify
        the SETUP stage before it's proxied to the real device.

        req: The request to be issued.
        stalled: True iff the packet has been stalled by a previous filter.

        returns: Modified versions of the arguments. If stalled is set to true,
            the packet will be immediately stalled an not proxied. If stalled is
            false, but req is returned as None, the packet will be NAK'd instead
            of proxied.
        """
        return req, stalled


    def filter_control_in(self, req, data, stalled):
        """
        Filters the data response from the proxied device during an IN control
        request. This allows us to modify the data returned from the proxied
        device during a setup stage.

        req: The request that was issued to the target host.
        data: The data being proxied during the data stage.
        stalled: True if the proxied device (or a previous filter) stalled the
                request.

        returns: Modified versions of the arguments. Note that modifying req
            will _only_ modify the request as seen by future filters, as the
            SETUP stage has already passed and the request has already been
            sent to the device.
        """
        return req, data, stalled


    def filter_control_out(self, req, data):
        """
        Filters handling of an OUT control request, which contains both a
        request and (optional) data stage.

        req: The request issued by the target host.
        data: The data sent by the target host with the request.

        returns: Modified versions of the arguments. Returning a request of
            None will absorb the packet silently and not proxy it to the
            device.
        """
        return req, data


    def handle_out_request_stall(self, req, data, stalled):
        """
        Handles an OUT request that was stalled by the proxied device.

        req: The request header for the request that stalled.
        data: The data stage for the request that stalled, if appropriate.
        stalled: True iff the request is still considered stalled. This can
            be overridden by previous filters, so it's possible for this to
            be false.
        """
        return req, data, stalled


    def filter_in_token(self, ep_num):
        """
        Filters an IN token before it's passed to the proxied device.
        This allows modification of e.g. the endpoint or absorption of
        the IN token before it's issued to the real device.

        ep_num: The endpoint number on which the IN token is to be proxied.
        returns: A modified version of the arguments. If ep_num is set to None,
            the token will be absorbed and not issued to the target host.
        """
        return ep_num


    def filter_in(self, ep_num, data):
        """
        Filters the response to an IN token (the data packet received in response
        to the host issuing an IN token).

        ep_num: The endpoint number associated with the data packet.
        data: The data packet received from the proxied device.

        returns: A modified version of the arguments. If data is set to none,
            the packet will be absorbed, and a NAK will be issued instead of
            responding to the IN request with data.
        """
        return ep_num, data


    def filter_out(self, ep_num, data):
        """
        Filters a packet sent from the host via an OUT token.

        ep_num: The endpoint number associated with the data packet.
        data: The data packet received from host.

        returns: A modified version of the arguments. If data is set to none,
            the packet will be absorbed,
        """
        return ep_num, data


    def handle_out_stall(self, ep_num, data, stalled):
        """
        Handles an OUT transfer that was stalled by the victim.

        ep_num: The endpoint number for the data that stalled.
        data: The data for the transfer that stalled, if appropriate.
        stalled: True iff the transfer is still considered stalled. This can
            be overridden by previous filters, so it's possible for this to
            be false.
        """
        return ep_num, data, stalled



class USBProxyDevice(USBDevice):
    name = "Proxy'd USB Device"

    filter_list = []

    def __init__(self, maxusb_app, verbose=0, index=0, quirks=[], scheduler=None, **kwargs):
        """
        Sets up a new USBProxy instance.
        """

        # Maintain a list of the current configuration's endpoints.
        self.endpoints = {}

        # Open a connection to the proxied device...
        usb_devices = list(usb.core.find(find_all=True, **kwargs))
        if len(usb_devices) <= index:
            raise DeviceNotFoundError("Could not find device to proxy!")
        self.libusb_device = usb_devices[index]


        try:
            interfaces = self.libusb_device.get_active_configuration().interfaces()
        except:
            print("-- could not read device interfaces --")
            interfaces = []


        # If possible, detach the device from any kernel-side driver that may prevent us
        # from communicating with it.
        for interface in interfaces:
            try:
                self.libusb_device.detach_kernel_driver(interface.bInterfaceNumber)
            except usb.core.USBError as e:
                if e.errno != errno.ENOENT:
                    print("-- could not detach interface {}--".format(interface))

        # ... and initialize our base class with a minimal set of parameters.
        # We'll do almost nothing, as we'll be proxying packets by default to the device.
        USBDevice.__init__(self, maxusb_app, verbose=verbose, quirks=quirks, scheduler=scheduler)


    def connect(self):
        """
        Initialize this device. We perform a reduced initialization, as we really
        only want to proxy data.
        """

        # Always use a max_packet_size of 64 on EP0.

        # This works around a Linux spec violation in which Linux assumes it can read 64 bytes of control
        # descriptor no matter the device speed and actual maximum packet size. If this doesn't work, Linux
        # tries to reset / power-cycle the device, and then recovers with an in-spec read; but this causes a
        # huge delay and/or breakage, depending on the proxied device.
        #
        # Since we're working at the transfer levels, the packet sizes will automatically be translated, anyway.
        max_ep0_packet_size = 64

        # Get the speed of the device being emulated and attempt to set it if the backend supports it.
        device_speed = DeviceSpeed(self.libusb_device.speed)
        try:
            self.maxusb_app.set_device_speed(device_speed)
        except:
            print(f"-- backend does not support setting device speed: {device_speed.name} --")

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

        # Clear endpoint list.
        self.endpoints = {}

        # Gather the configuration's endpoints for easy access, later...
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
        Proxy IN requests, which gather data from the device and
        forward it to the target host.
        """

        data = []
        stalled = False

        # Filter the setup stage generated by the target device. We can use this
        # to e.g. change the setup stage before proxying it to the target device,
        # or to absorb a packet before it's proxied.
        for f in self.filter_list:
            req, stalled = f.filter_control_in_setup(req, stalled)

        # If we stalled immediately, handle the stall and return without proxying.
        if stalled:
            self.maxusb_app.stall_ep0(1) # IN=1
            return

        # If we filtered out the setup request, NAK.
        if req is None:
            return

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
            self.maxusb_app.stall_ep0(1) # IN=1
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

                if stalled:
                    self.maxusb_app.stall_ep0(0) # OUT=0


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
            try:
                self.libusb_device.write(ep_num, data)
            except USBError as e:
                stalled = True

                for f in self.filter_list:
                    req, data, stalled = f.handle_out_stall(ep_num, data, stalled)

                if stalled:
                    self.maxusb_app.stall_ep0(0) # OUT=0



    def handle_nak(self, ep_num):
        """
        Handles a NAK, which means that the target asked the proxied device
        to participate in a transfer. We use this as our cue to participate
        in communications.
        """

        # Make sure the endpoint exists for the current configuration
        # before attempting to handle NAK events.
        if not ep_num in self.endpoints:
            return

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

        ep_num = endpoint.number

        # Filter the "IN token" generated by the target device. We can use this
        # to e.g. change the endpoint before proxying to the target device, or
        # to absorb a packet before it's proxied.
        for f in self.filter_list:
            ep_num = f.filter_in_token(ep_num)

        if ep_num is None:
            return

        # Read the target data from the target device.
        endpoint_address = ep_num | 0x80


        # Quick hack to improve responsiveness on interrupt endpoints.
        try:
            if endpoint.interval:
                timeout = endpoint.interval
            else:
                timeout = None

            data = self.libusb_device.read(endpoint_address, endpoint.max_packet_size, timeout=timeout)
        except usb.core.USBError as e:
            if e.errno != errno.ETIMEDOUT:
                raise e
            else:
                return


        # Run the data through all of our filters.
        for f in self.filter_list:
            ep_num, data = f.filter_in(endpoint.number, data)

        # If our data wasn't filtered out, transmit it to the target!
        if data:
            endpoint.send_packet(data)
