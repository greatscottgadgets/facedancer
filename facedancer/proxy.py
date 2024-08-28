#
# This file is part of Facedancer.
#
""" USB Proxy implementation. """

import atexit
import platform
import usb1
import sys

from usb1        import USBError, USBErrorTimeout

from .           import DeviceSpeed, USBConfiguration, USBDirection
from .device     import USBBaseDevice
from .errors     import DeviceNotFoundError
from .logging    import log
from .request    import USBControlRequest
from .types      import USB


class USBProxyDevice(USBBaseDevice):
    """ USB Proxy Device """

    name = "USB Proxy Device"

    filter_list = []

    def __init__(self, index=0, quirks=[], scheduler=None, **kwargs):
        """
        Sets up a new USBProxy instance.
        """

        # Finally, initialize our base class with a minimal set of
        # parameters.  We'll do almost nothing, as we'll be proxying
        # packets by default to the device.
        super().__init__()

        # We have only one proxy backend in existence at this time.
        self.proxied_device = LibUSB1Device

        # Maintain a list of the current configuration's endpoints.
        self.endpoints = {}

        # Find the device to proxy matching the given keyword arguments...
        usb_devices = list(self.proxied_device.find(find_all=True, **kwargs))
        if len(usb_devices) <= index:
            raise DeviceNotFoundError(f"Could not find device to proxy.")
        device = usb_devices[index]

        # Open a connection to the proxied device and attempt to
        # detach it from any kernel-side driver that may prevent us
        # from communicating with it...
        device_handle = self.proxied_device.open(device, detach=True)
        log.info(f"Found {self.proxied_device.device_speed().name} speed device to proxy: {device}")


    def add_filter(self, filter_object, head=False):
        """
        Adds a filter to the USBProxy filter stack.
        """
        if head:
            self.filter_list.insert(0, filter_object)
        else:
            self.filter_list.append(filter_object)


    def connect(self):
        """
        Initialize this device. We perform a reduced initialization, as we really
        only want to proxy data.
        """

        # Always use a max_packet_size of 64 on EP0.

        # This works around a Linux spec violation in which Linux assumes it can read 64 bytes of
        # control descriptor no matter the device speed and actual maximum packet size. If this
        # doesn't work, Linux tries to reset / power-cycle the device, and then recovers with an
        # in-spec read; but this causes a huge delay and/or breakage, depending on the proxied
        # device.
        #
        # Since we're working at the transfer levels, the packet sizes will automatically be
        # translated, anyway.
        self.max_packet_size_ep0 = 64

        # Get the USB device speed of the device being proxied.
        device_speed = self.proxied_device.device_speed()

        # Connect device.
        super().connect(device_speed=device_speed)

        # TODO check if we still need this in facedancer v3
        # skipping USB.state_attached may not be strictly correct (9.1.1.{1,2})
        self.state = USB.state_powered


    # - event handlers --------------------------------------------------------

    def configured(self, configuration: USBConfiguration):
        """
        Callback that handles when the target device becomes configured.
        If you're using the standard filters, this will be called automatically;
        if not, you'll have to call it once you know the device has been configured.

        Args:
            configuration: The configuration to be applied.
        """

        # Clear endpoint list.
        self.endpoints = {}

        # Gather the configuration's endpoints for easy access, later...
        for interface in configuration.interfaces.values():
            interface.parent = configuration # FIXME Not great semantics
            for endpoint in interface.endpoints.values():
                self.endpoints[endpoint.number] = endpoint

        # ... and pass our configuration on to the core device.
        self.backend.configured(configuration)
        configuration.parent = self # FIXME Not great semantics
        self.configuration = configuration


    def handle_bus_reset(self):
        super().handle_bus_reset()


    def handle_request(self, request: USBControlRequest):
        """
        Proxies EP0 requests between the victim and the target.
        """

        if request.get_direction() == 1:
            self._proxy_in_control_request(request)
        else:
            self._proxy_out_control_request(request)


    def handle_get_configuration_request(self, request):
        super().handle_get_configuration_request(request)


    def handle_get_descriptor_request(self, request):
        super().handle_get_descriptor_request(request)


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
                self.proxied_device.write(ep_num, data)
            except USBError as e:
                stalled = True

                for f in self.filter_list:
                    request, data, stalled = f.handle_out_stall(ep_num, data, stalled)

                if stalled:
                    self.backend.stall_endpoint(0, USBDirection.OUT)


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


    # - helpers ---------------------------------------------------------------

    def _ack_status_stage(self, blocking=False):
        self.backend.ack_status_stage(blocking=blocking)

    def _proxy_in_control_request(self, request: USBControlRequest):
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
            request, stalled = f.filter_control_in_setup(request, stalled)

        # If we stalled immediately, handle the stall and return without proxying.
        if stalled:
            self.backend.stall_endpoint(0, USBDirection.IN)
            return

        # If we filtered out the setup request, NAK.
        if request is None:
            return

        # Read any data from the real device...
        try:
            data = self.proxied_device.controlRead(
                request_type=request.request_type,
                request=request.request,
                value=request.value,
                index=request.index,
                length=request.length,
            )
        except USBError as e:
            stalled = True

        # Run filters here.
        for f in self.filter_list:
            request, data, stalled = f.filter_control_in(request, data, stalled)

        #... and proxy it to our victim.
        if stalled:
            # TODO: allow stalling of eps other than 0!
            self.backend.stall_endpoint(0, USBDirection.IN)
        else:
            # TODO: support control endpoints other than 0
            self.control_send(0, request, data)


    def _proxy_out_control_request(self, request: USBControlRequest):
        """
        Proxy OUT requests, which sends a request from the victim to the
        target device.
        """

        data = request.data

        for f in self.filter_list:
            request, data = f.filter_control_out(request, data)

        # ... forward the request to the real device.
        if request:
            try:
                self.proxied_device.controlWrite(
                    request_type=request.request_type,
                    request=request.request,
                    value=request.value,
                    index=request.index,
                    data=data
                )
                self._ack_status_stage()

            # Special case: we've stalled, allow the filters to decide what to do.
            except USBError as e:
                stalled = True

                for f in self.filter_list:
                    request, data, stalled = f.handle_out_request_stall(request, data, stalled)

                if stalled:
                    self.backend.stall_endpoint(0, USBDirection.OUT)


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

        try:
            # Quick hack to improve responsiveness on interrupt endpoints.
            if endpoint.interval:
                data = self.proxied_device.read(ep_num, endpoint.max_packet_size, timeout=endpoint.interval)
            else:
                data = self.proxied_device.read(ep_num, endpoint.max_packet_size)

        except usb1.USBErrorPipe:
            self.proxied_device.clear_halt(ep_num, USBDirection.IN)
            return
        except USBErrorTimeout:
            return

        # Run the data through all of our filters.
        for f in self.filter_list:
            ep_num, data = f.filter_in(endpoint.number, data)

        # If our data wasn't filtered out, transmit it to the target!
        if data:
            endpoint.send(data)



