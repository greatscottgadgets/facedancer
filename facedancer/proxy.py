#
# This file is part of Facedancer.
#
"""USB Proxy implementation."""

import atexit
import platform
import usb1
import sys

from usb1 import USBError, USBErrorTimeout

from . import DeviceSpeed, USBConfiguration, USBDirection
from .endpoint import USBEndpoint
from .device import USBBaseDevice
from .errors import DeviceNotFoundError
from .logging import log
from .request import USBControlRequest
from .types import USB


class USBProxyDevice(USBBaseDevice):
    """USB Proxy Device"""

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

        # Find the device to proxy matching the given keyword arguments...
        usb_devices = list(self.proxied_device.find(find_all=True, **kwargs))
        if len(usb_devices) <= index:
            raise DeviceNotFoundError("Could not find device to proxy.")
        device = usb_devices[index]

        # Open a connection to the proxied device and attempt to
        # detach it from any kernel-side driver that may prevent us
        # from communicating with it...
        self.proxied_device.open(device, detach=True)
        log.info(
            f"Found {self.proxied_device.device_speed().name} speed device to proxy: {device}"
        )

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

        self.proxied_device.setConfiguration(configuration.number)

        # All interfaces on the configuration are set to their default setting.
        configuration.active_interfaces = {
            interface.number: interface
            for interface in configuration.get_interfaces()
            if interface.alternate == 0
        }

        # Pass our configuration on to the core device.
        self.backend.configured(configuration)
        configuration.parent = self  # FIXME Not great semantics
        self.configuration = configuration

        self._ack_status_stage()

    def interface_changed(self, interface_number: int, alternate: int):
        """
        Callback that handles when a SET_INTERFACE request is made to the target.
        If you're using the standard filters, this will be called automatically;
        if not, you'll have to call it once you know an alternate setting has been
        applied.

        Args:
            interface_number: The interface number.
            alternate: The alternate setting to be applied.
        """
        log.debug(f"set interface num={interface_number} alt={alternate}")
        self.proxied_device.setInterface(interface_number, alternate)

        identifier = (interface_number, alternate)
        interface = self.configuration.interfaces[identifier]
        self.configuration.active_interfaces[interface_number] = interface
        self._ack_status_stage()

    def handle_bus_reset(self):
        super().handle_bus_reset()
        self.proxied_device.reset()

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

    def handle_data_received(self, endpoint, data):
        """
        Handles the case where data is ready from the Facedancer device
        that needs to be proxied to the target device.
        """
        ep_num = endpoint.number

        # Run the data through all of our filters.
        for f in self.filter_list:
            ep_num, data = f.filter_out(ep_num, data)

        # If the data wasn't filtered out, communicate it to the target device.
        if data:
            try:
                self.proxied_device.write(ep_num, data)
            except USBError:
                stalled = True

                for f in self.filter_list:
                    request, data, stalled = f.handle_out_stall(ep_num, data, stalled)

                if stalled:
                    self.backend.stall_endpoint(0, USBDirection.OUT)

    def handle_data_requested(self, endpoint: USBEndpoint):
        """Handler called when the host requests data on a non-control endpoint.

        Typically, this method will delegate the request to the appropriate
        configuration+interface+endpoint. If overridden, the
        overriding function will receive all events.

        Args:
            endpoint_number : The endpoint number on which the host requested data.
        """
        # TODO: Currently, we use this for _all_ non-control transfers, as we
        # don't e.g. periodically schedule isochronous or interrupt transfers.
        # We probably should set up those to be independently scheduled and
        # then limit this to only bulk endpoints.
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
                data = self.proxied_device.read(
                    ep_num, endpoint.max_packet_size, timeout=endpoint.interval
                )
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
            if not endpoint.get_device():
                log.warning("endpoint has no device")
                return
            endpoint.send(data)

    # - helpers ---------------------------------------------------------------

    def _ack_status_stage(self):
        self.backend.ack_status_stage(blocking=True)

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
        except USBError:
            stalled = True

        # Run filters here.
        for f in self.filter_list:
            request, data, stalled = f.filter_control_in(request, data, stalled)

        # ... and proxy it to our victim.
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
                    data=data,
                )
                self._ack_status_stage()

            # Special case: we've stalled, allow the filters to decide what to do.
            except USBError:
                stalled = True

                for f in self.filter_list:
                    request, data, stalled = f.handle_out_request_stall(
                        request, data, stalled
                    )

                if stalled:
                    self.backend.stall_endpoint(0, USBDirection.OUT)


