"""
Raw Gadget-based Facedancer backend.

See https://github.com/xairy/raw-gadget for details about Raw Gadget.

Authors:
- Andrey Konovalov <andreyknvl@gmail.com>
- Kirill Zhirovsky <me@kirill9617.win>
- Devin Bayer <dev@doubly.so>
"""

# Allow using forward type references in Python 3.10+.
from __future__ import annotations

import fcntl
import os
import time

from dataclasses import dataclass
from signal import signal, SIGUSR1, pthread_kill
from threading import Thread, Event
from queue import Queue, Empty

from construct import (
    Bit,
    BitStruct,
    BitsSwapped,
    Bytes,
    Enum,
    Int16ul,
    Int16un,
    Int32un,
    Int8ul,
    Int8un,
    Padding,
    PaddedString,
    Struct,
    this,
)

from ..core import FacedancerApp
from ..device import USBDevice
from ..configuration import USBConfiguration
from ..endpoint import USBEndpoint
from ..request import USBControlRequest
from ..types import (
    DeviceSpeed,
    USBDirection,
    USBRequestRecipient,
    USBStandardRequests,
)
from ..logging import log
from .base import FacedancerBackend


class RawGadgetBackend(FacedancerApp, FacedancerBackend):
    """
    Backend for the Linux-based boards that support Raw Gadget.
    """

    app_name = "Raw Gadget"

    device: RawGadget
    event_queue: Queue
    control: ControlHandler
    eps: dict[int, EndpointHandler]  # address -> handler
    connected_device: USBDevice
    configuration: USBConfiguration

    def __init__(
        self,
        device: RawGadget | None = None,
        verbose: int = 0,
        quirks=None,
    ):
        """
        Initializes the Raw Gadget backend.

        Args:
            device  : The Raw Gadget device that will act as our Facedancer. (Optional)
            verbose : The verbosity level of the given application. (Optional)
            quirks  : Unused.
        """
        super().__init__(device or RawGadget(), verbose)

        self.event_queue = Queue(100)
        self.control = None
        self.eps = {}

        self.connected_device = None
        self.configuration = None

        # These are kept track of but are not used by the backend yet.
        self.eps_info = None
        self.is_suspended = False

        self.device.open()

    @classmethod
    def appropriate_for_environment(cls, backend_name: str | None) -> bool:
        """
        Determines if the current environment seems appropriate
        for using the Raw Gadget backend.

        Args:
            backend_name : Backend name being requested. (Optional)
        """
        if backend_name and backend_name != "rawgadget":
            return False

        try:
            rg = open("/dev/raw-gadget")
        except Exception as e:
            log.info(f"Skipping Raw Gadget, as could not open /dev/raw-gadget: {e}.")
            return False

        rg.close()
        return True

    def get_version(self):
        raise NotImplementedError

    def requires_packetizing(self):
        """
        Tells whether the backend requires the data to be split into chunks
        of max packet size when sending this data on an endpoint.

        Returns False, as Raw Gadget packetizes data internally.
        """
        return False

    def connect(
        self,
        usb_device: USBDevice,
        max_packet_size_ep0: int = 64,
        device_speed: DeviceSpeed = DeviceSpeed.FULL,
    ):
        """
        Prepares the backend to connect to the target host and emulate a given device.

        Args:
            usb_device : The USBDevice object that represents the emulated device.
            max_packet_size_ep0 : Unused.
            device_speed : Requested USB speed for the emulated device.
        """
        log.info("connecting device: %s (%r)", usb_device.name, device_speed)

        # Set a no-op handler for SIGUSR1. Sending this signal to the threads
        # that handle enpoints will thus allows interrupting blocking Raw Gadget
        # ioctl calls without other side-effects.
        self._original_signal_handler = signal(SIGUSR1, self._ignore_signal)

        self.connected_device = usb_device

        if speed_override := int(os.environ.get("RG_USB_SPEED", 0)):
            device_speed = DeviceSpeed(speed_override)
            log.info(f"overriding device speed with %r", device_speed)

        self.device.init_and_run(
            udc_driver=os.environ.get("RG_UDC_DRIVER", "dummy_udc").lower(),
            udc_device=os.environ.get("RG_UDC_DEVICE", "dummy_udc.0").lower(),
            speed=device_speed,
        )

        self.control = ControlHandler(self)

    def disconnect(self):
        """Disconnects Raw Gadget from the target host."""

        assert self.connected_device

        self._disable_endpoints()
        self.control.stop()
        self.device.close()

        # Restore the original SIGUSR1 handler.
        signal(SIGUSR1, self._original_signal_handler)

        log.info("disconnected device: %s", self.connected_device.name)

        self.connected_device = None

    def reset(self):
        """
        Supposed to make the backend handle its side of a bus reset.

        Does nothing, as Raw Gadget handles resets internally.
        """
        pass

    def set_address(self, address: int, defer: bool = False):
        """
        Supposed to be called when the device address is being set.

        Not implemented for the Raw Gadget backend, as it cannot receive
        a SET_ADDRESS request: this request is handled by the UDC driver.
        """
        raise NotImplementedError

    def configured(self, configuration):
        """
        Callback that's issued when a USBDevice is configured, e.g. by the
        SET_CONFIGURATION request. Allows the backend to apply the new configuration.

        Args:
            configuration : The USBConfiguration object applied by the SET_CONFIG request.
        """
        # TODO: Confirm that this handler is called before SET_CONFIGURATION request is acked.
        # TODO: Handle configuration == None.

        log.info("applying configuration #%d", configuration.number)

        self.validate_configuration(configuration)

        self._disable_endpoints()

        self.device.vbus_draw(configuration.max_power // 2)
        self.device.configure()

        self.configuration = configuration

        self._enable_endpoints()

    def read_from_endpoint(self, endpoint_number: int) -> bytes:
        """
        Supposed to make the backend read data from the given endpoint.

        Not used with Raw Gadget, as endpoints are read internally.
        """
        raise NotImplementedError

    def send_on_control_endpoint(self, endpoint_number: int, in_request: USBControlRequest, data: bytes, blocking: bool=True):
        """
        Used to send data in response to an IN control request
        and for acknowledging both IN and OUT control requests.

        Args:
            endpoint_number  : The number of the endpoint on which data should be sent.
            in_request       : The control request being responded to.
            data             : The data to be sent.
            blocking         : If true, this function should wait for the transfer to complete.
        """
        log.trace(f"send_on_control_endpoint: {endpoint_number=} len={len(data)} {blocking=}")

        assert endpoint_number == 0, "control requests only supported for ep 0"

        if in_request.direction == USBDirection.OUT:
            if not self.unacked_request:
                log.debug("ignoring send_on_endpoint for already acked OUT request")
                return

            assert not data, "cannot send data for OUT request"
            self.control.read(0)
        else:
            self.control.send(data)

        if self.unacked_request is in_request:
            self.unacked_request = None

    def send_on_endpoint(
        self, endpoint_number: int, data: bytes, blocking: bool = True
    ):
        """
        Sends data on a given IN endpoint.

        Args:
            endpoint_number : The number of the IN endpoint on which data should be sent.
            data : The data to be sent.
            blocking : Wait for sending. Must be true for control.
        """
        log.trace(f"send_on_endpoint: {endpoint_number=} len={len(data)} {blocking=}")

        if not isinstance(data, (bytes, bytearray)):
            raise TypeError(f"{type(data)=}, must be bytes")
        assert endpoint_number != 0, "send_on_endpoint called for control endpoint"

        address = USBEndpoint.address_for_number(endpoint_number, USBDirection.IN)
        handler = self.eps[address]
        assert isinstance(handler, EndpointInHandler)
        handler.send(data, blocking)

    def ack_status_stage(
        self,
        direction: USBDirection = USBDirection.OUT,
        endpoint_number: int = 0,
        blocking: bool = False,
    ):
        """
        Supposed to be used to acknowledge control requests. But only called
        by the proxy and only for OUT requests; other requests are acknowledged
        via send_on_control_endpoint.

        Args:
            direction : Determines if we're ACK'ing an IN or OUT vendor request.
                        (This should match the direction of the DATA stage.)
            endpoint_number : The endpoint number on which the control request
                              occurred.
            blocking : True if we should wait for the ACK to be fully issued
                       before returning.
        """
        log.trace(f"ack_status_stage: {endpoint_number=} direction={direction.name} {blocking=}")

        if not self.unacked_request:
            log.debug("ignoring ack_status_stage for already acked OUT request")
            return

        assert direction == USBDirection.OUT
        self.send_on_control_endpoint(0, self.unacked_request, b"", blocking)

    def stall_endpoint(
        self, endpoint_number: int, direction: USBDirection = USBDirection.OUT
    ):
        """
        Stalls the provided endpoint.

        Args:
            endpoint_number : The number of the endpoint to be stalled.
        """
        log.trace(f"stall_endpoint: {endpoint_number=} direction={direction.name}")

        if endpoint_number == 0:
            log.trace("ep0: stalling")
            self.device.ep0_stall()
        else:
            # Raw Gadget does support stalling non-control endpoints, but none
            # of the Facedancer examples do this. Thus, testing this feature is
            # hard, so leave this as not implemented.
            raise NotImplementedError

    def service_irqs(self):
        """
        Core event loop. Reacts to events recevied via Raw Gadget from the host.
        """
        try:
            event = self.event_queue.get_nowait()
        except Empty:
            # No events, yield to other threads.
            time.sleep(0)
            return
        match event:
            case RawGadgetEvent(kind, data):
                log.trace(f"received event: {kind} len={len(data)}")
                self._handle_event(kind, data)
            case EpReadEvent(handler, data):
                log.trace(f"received read event: len={len(data)}")
                if handler.stopped.is_set():
                    log.debug(f"discarding read event: handler stopped")
                    return
                self.connected_device.handle_data_received(handler.ep, data)
            case _:
                assert False

    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
    # Internal functions
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    def _handle_event(self, kind, data):
        match kind:
            case usb_raw_event_type.USB_RAW_EVENT_CONNECT:
                # UDC endpoint information is only obtained for reference:
                # this backend does use it in any way. In the future, this
                # backend can be extended to validate UDC endpoints
                # capabilities against the device endpoint descriptors.
                self.eps_info = self.device.eps_info()
                log.info("gadget connected")
            case usb_raw_event_type.USB_RAW_EVENT_CONTROL:
                self._handle_control_event(data)
            case usb_raw_event_type.USB_RAW_EVENT_DISCONNECT:
                # Some UDC drivers (e.g. dwc2) issue a disconnect event when the
                # device is being reconfigured. Thus, treat disconnect as reset.
                log.info("gadget reset (disconnected)")
                self._handle_reset_event()
            case usb_raw_event_type.USB_RAW_EVENT_SUSPEND:
                # TODO: Handle suspend/resume.
                log.info("gadget suspended")
                self.is_suspended = True
            case usb_raw_event_type.USB_RAW_EVENT_RESET:
                log.info("gadget reset")
                self._handle_reset_event()
            case usb_raw_event_type.USB_RAW_EVENT_RESUME:
                self.is_suspended = False
                log.info("gadget resumed")
            case _:
                # Raw Gadget might be extended and start reporting other kinds
                # of events. Instead of ignoring these events, raise an
                # exception to hint that this backend must be extended as well.
                raise NotImplementedError

    def _handle_control_event(self, req_header: bytes):
        req: USBControlRequest = self.connected_device.create_request(req_header)
        log.debug(f"received control request: {req}")

        if req.direction == USBDirection.OUT and req.length > 0:
            rv, data = self.control.read(req.length)
            assert data and rv == req.length
            req.data = bytes(data)
            log.debug(f"  data: {data.hex(' ', -2)}")
            # The Linux USB Gadget subsystem automatically acks non-0-length
            # OUT control requests when the data is read.
            self.unacked_request = None
        else:
            # But 0-length OUT control requests require explicit ack.
            # Done later either via ack_status_stage() or send_on_control_endpoint().
            self.unacked_request = req

        reenable = False
        if (
            req.get_recipient() == USBRequestRecipient.INTERFACE
            and req.request == USBStandardRequests.SET_INTERFACE
        ):
            log.info(f"changing interface #{req.index} altsetting to #{req.value}")
            reenable = True

        # TODO: Only reenable endpoints for the interface whose altsetting is being changed.
        if reenable:
            self._disable_endpoints()

        self.connected_device.handle_request(req)

        if reenable:
            self._enable_endpoints()

    def _handle_reset_event(self):
        self.configuration = None
        self._disable_endpoints()

        if self.connected_device:
            self.connected_device.handle_bus_reset()

    def _enable_endpoints(self):
        if not self.configuration:
            return

        for interface in self.configuration.active_interfaces.values():
            for ep in interface.get_endpoints():
                if ep.direction == USBDirection.IN:
                    self.eps[ep.address] = EndpointInHandler(ep, self)
                else:
                    self.eps[ep.address] = EndpointOutHandler(ep, self)

                self.eps[ep.address].start()

    def _disable_endpoints(self):
        for ep in self.eps.values():
            ep.stop()

        self.eps = {}

    def _ignore_signal(self, signum, _frame):
        log.debug(f"ignoring signal {signum}")


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Endpoint handlers
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


@dataclass
class RawGadgetEvent:
    kind: int
    data: bytes


@dataclass
class EpReadEvent:
    handler: EndpointHandler
    data: bytes


class ControlHandler:
    """
    Handler for the Raw Gadget events, including the control requests.

    Spawns a thread for fetching Raw Gadget events, as the Raw Gadget API
    for this is blocking.
    """

    def __init__(self, backend):
        log.debug("ep0: starting handler")
        self._stopped = Event()
        self._backend = backend
        self._thread = Thread(target=self._gadget_loop, name="ep0", daemon=True)
        self._thread.start()

    def stop(self):
        log.debug("ep0: stopping handler")
        self._stopped.set()
        # Send SIGUSR1 to the thread to interrupt the possibly event_fetch().
        pthread_kill(self._thread.ident, SIGUSR1)
        self._thread.join()

    def read(self, length: int):
        log.debug(f"ep0: reading {length} bytes")
        data = self._backend.device.ep0_read(length)
        return data

    def send(self, data: bytes):
        log.debug(f"ep0: sending {len(data)} bytes")
        if len(data) > 0:
            log.trace(f"  data: {data.hex(' ', -2)}")
        self._backend.device.ep0_write(data)

    def _gadget_loop(self):
        while not self._stopped.is_set():
            try:
                event = self._backend.device.event_fetch()
            except InterruptedError:
                continue
            self._backend.event_queue.put(RawGadgetEvent(event.kind, event.data))
        log.debug("ep0: handler stopped")


class EndpointHandler:
    ep: USBEndpoint
    stopped: Event

    def __init__(self, ep, backend):
        self.ep = ep
        self.stopped = Event()
        self._backend = backend
        # Create the handler thread but don't start it yet.
        self._gadget_thread = Thread(
            target=self._gadget_loop, name=f"{self}-gadget", daemon=True
        )
        # We could validate the endpoint descriptor against the UDC endpoint
        # capabilities and the selected USB device speed. This will, however,
        # limit the ability to emulate devices that do not strictly follow the
        # USB specifications; some UDCs unofficially support this. As having
        # this ability might be useful for fuzzing, use the endpoint descriptor
        # as is. As a trade off, this might lead to unpredictable errors during
        # the device emulation.
        self._handle = self._backend.device.ep_enable(ep.get_descriptor())
        log.debug(f"{self}: enabled (handle={self._handle})")

    def __str__(self):
        assert self.ep
        return f"ep{self.ep.number:02x}/{self.ep.direction.name}"

    def _gadget_loop(self):
        # Must be implemented in the child class.
        raise NotImplementedError

    def start(self):
        log.debug(f"{self}: starting handler")
        self._gadget_thread.start()

    def stop(self):
        log.debug(f"{self}: stopping handler")
        self.stopped.set()
        # Send SIGUSR1 to the thread to interrupt a possibly blocked ioctl.
        pthread_kill(self._gadget_thread.ident, SIGUSR1)
        self._gadget_thread.join()
        self._backend.device.ep_disable(self._handle)
        log.debug(f"{self}: disabled (handle={self._handle})")


class EndpointOutHandler(EndpointHandler):
    """
    Handler for non-control OUT endpoints.

    Spawns a thread for reading data from the endpoint, as the Raw Gadget API
    for this is blocking. Passes read data to the main thread to be reported
    to the emulated device.
    """

    def _gadget_loop(self):
        while not self.stopped.is_set():
            try:
                # Fetch data from the host.
                # TODO: We should be able to use 4096 instead of max_packet_size,
                #       but this emulating some devices fail for an unknown reason.
                #       Investigate.
                data = self._backend.device.ep_read(
                    self._handle, self.ep.max_packet_size
                )
                log.debug(f"{self}: read {len(data)} bytes")
                if len(data) > 0:
                    log.trace(f"  data: {data.hex(' ', -2)}")
            except (InterruptedError, BrokenPipeError):
                # BrokenPipeError corresponds to the -ESHUTDOWN error, which
                # might be returned if the host decides to reset the device.
                continue
            # Queue data for service_irqs() to be reported to the emulated device.
            self._backend.event_queue.put(EpReadEvent(handler=self, data=data))

        log.debug(f"{self}: handler stopped")



class EndpointInHandler(EndpointHandler):
    """
    Handler for non-control IN endpoints.

    Spawns a thread to fetching data to be written from the emulated device,
    as the emulated device might be a proxy and thus block for some time.

    Spawns another thread for writing data to the endpoint, as the Raw Gadget
    API for this is blocking and the host might not read out the data right
    away (observed when running the Facedancer tests).
    """

    def start(self):
        # This queue is used to pass requested data from the device handler
        # to the gadget handler to be sent to the host.
        self._data_queue = Queue()
        # This flag indicates whether the gadget handler is idle
        # or blocked on executing a transfer.
        self._ep_idle = Event()
        self._ep_idle.set()
        # Create and start the device thread.
        self._device_thread = Thread(
            target=self._device_loop, name=f"{self}-device", daemon=True
        )
        self._device_thread.start()
        # Start the gadget thread.
        super().start()

    def stop(self):
        # Put None into the queue to unblock the gadget thread that might be
        # blocked on queue.get().
        self._data_queue.put(None)
        super().stop()
        self._device_thread.join()

    def send(self, data: bytes, blocking: bool):
        self._data_queue.put(data)
        if blocking:
            self._data_queue.join()

    def _gadget_loop(self):
        while not self.stopped.is_set():
            try:
                # Fetch data from the device thread.
                data = self._data_queue.get()
                if data is None or self.stopped.is_set():
                    break
                if len(data) == 0:
                    # In Facedancer tests, handle_data_requested() might return
                    # a 0-length transfer when called before in_transfer_length
                    # is set. Ignore this transfer.
                    continue
                # Send data to the host.
                self._ep_idle.clear()
                rv = self._backend.device.ep_write(self._handle, data)
                if rv != len(data):
                    # TODO: Investigate whether any UDC can actually only partially write the data.
                    #       If so, add a loop here to write data chunk by chunk.
                    log.warning(f"{self}: wrote only {rv} bytes instead of {len(data)}")
                else:
                    log.debug(f"{self}: wrote {rv} bytes")
                if len(data) > 0:
                    log.trace(f"  data: {data.hex(' ', -2)}")
                self._ep_idle.set()
                self._data_queue.task_done()
            except (InterruptedError, BrokenPipeError):
                # BrokenPipeError corresponds to the -ESHUTDOWN error, which
                # might be returned if the host decides to reset the device.
                self._ep_idle.clear()
                continue

        log.debug(f"{self}: gadget handler stopped")

    def _device_loop(self):
        while not self.stopped.is_set():
            # Avoid calling handle_data_requested() while ep_write() is blocked.
            if self._ep_idle.wait(timeout=self.ep.interval * 0.001):
                # Indicate to the emulated device that more data was requested.
                # This will likely make the emulated device call
                # backend.send_on_endpoint(), which will in turn call self.send().
                self._backend.connected_device.handle_data_requested(self.ep)

            # Either handle_data_requested() might have sent data on the endpoint
            # or ep_write() is blocked. Yield the execution to other threads.
            time.sleep(0)

        log.debug(f"{self}: device handler stopped")


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Raw Gadget API wrapper
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


class TrailingBytes(Bytes):
    def _sizeof(self, context, path):
        return 0


usb_endpoint_descriptor = Struct(
    "bLength" / Int8ul,
    "bDescriptorType" / Int8ul,
    "bEndpointAddress" / Int8ul,
    "bmAttributes" / Int8ul,
    "wMaxPacketSize" / Int16ul,
    "bInternal" / Int8ul,
    "bRefresh" / Int8ul,
    "bSynchAddress" / Int8ul,
)

usb_ctrlrequest = Struct(
    "bRequestType" / Int8ul,
    "bRequest" / Int8ul,
    "wValue" / Int16ul,
    "wIndex" / Int16ul,
    "wLength" / Int16ul,
)

UDC_NAME_LENGTH_MAX = 128

usb_raw_init = Struct(
    "driver_name" / PaddedString(UDC_NAME_LENGTH_MAX, "ascii"),
    "device_name" / PaddedString(UDC_NAME_LENGTH_MAX, "ascii"),
    "speed" / Int8un,
)

usb_raw_event_type = Enum(
    Int32un,
    USB_RAW_EVENT_INVALID=0,
    USB_RAW_EVENT_CONNECT=1,
    USB_RAW_EVENT_CONTROL=2,
    USB_RAW_EVENT_SUSPEND=3,
    USB_RAW_EVENT_RESUME=4,
    USB_RAW_EVENT_RESET=5,
    USB_RAW_EVENT_DISCONNECT=6,
)

usb_raw_event = Struct(
    "kind" / usb_raw_event_type,
    "length" / Int32un,
    "data" / TrailingBytes(this.length)
)

usb_raw_ep_io = Struct(
    "ep" / Int16un,
    "flags" / Int16un,
    "length" / Int32un,
    "data" / TrailingBytes(this.length),
)

usb_raw_ep_caps = BitsSwapped(
    BitStruct(
        "type_control" / Bit,
        "type_iso" / Bit,
        "type_bulk" / Bit,
        "type_int" / Bit,
        "dir_in" / Bit,
        "dir_out" / Bit,
        Padding(26),
    )
)

usb_raw_ep_limits = Struct(
    "maxpacket_limit" / Int16un, "max_streams" / Int16un, "reserved" / Int32un
)

USB_RAW_EPS_NUM_MAX = 30
USB_RAW_EP_NAME_MAX = 16

usb_raw_ep_info = Struct(
    "name" / PaddedString(USB_RAW_EP_NAME_MAX, "ascii"),
    "addr" / Int32un,
    "caps" / usb_raw_ep_caps,
    "limits" / usb_raw_ep_limits,
)

usb_raw_eps_info = Struct("eps" / usb_raw_ep_info[USB_RAW_EPS_NUM_MAX])


class IOCTLRequest:
    IOC_NONE = 0
    IOC_WRITE = 1
    IOC_READ = 2

    IOC_NRBITS = 8
    IOC_TYPEBITS = 8
    IOC_SIZEBITS = 14
    IOC_DIRBITS = 2

    IOC_NRSHIFT = 0
    IOC_TYPESHIFT = IOC_NRSHIFT + IOC_NRBITS
    IOC_SIZESHIFT = IOC_TYPESHIFT + IOC_TYPEBITS
    IOC_DIRSHIFT = IOC_SIZESHIFT + IOC_SIZEBITS

    @staticmethod
    def IOC(dir, typ, nr, size):
        if size is None:
            size = 0
        else:
            size = size.sizeof()
        if isinstance(typ, str):
            typ = ord(typ[0])
        if isinstance(dir, str):
            dir = {
                "": IOCTLRequest.IOC_NONE,
                "R": IOCTLRequest.IOC_READ,
                "W": IOCTLRequest.IOC_WRITE,
                "WR": IOCTLRequest.IOC_WRITE | IOCTLRequest.IOC_READ,
            }[dir]
        return (
            dir << IOCTLRequest.IOC_DIRSHIFT
            | typ << IOCTLRequest.IOC_TYPESHIFT
            | nr << IOCTLRequest.IOC_NRSHIFT
            | size << IOCTLRequest.IOC_SIZESHIFT
        )

    @staticmethod
    def ioc(dir, typ, nr, size):
        def fn(fd, arg=0):
            req = IOCTLRequest.IOC(dir, typ, nr, size)
            if isinstance(arg, bytes):
                arg = bytearray(arg)
            rv = fcntl.ioctl(fd, req, arg, True)
            return rv, arg

        return fn


class RawGadgetRequests(IOCTLRequest):
    USB_RAW_IOCTL_INIT = IOCTLRequest.ioc("W", "U", 0, usb_raw_init)
    USB_RAW_IOCTL_RUN = IOCTLRequest.ioc("", "U", 1, None)
    USB_RAW_IOCTL_EVENT_FETCH = IOCTLRequest.ioc("R", "U", 2, usb_raw_event)
    USB_RAW_IOCTL_EP0_WRITE = IOCTLRequest.ioc("W", "U", 3, usb_raw_ep_io)
    USB_RAW_IOCTL_EP0_READ = IOCTLRequest.ioc("WR", "U", 4, usb_raw_ep_io)
    USB_RAW_IOCTL_EP_ENABLE = IOCTLRequest.ioc("W", "U", 5, usb_endpoint_descriptor)
    USB_RAW_IOCTL_EP_DISABLE = IOCTLRequest.ioc("W", "U", 6, Int32un)
    USB_RAW_IOCTL_EP_WRITE = IOCTLRequest.ioc("W", "U", 7, usb_raw_ep_io)
    USB_RAW_IOCTL_EP_READ = IOCTLRequest.ioc("WR", "U", 8, usb_raw_ep_io)
    USB_RAW_IOCTL_CONFIGURE = IOCTLRequest.ioc("", "U", 9, None)
    USB_RAW_IOCTL_VBUS_DRAW = IOCTLRequest.ioc("W", "U", 10, Int32un)
    USB_RAW_IOCTL_EPS_INFO = IOCTLRequest.ioc("R", "U", 11, usb_raw_eps_info)
    USB_RAW_IOCTL_EP0_STALL = IOCTLRequest.ioc("", "U", 12, None)
    USB_RAW_IOCTL_EP_SET_HALT = IOCTLRequest.ioc("W", "U", 13, Int32un)
    USB_RAW_IOCTL_EP_CLEAR_HALT = IOCTLRequest.ioc("W", "U", 14, Int32un)
    USB_RAW_IOCTL_EP_SET_WEDGE = IOCTLRequest.ioc("W", "U", 15, Int32un)


class RawGadget:
    def __init__(self):
        self.fd = None

    def open(self):
        self.fd = open("/dev/raw-gadget", "bw")

    def close(self):
        assert self.fd is not None
        self.fd.close()
        self.fd = None

    def init_and_run(self, udc_driver, udc_device, speed: DeviceSpeed):
        arg = usb_raw_init.build(
            {"driver_name": udc_driver, "device_name": udc_device, "speed": speed}
        )
        RawGadgetRequests.USB_RAW_IOCTL_INIT(self.fd, arg)
        RawGadgetRequests.USB_RAW_IOCTL_RUN(self.fd)

    def event_fetch(self):
        length = usb_ctrlrequest.sizeof()
        arg = usb_raw_event.build(
            {"kind": 0, "length": length, "data": bytes(length)}
        )
        _, data = RawGadgetRequests.USB_RAW_IOCTL_EVENT_FETCH(self.fd, arg)
        return usb_raw_event.parse(data)

    def ep0_write(self, data, flags=0):
        arg = usb_raw_ep_io.build(
            {"ep": 0, "flags": flags, "length": len(data), "data": data}
        )
        RawGadgetRequests.USB_RAW_IOCTL_EP0_WRITE(self.fd, arg)

    def ep0_read(self, length, flags=0):
        arg = usb_raw_ep_io.build(
            {"ep": 0, "flags": flags, "length": length, "data": bytes(length)}
        )
        rv, data = RawGadgetRequests.USB_RAW_IOCTL_EP0_READ(self.fd, arg)
        return rv, usb_raw_ep_io.parse(data).data[:rv]

    def ep_enable(self, ep_desc):
        handle, _ = RawGadgetRequests.USB_RAW_IOCTL_EP_ENABLE(self.fd, ep_desc)
        return handle

    def ep_disable(self, handle):
        RawGadgetRequests.USB_RAW_IOCTL_EP_DISABLE(self.fd, handle)

    def ep_write(self, handle, data, flags=0):
        arg = usb_raw_ep_io.build(
            {"ep": handle, "flags": flags, "length": len(data), "data": data}
        )
        rv, _ = RawGadgetRequests.USB_RAW_IOCTL_EP_WRITE(self.fd, arg)
        return rv

    def ep_read(self, handle, length, flags=0):
        arg = usb_raw_ep_io.build(
            {"ep": handle, "flags": flags, "length": length, "data": bytes(length)}
        )
        rv, data = RawGadgetRequests.USB_RAW_IOCTL_EP_READ(self.fd, arg)
        return usb_raw_ep_io.parse(data).data[:rv]

    def configure(self):
        RawGadgetRequests.USB_RAW_IOCTL_CONFIGURE(self.fd)

    def vbus_draw(self, power):
        RawGadgetRequests.USB_RAW_IOCTL_VBUS_DRAW(self.fd, power)

    def eps_info(self):
        eps_info = bytes(usb_raw_eps_info.sizeof())
        num, resp = RawGadgetRequests.USB_RAW_IOCTL_EPS_INFO(self.fd, eps_info)
        return usb_raw_eps_info.parse(resp)

    def ep0_stall(self):
        RawGadgetRequests.USB_RAW_IOCTL_EP0_STALL(self.fd)
