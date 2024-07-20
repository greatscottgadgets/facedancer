"""
Backend for the Hydradancer boards.

Supports 5 endpoints, with addresses between 0 and 7. Supports low, full and high-speed.
"""

import sys
import logging
import time
from array import array
from time import time_ns
from dataclasses import dataclass
from typing import List, Dict, Any

import usb
from usb.util import CTRL_TYPE_VENDOR, CTRL_RECIPIENT_DEVICE, CTRL_IN, CTRL_OUT

from ..core           import *
from ..device         import USBDevice, USBConfiguration, USBDirection, USBEndpoint
from ..types          import DeviceSpeed
from ..logging        import log
from .base            import FacedancerBackend


@dataclass
class HydradancerEvent:
    # Events
    EVENT_BUS_RESET = 0x0
    EVENT_IN_BUFFER_AVAILABLE = 0x1
    EVENT_OUT_BUFFER_AVAILABLE = 0x2
    EVENT_NAK = 0x3

    event_type : int = -1
    value : int = -1

    @staticmethod
    def from_bytes(data : bytes):
        return HydradancerEvent(event_type = data[0], value = data[1])

    def __repr__(self):
        return f"event_type {self.event_type} value {self.value}"


class HydradancerHostApp(FacedancerApp, FacedancerBackend):
    """
    Backend for the HydraUSB3 boards.
    """
    app_name = "Hydradancer Host"

    MANUFACTURER_STRING = "Quarkslab https://www.quarkslab.com/ & HydraBus https://hydrabus.com/"

    # USB directions
    HOST_TO_DEVICE = 0
    DEVICE_TO_HOST = 1

    USB2_MAX_EP_IN = 16

    current_setup_req = None

    def __init__(self, device: USBDevice=None, verbose: int=0, quirks: List[str]=[]):
        """
        Initializes the backend.

        Args:
            device  :  The device that will act as our Facedancer.   (Optional)
            verbose : The verbosity level of the given application. (Optional)
            quirks  :  List of USB platform quirks.                  (Optional)
        """
        super().__init__(self)

        self.configuration = None
        self.pending_control_out_request = None
        self.connected_device = None
        self.max_ep0_packet_size = None

        self.ep_transfer_queue : List[List[Any]] = [[]] * self.USB2_MAX_EP_IN

        self.ep_in : Dict[int, USBEndpoint] = {}
        self.ep_out : Dict[int, USBEndpoint] = {}

        self.api = HydradancerBoard()
        self.verbose = verbose
        self.api.wait_board_ready()

    @classmethod
    def appropriate_for_environment(cls, backend_name: str) -> bool:
        """
        Determines if the current environment seems appropriate
        for using this backend.

        Args:
            backend_name : Backend name being requested. (Optional)
        """

        logging.info("this is hydradancer hi")
        # Open a connection to the target device...
        device = usb.core.find(idVendor=0x16c0, idProduct=0x27d8)

        if device is not None and device.manufacturer == cls.MANUFACTURER_STRING and backend_name == "hydradancer":
            return True

        return False

    def get_version(self):
        """
        Returns information about the active Facedancer version.
        """
        raise NotImplementedError

    def connect(self, usb_device: USBDevice, max_packet_size_ep0: int=64, device_speed: DeviceSpeed=DeviceSpeed.FULL):
        """
        Prepares backend to connect to the target host and emulate
        a given device.

        Args:
            usb_device : The USBDevice object that represents the emulated device.
            max_packet_size_ep0 : Max packet size for control endpoint.
            device_speed : Requested usb speed for the Facedancer board.
        """
        self.api.set_endpoint_mapping(0)

        if device_speed not in [DeviceSpeed.LOW, DeviceSpeed.FULL, DeviceSpeed.HIGH]:
            log.warning(f"Hydradancer only supports USB Low, Full and High Speed. Ignoring requested speed: {device_speed.name}")

        self.api.set_usb2_speed(device_speed)
        logging.info("connect ...")

        self.api.connect()

        self.connected_device = usb_device

        self.max_ep0_packet_size = max_packet_size_ep0

    def disconnect(self):
        """ Disconnects Facedancer from the target host. """
        logging.info("disconnect")
        self.configuration = None
        self.pending_control_out_request = None
        self.connected_device = None
        self.max_ep0_packet_size = 0
        self.ep_transfer_queue = [[]] * self.USB2_MAX_EP_IN
        self.api.disconnect()

    def reset(self):
        """
        Triggers the Facedancer to handle its side of a bus reset.
        """
        logging.info("bus reset")

    def set_address(self, address: int, defer: bool=False):
        """
        Sets the device address of the Facedancer. Usually only used during
        initial configuration.

        Args:
            address : The address the Facedancer should assume.
            defer   : True iff the set_address request should wait for an active transaction to
                      finish.
        """
        logging.info("set address")
        self.api.set_address(address, defer)

    def configured(self, configuration: USBConfiguration):
        """
        Callback that's issued when a USBDevice is configured, e.g. by the
        SET_CONFIGURATION request. Allows us to apply the new configuration.

        Args:
            configuration : The USBConfiguration object applied by the SET_CONFIG request.
        """

        if configuration is None:
            self.configuration = None
            self.api.configured = False
            logging.debug("unconfigured")
            return

        self.api.reinit(keep_ep0=True)
        endpoint_numbers = []

        for interface in configuration.get_interfaces():
            for endpoint in interface.get_endpoints():
                ep_num = endpoint.number
                is_ep_in = endpoint.direction == 1
                if ep_num not in endpoint_numbers:
                    endpoint_numbers.append(ep_num)

                if is_ep_in:
                    self.ep_in[ep_num] = endpoint
                else:
                    self.ep_out[ep_num] = endpoint

        self.api.configure(endpoint_numbers)
        self.configuration = configuration
        logging.debug("configured")

    def read_from_endpoint(self, endpoint_number: int) -> bytes:
        """
        Reads a block of data from the given endpoint.

        Args:
            endpoint_number : The number of the OUT endpoint on which data is to be rx'd.
        """
        return self.api.read(endpoint_number, blocking=True)

    def send_on_endpoint(self, endpoint_number: int, data: bytes, blocking: bool=True):
        """
        Sends a collection of USB data on a given endpoint.

        Args:
            endpoint_number : The number of the IN endpoint on which data should be sent.
            data : The data to be sent.
            blocking : If true, this function should wait for the transfer to complete.
        """
        if endpoint_number != 0 and not blocking and not self.api.in_buffer_empty(endpoint_number):
            logging.debug(f"Storing {len(data)} on ep {endpoint_number} for later")
            self.ep_transfer_queue[endpoint_number].append(data)
            return

        backup_len = len(data)
        max_packet_size = self.max_ep0_packet_size if endpoint_number == 0 else self.ep_in[endpoint_number].max_packet_size

        if not data:
            self.api.send(endpoint_number, data)

        while data:
            packet = data[0:max_packet_size]
            data = data[len(packet):]
            logging.debug(f"Sending {len(packet)} on ep {endpoint_number}")
            self.api.send(endpoint_number, packet)

        # Many things to take into account here ...
        # first, if the len we are sending is a multiple of the max_packet_size, the host will request a ZLP (otherwise, it can't know when the transfer ends)
        # however, if the endpoint is endpoint 0, the host knows the size of the transfer in advance so it might not request the ZLP
        # this could be solved by using NAKs for EP0 as well (answering by a ZLP if a NAK is received but we already sent everything)
        # however, this could add too much latency and make enumeration fail
        if endpoint_number == 0 and (backup_len % max_packet_size) == 0 and backup_len > 0 and backup_len != self.current_setup_req.length:
            logging.debug(f"Sending ZLP")
            self.api.send(endpoint_number, b"") # Sending ZLP

    def ack_status_stage(self, direction: USBDirection=USBDirection.OUT, endpoint_number:int =0, blocking: bool=False):
        """
        Handles the status stage of a correctly completed control request,
        by priming the appropriate endpoint to handle the status phase.

        Args:
            direction : Determines if we're ACK'ing an IN or OUT vendor request.
                       (This should match the direction of the DATA stage.)
            endpoint_number : The endpoint number on which the control request
                              occurred.
            blocking : True if we should wait for the ACK to be fully issued
                       before returning.
        """
        if direction == USBDirection.OUT:
            # If this was an OUT request, we'll prime the output buffer to
            # respond with the ZLP expected during the status stage.
            self.send_on_endpoint(endpoint_number, data=b"", blocking=blocking)

        else:
            # If this was an IN request, we'll need to set up a transfer descriptor
            # so the status phase can operate correctly. This effectively reads the
            # zero length packet from the STATUS phase.
            self.read_from_endpoint(endpoint_number)

    def stall_endpoint(self, endpoint_number:int, direction: USBDirection=USBDirection.OUT):
        """
        Stalls the provided endpoint, as defined in the USB spec.

        Args:
            endpoint_number : The number of the endpoint to be stalled.
        """
        in_vs_out = "IN" if direction else "OUT"
        logging.info(f"Stalling EP {endpoint_number} {in_vs_out}")

        self.api.stall_endpoint(endpoint_number, direction)         

    def service_irqs(self):
        """
        Core routine of the Facedancer execution/event loop. Continuously monitors the
        Facedancer's execution status, and reacts as events occur.
        """
        events = self.api.fetch_events()

        if events is not None:
            for event in events:
                if event is None:
                    continue
                if event.event_type == HydradancerEvent.EVENT_BUS_RESET:
                    self.handle_bus_reset()
                if event.event_type == HydradancerEvent.EVENT_IN_BUFFER_AVAILABLE and event.value != 0 and (event.value in self.ep_in.keys()):
                    self.connected_device.handle_buffer_empty(self.ep_in[event.value])

        self.handle_control_request()
        self.handle_data_endpoints()

    def handle_bus_reset(self):
        """
        Triggers Hydradancer to perform its side of a bus reset.
        """
        if self.connected_device:
            self.connected_device.handle_bus_reset()
        else:
            self.reset()

    def handle_data_endpoints(self):
        """
        Handle IN or OUT requests on non-control endpoints.
        """

        # process ep OUT firsts, transfer is dictated by the host, if there is data available on an ep OUT,
        # it should be processed before setting new IN data
        for ep_num in self.ep_out:
            if self.api.out_buffer_available(ep_num):
                data = self.api.read(ep_num)
                if data is not None:
                    self.connected_device.handle_data_available(
                        ep_num, data.tobytes())

        for ep_num, ep in self.ep_in.items():
            if self.api.in_buffer_empty(ep_num) and self.api.nak_on_endpoint(ep_num):
                if len(self.ep_transfer_queue[ep_num]) != 0:
                    max_packet_size = ep.max_packet_size
                    packet = self.ep_transfer_queue[ep_num][0][0:max_packet_size]
                    self.ep_transfer_queue[ep_num][0] = self.ep_transfer_queue[ep_num][0][len(packet):]

                    self.api.send(ep_num, packet)

                    if len(self.ep_transfer_queue[ep_num][0]) == 0:
                        self.ep_transfer_queue[ep_num].pop(0)
                else:
                    self.connected_device.handle_nak(ep_num)

    def handle_control_request(self):
        if not self.api.control_buffer_available():
            return

        data = self.api.read(0)
        if data is None:
            return

        logging.debug(
            f"CONTROL EP/OUT: -> size {len(data)} {bytes(data)}")

        #  inspired from moondancer and greatdancer backends
        if self.pending_control_out_request is not None:
            self.pending_control_out_request.data.extend(data)
            all_data_received = len(
                self.pending_control_out_request.data) == self.pending_control_out_request.length
            is_short_packet = len(data) < self.max_ep0_packet_size

            if all_data_received or is_short_packet:
                self.connected_device.handle_request(
                    self.pending_control_out_request)
                self.pending_control_out_request = None
        elif len(data) > 0:
            request = self.connected_device.create_request(data)
            is_out = request.get_direction() == self.HOST_TO_DEVICE
            has_data = (request.length > 0)

            self.current_setup_req = request

            if is_out and has_data:
                logging.debug("queuing Control OUT req, waiting for more data")
                self.pending_control_out_request = request
                return

            self.connected_device.handle_request(request)

        # handle status stage of IN transfer
        elif len(data) == 0:
            logging.debug("Received ACK for IN Ctrl req")