class LibUSB1Device:
    """A wrapper around the proxied device based on libusb1."""

    """ Class variable that stores our global libusb library context. """
    context: usb1.USBContext | None = None

    """ Class variable that stores our device handle. """
    device_handle: usb1.USBDeviceHandle | None = None

    @classmethod
    def _get_libusb_context(cls) -> usb1.USBContext:
        """Retrieves the libusb context we'll use to fetch libusb device instances."""

        # If we don't have a libusb context, create one.
        if cls.context is None:
            cls.context = usb1.USBContext().__enter__()
            atexit.register(cls._destroy_libusb_context)

        return cls.context

    @classmethod
    def _handle(cls) -> usb1.USBDeviceHandle:
        assert cls.device_handle is not None
        return cls.device_handle

    @classmethod
    def _destroy_libusb_context(cls):
        """Destroys our libusb context on closing our python instance."""
        if cls.device_handle is not None:
            cls._release()
            cls.device_handle.close()
            cls.device_handle = None

        if cls.context is not None:
            cls.context.close()
            cls.context = None

    @classmethod
    def open(cls, device: usb1.USBDevice, detach=True):
        log.debug(f"opening {device}")
        cls.device_handle = device.open()
        try:
            cls.device_handle.setAutoDetachKernelDriver(detach)
        except usb1.USBErrorNotSupported as e:
            log.debug(f"setAutoDetachKernelDriver: {e}")

        cls._claim()

        return cls.device_handle

    # TODO adapt logic from pygreat usb1.py
    @classmethod
    def find(cls, idVendor, idProduct, find_all=True):
        """Finds a USB device by its identifiers."""

        matching_devices = []
        context = cls._get_libusb_context()

        device: usb1.USBDevice
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
    def setInterface(cls, interface: int, alt: int):
        """libusb1 recommends always using this instead of sending control packets."""
        log.info(f"LibUSB1Device setInterface {interface} alt {alt}")
        cls._handle().setInterfaceAltSetting(interface, alt)

    @classmethod
    def setConfiguration(cls, number: int):
        """libusb1 recommends always using this instead of sending control packets."""
        old = cls._handle().getConfiguration()
        if old == number:
            log.info(f"LibUSB1Device keeping configuration {number}")
            return

        log.info(f"LibUSB1Device set configuration {old} → {number}")

        # prevent kernel driver from re-attaching
        cls._handle().setAutoDetachKernelDriver(0)

        cls._release()
        cls._handle().setConfiguration(number)
        cls._claim()

        cls._handle().setAutoDetachKernelDriver(1)

    @classmethod
    def _release(cls):
        active_configuration = cls.active_configuration()
        if not active_configuration:
            return

        for interface in active_configuration:
            number = interface[0].getNumber()
            try:
                log.info(f"Release interface {number}")
                cls._handle().releaseInterface(number)
            except usb1.USBErrorNotFound:
                log.warning(f"Failed to release interface {number}")

    @classmethod
    def _claim(cls):
        log.info("Claiming interfaces")
        active_configuration = cls.active_configuration()
        if not active_configuration:
            return

        for interface in active_configuration:
            number = interface[0].getNumber()
            try:
                log.info(f"Claiming interface {number}")
                cls._handle().claimInterface(number)
            except usb1.USBErrorAccess:
                log.error(f"Failed to claim interface {number}")
                if platform.system() == "Darwin":
                    log.error("You may need to run your proxy code as root.\n")
                elif platform.system() == "Linux":
                    log.error(
                        "Please ensure you have configured an entry for the device in your"
                    )
                    log.error("/etc/udev/rules.d directory.\n")
                elif platform.system() == "Windows":
                    log.error(
                        "You may need to experiment with the Zadig driver to access the device.\n"
                    )
                sys.exit(1)

    @classmethod
    def active_configuration(cls) -> usb1.USBConfiguration | None:
        device = cls._handle().getDevice()
        number = cls._handle().getConfiguration()
        for cfg in device:
            if cfg.getConfigurationValue() == number:
                return cfg

    @classmethod
    def device_speed(cls):
        return DeviceSpeed(cls._handle().getDevice().getDeviceSpeed())

    @classmethod
    def controlRead(cls, request_type, request, value, index, length, timeout=1000):
        return cls._handle().controlRead(
            request_type, request, value, index, length, timeout
        )

    @classmethod
    def controlWrite(cls, request_type, request, value, index, data, timeout=1000):
        return cls._handle().controlWrite(
            request_type, request, value, index, data, timeout
        )

    @classmethod
    def read(cls, endpoint_number, length, timeout=1000):
        # Avoid accidental uses of endpoint address
        endpoint_number = endpoint_number & 0x7F

        # TODO support interrupt endpoints
        return cls._handle().bulkRead(endpoint_number, length, timeout)

    @classmethod
    def write(cls, endpoint_number, data, timeout=1000):
        # TODO support interrupt endpoints
        return cls._handle().bulkWrite(endpoint_number, data, timeout)

    @classmethod
    def clear_halt(cls, endpoint_number, direction):
        endpoint_address = direction.to_endpoint_address(endpoint_number)
        return cls._handle().clearHalt(endpoint_address)

    @classmethod
    def reset(cls):
        log.info("LibUSB1Device reset")
        cls._handle().resetDevice()
        cls._claim()


if __name__ == "__main__":
    from .filters.standard import USBProxySetupFilters
    from .filters.logging import USBProxyPrettyPrintFilter

    # akai midimix
    VENDOR_ID = 0x09E8
    PRODUCT_ID = 0x0031

    # xbox controller
    # VENDOR_ID  = 0x045e
    # PRODUCT_ID = 0x02d1

    device = USBProxyDevice(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)

    device.add_filter(USBProxySetupFilters(device, verbose=2))
    device.add_filter(USBProxyPrettyPrintFilter(verbose=5))

    async def configure_logging():
        import logging

        logging.getLogger("facedancer").setLevel(logging.INFO)

    from facedancer import main

    main(device, configure_logging())