class LibUSB1Device:
    """ A wrapper around the proxied device based on libusb1. """


    """ Class variable that stores our global libusb library context. """
    context = None

    """ Class variable that stores our device handle. """
    device_handle = None


    @classmethod
    def _get_libusb_context(cls):
        """ Retrieves the libusb context we'll use to fetch libusb device instances. """

        # If we don't have a libusb context, create one.
        if cls.context is None:
            cls.context = usb1.USBContext().__enter__()
            atexit.register(cls._destroy_libusb_context)

        return cls.context


    @classmethod
    def _destroy_libusb_context(cls):
        """ Destroys our libusb context on closing our python instance. """
        if cls.device_handle is not None:
            device = cls.device_handle.getDevice()
            number = cls.device_handle.getConfiguration()
            active_configuration = next(filter(lambda c: c.getConfigurationValue() == number, device), None)
            if active_configuration:
                for interface in active_configuration:
                    number = interface[0].getNumber()
                    try:
                        cls.device_handle.releaseInterface(number)
                    except usb1.USBErrorNotFound as e:
                        log.warning(f"Failed to releace interface {0} for {device}")
                        pass

            cls.device_handle.close()
            cls.device_handle = None

        if cls.context is not None:
            cls.context.close()
            cls.context = None


    @classmethod
    def open(cls, device, detach=True):
        cls.device_handle = device.open()
        try:
            cls.device_handle.setAutoDetachKernelDriver(detach)
        except usb1.USBErrorNotSupported:
            pass

        number = cls.device_handle.getConfiguration()
        active_configuration = next(filter(lambda c: c.getConfigurationValue() == number, device), None)
        if active_configuration:
            for interface in active_configuration:
                number = interface[0].getNumber()
                try:
                    cls.device_handle.claimInterface(number)
                except usb1.USBErrorAccess:
                    log.error(f"Failed to claim interface {number} for {device}")
                    if platform.system() == "Darwin":
                        log.error("You may need to run your proxy code as root.\n")
                    elif platform.system() == "Linux":
                        log.error("Please ensure you have configured an entry for the device in your")
                        log.error("/etc/udev/rules.d directory.\n")
                    elif platform.system() == "Windows":
                        log.error("You may need to experiment with the Zadig driver to access the device.\n")
                    sys.exit(1)

        return cls.device_handle


    # TODO adapt logic from pygreat usb1.py
    @classmethod
    def find(cls, idVendor, idProduct, find_all=True):
        """ Finds a USB device by its identifiers. """

        matching_devices = []
        context = cls._get_libusb_context()

        for device in context.getDeviceList():
            if device.getVendorID() == idVendor and device.getProductID() == idProduct:
                matching_devices.append(device)

        if find_all:
            return matching_devices
        elif matching_devices:
            return matching_devices
        else:
            return None


    @classmethod
    def device_speed(cls):
        return DeviceSpeed(cls.device_handle.getDevice().getDeviceSpeed())


    @classmethod
    def controlRead(cls, request_type, request, value, index, length, timeout=1000):
        return cls.device_handle.controlRead(request_type, request, value, index, length, timeout)


    @classmethod
    def controlWrite(cls, request_type, request, value, index, data, timeout=1000):
        return cls.device_handle.controlWrite(request_type, request, value, index, data, timeout)


    @classmethod
    def read(cls, endpoint_number, length, timeout=1000):
        # Avoid accidental uses of endpoint address
        endpoint_number = endpoint_number & 0x7f

        # TODO support interrupt endpoints
        return cls.device_handle.bulkRead(endpoint_number, length, timeout)


    @classmethod
    def write(cls, endpoint_number, data, timeout=1000):
        # TODO support interrupt endpoints
        return cls.device_handle.bulkWrite(endpoint_number, data, timeout)


    @classmethod
    def clear_halt(cls, endpoint_number, direction):
        endpoint_address = direction.to_endpoint_address(endpoint_number)
        return cls.device_handle.clearHalt(endpoint_address)


if __name__ == "__main__":
    from .                  import FacedancerUSBApp
    from .filters.standard  import USBProxySetupFilters
    from .filters.logging   import USBProxyPrettyPrintFilter

    # akai midimix
    VENDOR_ID  = 0x09e8
    PRODUCT_ID = 0x0031

    # xbox controller
    #VENDOR_ID  = 0x045e
    #PRODUCT_ID = 0x02d1

    device = USBProxyDevice(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)

    device.add_filter(USBProxySetupFilters(device, verbose=2))
    device.add_filter(USBProxyPrettyPrintFilter(verbose=5))

    async def configure_logging():
        import logging
        logging.getLogger("facedancer").setLevel(logging.INFO)

    from facedancer import main
    main(device, configure_logging())