class HydradancerBoardFatalError(Exception):
    pass


class HydradancerBoard():
    """
    Handles the communication with the Hydradancer control board and manages the events it sends.
    """
    MAX_PACKET_SIZE = 1024

    # USB Vendor Requests codes
    ENABLE_USB_CONNECTION = 50
    SET_ADDRESS = 51
    GET_EVENT = 52
    SET_ENDPOINT_MAPPING = 53
    DISABLE_USB = 54
    SET_SPEED = 55
    SET_EP_RESPONSE = 56
    CHECK_HYDRADANCER_READY = 57
    DO_BUS_RESET = 58
    CONFIGURED = 59

    # Facedancer USB2 speed to Hydradancer USB2 speed
    facedancer_to_hydradancer_speed = {
        DeviceSpeed.LOW : 0,
        DeviceSpeed.FULL : 1,
        DeviceSpeed.HIGH : 2
    }
    
    # Max number of events that can be sent by the board
    # This must not be less than what is defined in the firmware
    EVENT_QUEUE_SIZE = 100

    # Endpoint states on the emulation board
    ENDP_STATE_ACK = 0x00
    ENDP_STATE_NAK = 0x02
    ENDP_STATE_STALL = 0x03

    # USB endpoints direction
    HOST_TO_DEVICE = 0
    DEVICE_TO_HOST = 1

    EP_POLL_NUMBER = 1
    SUPPORTED_EP_NUM = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    INCOMPATIBLE_EP = [[], [9], [10], [11], [8, 12], [13], [14], [15], [4], [1], [2], [3], [4], [5], [6], [7]]

    timeout_ms_poll = 1

    def reinit(self, keep_ep0:bool = False):
        if keep_ep0 and 0 in self.endpoints_mapping:
            old_control_ep = self.endpoints_mapping[0]
            self.endpoints_mapping = {0: self.endpoints_mapping[0]}
            self.reverse_endpoints_mapping = {old_control_ep:0}
        else:
            self.endpoints_mapping = {}  # emulated endpoint -> control board endpoint
            self.reverse_endpoints_mapping = {}  # control_board_endpoint -> emulated_endpoint

        self.events = array('B', [0] * 2 * self.EVENT_QUEUE_SIZE)
        # True when SET_CONFIGURATION has been received and the Hydradancer boards are configured
        self.configured = False
        # 0x00ff (IN status mask, 1 = emulated ep ready for priming), 0xff00 (OUT mask, data received on emulated ep)
        self._hydradancer_status_bytes = array('B', [0] * 4)
        self.hydradancer_status = {}
        self.hydradancer_status["ep_in_status"] = (1 << 0) & 0xff
        self.hydradancer_status["ep_out_status"] = 0x00
        self.hydradancer_status["ep_in_nak"] = 0x00
        

    def __init__(self):
        """
        Get handles on the USB control board, and wait for Hydradancer to be ready
        """
        self.configured = False
        self.endpoints_mapping : Dict[int,int] = {}

        self.reinit()

        # Open a connection to the target device...
        self.device = usb.core.find(idVendor=0x16c0, idProduct=0x27d8)

        if self.device is None:
            raise HydradancerBoardFatalError("Hydradancer board not found")

        if self.device.speed != usb.util.SPEED_SUPER:
            raise HydradancerBoardFatalError(
                "Hydradancer not detected as USB3 Superspeed")

        cfg = self.device.get_active_configuration()
        intf = cfg[(0, 0)]

        # Detach the device from any kernel driver
        for intf in cfg:
            if self.device.is_kernel_driver_active(intf.bInterfaceNumber):
                try:
                    self.device.detach_kernel_driver(intf.bInterfaceNumber)
                except usb.core.USBError as e:
                    sys.exit("Could not detach kernel driver from interface({0}): {1}".format(
                        intf.bInterfaceNumber, str(e)))

        # store the different endpoints handles we need
        self.ep_in = list(usb.util.find_descriptor(
            intf,
            find_all=True,
            custom_match=lambda e:
            usb.util.endpoint_direction(e.bEndpointAddress) ==
            usb.util.ENDPOINT_IN and usb.util.endpoint_address(e.bEndpointAddress) !=
            self.EP_POLL_NUMBER))

        self.ep_in = {usb.util.endpoint_address(
            e.bEndpointAddress): e for e in self.ep_in}

        self.ep_out = list(usb.util.find_descriptor(
            intf,
            find_all=True,
            custom_match=lambda e:
            usb.util.endpoint_direction(e.bEndpointAddress) ==
            usb.util.ENDPOINT_OUT and usb.util.endpoint_address(e.bEndpointAddress) !=
            self.EP_POLL_NUMBER))

        self.ep_out = {usb.util.endpoint_address(
            ep.bEndpointAddress): ep for ep in self.ep_out}

        # the endpoint on which status information is received
        self.ep_poll = usb.util.find_descriptor(
            intf,
            custom_match=lambda e:
            usb.util.endpoint_direction(e.bEndpointAddress) ==
            usb.util.ENDPOINT_IN and usb.util.endpoint_address(e.bEndpointAddress) ==
            self.EP_POLL_NUMBER)

        if len(self.ep_in.keys()) == 0 and len(self.ep_out.keys()) == 0:
            logging.info("Dumping device configuration \r\n" + str(cfg))
            raise HydradancerBoardFatalError(
                "Could not fetch Hydradancer IN and OUT endpoints list")
        if len(self.ep_in.keys()) == 0:
            logging.info("Dumping device configuration \r\n" + str(cfg))
            raise HydradancerBoardFatalError(
                "Could not fetch Hydradancer IN endpoints list")
        if len(self.ep_out.keys()) == 0:
            logging.info("Dumping device configuration \r\n" + str(cfg))
            raise HydradancerBoardFatalError(
                "Could not fetch Hydradancer OUT endpoints list")
        if self.ep_out.keys() != self.ep_in.keys():
            logging.info("Dumping device configuration \r\n" + str(cfg))
            raise HydradancerBoardFatalError(
                f"Hydradancer IN/OUT endpoints pair incomplete \r\nep_in {self.ep_in} \r\nep_out {self.ep_out}")
        if self.ep_poll is None:
            logging.info("Dumping device configuration \r\n" + str(cfg))
            raise HydradancerBoardFatalError(
                f"Could not get handle on Hydradancer events endpoint (EP {self.EP_POLL_NUMBER})")

        self.endpoints_pool = set(self.ep_in.keys())

        # wait until the board is ready, for instance if a disconnect was previously issued
        self.wait_board_ready()

    def connect(self):
        """
        Enable the USB2 connection on the emulation board
        """
        try:
            self.device.ctrl_transfer(
                CTRL_TYPE_VENDOR | CTRL_RECIPIENT_DEVICE | CTRL_OUT, self.ENABLE_USB_CONNECTION)
        except (usb.core.USBTimeoutError, usb.core.USBError) as exception:
            logging.error(exception)
            raise HydradancerBoardFatalError("Error, unable to connect") from exception

    def disconnect(self):
        """
        Disable the USB2 connection on the emulation board,
        and reset internal states on both control and emulation boards.
        """
        try:
            self.device.ctrl_transfer(
                CTRL_TYPE_VENDOR | CTRL_RECIPIENT_DEVICE | CTRL_OUT, self.DISABLE_USB)
            usb.util.dispose_resources(self.device)

        except (usb.core.USBTimeoutError, usb.core.USBError) as exception:
            logging.error(exception)
            raise HydradancerBoardFatalError("Error, unable to disconnect") from exception

    def wait_board_ready(self):
        """
        Wait until the Hydradancer boards are ready, try to disconnect at some point to reset the internal states,
        hoping it will be ready next time.
        """
        #  num of checks before trying to disconnect
        max_num_status_ready_before_disconnect = 100
        count_status_ready = 0
        max_disconnect = 2
        count_disconnect = 2
        time_after_disconnect_sec = 1
        time_between_checks_sec = 0.01

        try:
            # check if the board is ready a first time
            hydradancer_ready = self.device.ctrl_transfer(
                CTRL_TYPE_VENDOR | CTRL_RECIPIENT_DEVICE | CTRL_IN, self.CHECK_HYDRADANCER_READY,
                data_or_wLength=1, timeout=5)

            # repeat max_num_status_ready_before_disconnect times
            while (hydradancer_ready is None or hydradancer_ready == 0) and count_disconnect < max_disconnect:
                count_status_ready += 1
                if count_status_ready % max_num_status_ready_before_disconnect == 0 and \
                   count_disconnect < max_disconnect:
                    logging.info(
                        "This is taking too long, disconnecting again ...")
                    self.disconnect()
                    time.sleep(time_after_disconnect_sec)
                    count_disconnect += 1
                hydradancer_ready = self.device.ctrl_transfer(
                    CTRL_TYPE_VENDOR | CTRL_RECIPIENT_DEVICE | CTRL_IN, self.CHECK_HYDRADANCER_READY,
                    data_or_wLength=1, timeout=5)
                time.sleep(time_between_checks_sec)

            # if hydradancer is still not ready
            if hydradancer_ready == 0:
                raise HydradancerBoardFatalError(
                    "Hydradancer is not ready, please reset the board")
        except (usb.core.USBTimeoutError, usb.core.USBError) as exception:
            logging.error(exception)
            raise HydradancerBoardFatalError(
                "USB Error while waiting for Hydradancer go-ahead") from exception

    def set_endpoint_mapping(self, ep_num):
        """
        Maps emulated endpoints (endpoints facing the target) to Facedancer's host endpoints (control board endpoints)
        """
        if ep_num not in self.SUPPORTED_EP_NUM:
            raise HydradancerBoardFatalError(
                f"Endpoint number {ep_num} not supported, supported numbers : {self.SUPPORTED_EP_NUM}")

        if len(self.endpoints_mapping.values()) >= len(self.endpoints_pool):
            raise HydradancerBoardFatalError(
                f"All {len(self.endpoints_pool)} endpoints are already in use (for EP0 included)")

        if ep_num not in self.endpoints_mapping:
            self.endpoints_mapping[ep_num] = list(
                self.endpoints_pool - set(self.endpoints_mapping.values()))[0]
            self.reverse_endpoints_mapping[self.endpoints_mapping[ep_num]] = ep_num

        try:
            self.device.ctrl_transfer(CTRL_TYPE_VENDOR | CTRL_RECIPIENT_DEVICE | CTRL_OUT,
                                      self.SET_ENDPOINT_MAPPING, wValue=(
                                          ep_num & 0x00ff) | ((self.endpoints_mapping[ep_num] << 8) & 0xff00))
        except (usb.core.USBTimeoutError, usb.core.USBError) as exception:
            logging.error(exception)
            raise HydradancerBoardFatalError(
                f"Could not set mapping for ep {ep_num}") from exception

    def set_usb2_speed(self, device_speed: DeviceSpeed=DeviceSpeed.FULL):
        """
        Set the speed of the USB2 device. Speed is physically determined by the host,
        so the emulation board must be configured.
        """
        try:
            self.device.ctrl_transfer(
                CTRL_TYPE_VENDOR | CTRL_RECIPIENT_DEVICE | CTRL_OUT, self.SET_SPEED, wValue=self.facedancer_to_hydradancer_speed[device_speed] & 0x00ff)
        except (usb.core.USBTimeoutError, usb.core.USBError) as exception:
            logging.error(exception)
            raise HydradancerBoardFatalError("Error, unable to set speed") from exception

    def set_address(self, address, defer=False):
        """
        Set the USB address on the emulation board
        """
        try:
            self.device.ctrl_transfer(
                CTRL_TYPE_VENDOR | CTRL_RECIPIENT_DEVICE | CTRL_OUT, self.SET_ADDRESS, address)
        except (usb.core.USBTimeoutError, usb.core.USBError) as exception:
            logging.error(exception)
            raise HydradancerBoardFatalError(
                "Error, unable to set address on emulated device") from exception

    def stall_endpoint(self, ep_num, direction=0):
        """
        Stall the ep_num endpoint on the emulation board.
        STALL will be cleared automatically after next SETUP packet received.
        """
        # Stall EP

        try:
            if ep_num == 0:
                self.device.ctrl_transfer(
                    CTRL_TYPE_VENDOR | CTRL_RECIPIENT_DEVICE | CTRL_OUT, self.SET_EP_RESPONSE, wValue=(ep_num | 0 << 7) | (self.ENDP_STATE_STALL << 8) & 0xff00)
                self.device.ctrl_transfer(
                    CTRL_TYPE_VENDOR | CTRL_RECIPIENT_DEVICE | CTRL_OUT, self.SET_EP_RESPONSE, wValue=(ep_num | 1 << 7) | (self.ENDP_STATE_STALL << 8) & 0xff00)
            else:
                self.device.ctrl_transfer(
                    CTRL_TYPE_VENDOR | CTRL_RECIPIENT_DEVICE | CTRL_OUT, self.SET_EP_RESPONSE, wValue=(ep_num | direction << 7) | (self.ENDP_STATE_STALL << 8) & 0xff00)
        except (usb.core.USBTimeoutError, usb.core.USBError) as exception:
            logging.error(exception)
            raise HydradancerBoardFatalError(f"Could not stall ep {ep_num}") from exception

    def send(self, ep_num, data):
        """
        Prime target endpoint ep_num.
        """
        try:
            while not self.in_buffer_empty(ep_num):
                events = self.fetch_events()
            logging.debug(f"Sending len {len(data)} {data} on ep {ep_num}")
            self.ep_out[self.endpoints_mapping[ep_num]].write(
                data)
            self.hydradancer_status["ep_in_status"] &= ~(0x01 << ep_num)
            self.hydradancer_status["ep_in_nak"] &= ~(0x01 << ep_num)
        except (usb.core.USBTimeoutError, usb.core.USBError):
            logging.error(f"could not send data on ep {ep_num}")

    def read(self, ep_num, blocking=False):
        """
        Read from target endpoint ep_num. If blocking=True, wait until the endpoint's buffer is full.
        """
        logging.debug(f"reading from ep {ep_num}")
        try:
            if blocking:
                while not self.out_buffer_available(ep_num):
                    self.fetch_events()
            if self.out_buffer_available(ep_num):
                read = self.ep_in[self.endpoints_mapping[ep_num]].read(
                    self.MAX_PACKET_SIZE)
                logging.debug(
                    f"EP{ep_num}/OUT: <- size {len(read)} {bytes(read)}")
                self.hydradancer_status["ep_out_status"] &= ~(0x01 << ep_num)
                return read
            return None
        except (usb.core.USBTimeoutError, usb.core.USBError):
            logging.error(f"could not read data from ep {ep_num}")
            return None

    def configure(self, endpoint_numbers):
        if len(endpoint_numbers) > len(self.endpoints_pool):
            raise HydradancerBoardFatalError(
                f"Hydradancer cannot handle {len(endpoint_numbers)} endpoints, only {len(self.endpoints_pool)}")
        try:
            for number in endpoint_numbers:
                if self.INCOMPATIBLE_EP[number] in endpoint_numbers:
                   raise HydradancerBoardFatalError(
                    f"EP {number} can't be used at the same time as EPs {','.join([endpoint_numbers])}") from exception             
                self.set_endpoint_mapping(number)
            self.device.ctrl_transfer(CTRL_TYPE_VENDOR | CTRL_RECIPIENT_DEVICE | CTRL_OUT,
                                    self.CONFIGURED)
            logging.info(f"Endpoints mapping {self.endpoints_mapping}")
            self.configured = True
        except (usb.core.USBTimeoutError, usb.core.USBError) as exception:
            logging.error(exception)
            raise HydradancerBoardFatalError(
                "Could not pass configured step on board") from exception


    def fetch_events(self):
        """
        Poll the status of the endpoints. The state are accumulated (like on the boards),
        and cleared when sending or reading data (which will trigger a similar clear on the boards).
        Thus, self.ep_status should always be in sync with the endpoint's status on the boards.
        """
        try:
            # Use the endpoint type that best fits the type of request :
            # -> for control requests, polling using ctrl transfers garanties the fastest status update.
            #     Latency is key in the enumeration phase
            # -> for bulk requests, polling using bulk transfers allows for more status updates to be sent,
            #    thus increasing the speed
            #  TODO : what about interrupt or isochronous transfers ?

            if not self.configured:
                read = self.device.ctrl_transfer(
                    CTRL_TYPE_VENDOR | CTRL_RECIPIENT_DEVICE | CTRL_IN, self.GET_EVENT, data_or_wLength=self.events, timeout=self.timeout_ms_poll)
            else:
                read = self.ep_poll.read(
                    self.events, timeout=self.timeout_ms_poll*10)
            if read >= 2:
                events = []
                for i in range(0, read, 2):
                    event = HydradancerEvent.from_bytes(self.events[i:i+2])
                    events.append(event)
                    logging.debug(event)
                    if event.event_type == HydradancerEvent.EVENT_IN_BUFFER_AVAILABLE:
                        self.hydradancer_status["ep_in_status"] |= (0x1 << event.value) & 0xff
                    elif event.event_type == HydradancerEvent.EVENT_OUT_BUFFER_AVAILABLE:
                        self.hydradancer_status["ep_out_status"] |= (0x1 << event.value) & 0xff
                    elif event.event_type == HydradancerEvent.EVENT_NAK:
                        self.hydradancer_status["ep_in_nak"] |= (0x1 << event.value) & 0xff
                logging.debug(f"Hydradancer status {self.hydradancer_status}")
                return events
            return None
        except usb.core.USBTimeoutError:
            return None
        except usb.core.USBError as exception:
            logging.error(exception)
            raise HydradancerBoardFatalError("USB Error while fetching events") from exception

    def in_buffer_empty(self, ep_num):
        """
        Returns True if the IN buffer for target endpoint ep_num is ready for priming
        """
        return self.hydradancer_status["ep_in_status"] & (0x1 << ep_num)

    def nak_on_endpoint(self, ep_num):
        """
        Returns True if the IN Endpoint has sent a NAK (meaning a host has sent an IN request)
        """
        return self.hydradancer_status["ep_in_nak"] & (0x1 << ep_num)

    def out_buffer_available(self, ep_num):
        """
        Returns True if the OUT buffer for target endpoint ep_num is full
        """
        return self.hydradancer_status["ep_out_status"] & (0x1 << ep_num)

    def control_buffer_available(self):
        """
        Returns True if the control buffer is available. Since this buffer is shared between EP0 IN/EP0 OUT, only the OUT status is used for both.
        """
        return self.out_buffer_available(0)
