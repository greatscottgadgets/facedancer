"""
Backend for HydraUSB3.

Supports 4 high-speed endpoints, with addresses between 1 and 7.
"""

import sys
import logging
import usb
from usb.util import CTRL_TYPE_VENDOR, CTRL_RECIPIENT_DEVICE, CTRL_IN, CTRL_OUT, ENDPOINT_IN
import time
from array import array

from ..core import FacedancerApp
from ..USBDevice import USBDevice


class HydradancerHostApp(FacedancerApp):
    """
    Backend for the HydraUSB3 boards.

    It supports USB2 High-speed, the speed can be set with the attribute "usb2_speed" of the device class.
    If this attribute is not present, it will default to full-speed (the speed currently assumed by the examples).
    """
    app_name = "Hydradancer Host"

    MANUFACTURER_STRING = "Quarkslab https://www.quarkslab.com/ & HydraBus https://hydrabus.com/"

    # USB directions
    HOST_TO_DEVICE = 0
    DEVICE_TO_HOST = 1

    # USB speeds
    USB2_LS = 0  # low-speed
    USB2_FS = 1  # full-speed
    USB2_HS = 2  # high-speed

    usb2_speed = USB2_FS  # default to full-speed

    configuration = None
    pending_control_out_request = None
    connected_device = None
    max_ep0_packet_size = None

    ep_in = {}
    ep_out = {}

    legacy_mode = False  # legacy_mode is used for legacy_applets

    @classmethod
    def appropriate_for_environment(cls, backend_name):
        """
        Determines if the current environment seems appropriate
        for using the libusb backend.
        """

        logging.info("this is hydradancer hi")
        # Open a connection to the target device...
        device = usb.core.find(idVendor=0x16c0, idProduct=0x27d8)

        if device is not None and device.manufacturer == cls.MANUFACTURER_STRING and backend_name == "hydradancer":
            return True

        return False

    def __init__(self, verbose=0, quirks=[], index=0, **kwargs):
        """
        Creates a new hydradancer backend for communicating with a target device.
        """

        super().__init__(self)
        self.api = HydradancerBoard()
        self.verbose = verbose
        self.api.init()
        self.api.wait_board_ready()

    def init_commands(self):
        """
        API compatibility function;
        """

    def get_version(self):
        raise NotImplementedError()

    def connect(self, usb_device, max_ep0_packet_size=64):
        """
        Prepares Hydradancer to connect to the target host and emulate
        a given device.

        usb_device: The USBDevice object that represents the device to be
            emulated.
        """
        self.api.set_endpoint_mapping(0)

        if hasattr(usb_device, 'usb2_speed'):
            self.usb2_speed = usb_device.usb2_speed

        if self.usb2_speed == self.USB2_LS:
            logging.info("Setting speed to low-speed")
        elif self.usb2_speed == self.USB2_FS:
            logging.info("Setting speed to full-speed")
        elif self.usb2_speed == self.USB2_HS:
            logging.info("Setting speed to high-speed")
        else:
            logging.info("Setting speed to full-speed")

        self.api.set_usb2_speed(self.usb2_speed)
        logging.info("connect ...")

        self.api.connect()

        self.connected_device = usb_device

        self.legacy_mode = isinstance(self.connected_device, USBDevice)
        self.max_ep0_packet_size = max_ep0_packet_size

    def disconnect(self):
        """ Disconnects the Hydradancer from its target host. """
        logging.info("disconnect")
        self.api.disconnect()

    def send_on_endpoint(self, ep_num, data, blocking=False):
        """
        Sends a collection of USB data on a given endpoint.

        ep_num: The number of the IN endpoint on which data should be sent.
        data: The data to be sent.
        blocking: If true, this function will wait for the transfer to complete.
        """
        # handle ZLP
        if not data:
            self.api.send(ep_num, data, blocking)

        if ep_num == 0:
            max_packet_size = self.max_ep0_packet_size
        else:
            max_packet_size = self.ep_in[ep_num].max_packet_size

        if len(data) > max_packet_size:
            blocking = True

        while data:
            packet = data[0:max_packet_size]
            data = data[max_packet_size:]
            self.api.send(ep_num, packet, blocking)

    def read_from_endpoint(self, ep_num):
        """
        Reads a block of data from the given endpoint.

        ep_num: The number of the OUT endpoint on which data is to be rx'd.
        """
        return self.api.read(ep_num, blocking=True)

    def stall_endpoint(self, ep_num, direction=0):
        """
        Stalls the provided endpoint, as defined in the USB spec.

        ep_num: The number of the endpoint to be stalled.
        """

        in_vs_out = "IN" if direction else "OUT"
        logging.info(f"Stalling EP {ep_num} {in_vs_out}")

        self.api.stall_endpoint(ep_num, direction)

    def stall_ep0(self):
        """
        Convenience function that stalls the control endpoint zero.
        """
        logging.info("stall_ep0")
        self.stall_endpoint(0)

    def set_address(self, address, defer=False):
        """
        Sets the device address of the Hydradancer. Usually only used during
        initial configuration.

        address: The address that the Hydradancer should assume.
        defer: True if the set_address request should wait for an active transaction to finish.
        """
        logging.info("set address")
        self.api.set_address(address, defer)

    def reset(self):
        """
        Triggers the Hydradancer to handle its side of a bus reset.
        The USB2 PHY has already been reset on the boards, this is called only to reset Facedancer and Hydradancer state.

        TODO : what if a USB request happens after the USB2 PHY has been reset but before Hydradancer has been reset as well ?
        """
        logging.info("bus reset")
        self.api.do_bus_reset()

    def configured(self, configuration):
        """
        Callback that's issued when a USBDevice is configured, e.g. by the
        SET_CONFIGURATION request. Allows us to apply the new configuration.

        configuration: The configuration applied by the SET_CONFIG request.
        """
        logging.info("configured")

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

    def ack_status_stage(self, direction=HOST_TO_DEVICE, endpoint_number=0, blocking=False):
        """
            Handles the status stage of a correctly completed control request,
            by priming the appropriate endpoint to handle the status phase.

            direction: Determines if we're ACK'ing an IN or OUT vendor request.
                (This should match the direction of the DATA stage.)
            endpoint_number: The endpoint number on which the control request
                occurred.
            blocking: True if we should wait for the ACK to be fully issued
                before returning.
        """
        if direction == self.HOST_TO_DEVICE:
            # If this was an OUT request, we'll prime the output buffer to
            # respond with the ZLP expected during the status stage.
            self.send_on_endpoint(endpoint_number, data=[], blocking=blocking)

        else:
            # If this was an IN request, we'll need to set up a transfer descriptor
            # so the status phase can operate correctly. This effectively reads the
            # zero length packet from the STATUS phase.
            self.read_from_endpoint(endpoint_number)

    def handle_data_endpoints(self):
        """
        Handle IN or OUT requests on non-control endpoints.
        """

        # process ep OUT firsts, transfer is dictated by the host, if there is data available on an ep OUT,
        # it should be processed before setting new IN data
        for ep_num, ep in self.ep_out.items():
            if self.api.OUT_buffer_available(ep_num):
                data = self.api.read(ep_num)
                if data is not None:
                    self.connected_device.handle_data_available(
                        ep_num, data.tobytes())

        for ep_num, ep in self.ep_in.items():
            if self.api.IN_buffer_empty(ep_num):
                self.connected_device.handle_data_requested(ep)

    def handle_data_endpoints_legacy(self):
        """
        Handle IN or OUT requests on non-control endpoints for the legacy_applets
        """
        # process ep OUT firsts, transfer is dictated by the host, if there is data available on an ep OUT,
        # it should be processed before setting new IN data
        for ep_num, ep in self.ep_out.items():
            if self.api.OUT_buffer_available(ep_num):
                data = self.api.read(ep_num)
                if data is not None:
                    self.connected_device.handle_data_available(
                        ep_num, data.tobytes())

        for ep_num, ep in self.ep_in.items():
            if self.api.IN_buffer_empty(ep_num):
                self.connected_device.handle_nak(ep)

    def handle_control_request(self):
        if not self.api.CONTROL_buffer_available():
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

            if is_out and has_data:
                logging.debug("queuing Control OUT req, waiting for more data")
                self.pending_control_out_request = request
                return

            self.connected_device.handle_request(request)

        # handle status stage of IN transfer
        elif len(data) == 0:
            logging.debug("Received ACK for IN Ctrl req")

    def service_irqs(self):
        """
        Core routine of the Facedancer execution/event loop. Continuously monitors the
        Hydradancers's execution status, and reacts as events occur.
        """

        self.api.fetch_events()

        if self.api.bus_reset_pending():
            self.reset()

        self.handle_control_request()

        if self.configuration is not None:
            if not self.legacy_mode:
                self.handle_data_endpoints()
            else:  # support for old USBDevice
                self.handle_data_endpoints_legacy()


class HydradancerBoardFatalError(Exception):
    pass


class HydradancerBoard():
    """
    Handles the communication with the Hydradancer control board and manages the events it sends.
    """

    MAX_PACKET_SIZE = 512

    # USB Vendor Requests codes
    ENABLE_USB_CONNECTION_REQUEST_CODE = 50
    SET_ADDRESS_REQUEST_CODE = 51
    GET_EP_STATUS = 52
    SET_ENDPOINT_MAPPING = 53
    DISABLE_USB = 54
    SET_SPEED = 55
    SET_EP_RESPONSE = 56
    CHECK_HYDRADANCER_READY = 57
    DO_BUS_RESET = 58

    #  events offsets
    HYDRADANCER_STATUS_BUS_RESET = 0x1

    # USB speeds
    USB2_LS = 0
    USB2_FS = 1
    USB2_HS = 2

    # Endpoint states on the emulation board
    ENDP_STATE_ACK = 0x00
    ENDP_STATE_NAK = 0x02
    ENDP_STATE_STALL = 0x03

    # Endpoints available on the control board for mapping (to the emulated device endpoints)
    endpoints_pool = None
    endpoints_mapping = {}  # emulated endpoint -> control board endpoint
    reverse_endpoints_mapping = {}  # control_board_endpoint -> emulated_endpoint

    EP_POLL_NUMBER = 1

    SUPPORTED_EP_NUM = [0, 1, 2, 3, 4, 5, 6, 7]

    # True when SET_CONFIGURATION has been received and the Hydradancer boards are configured
    configured = False

    # 0x00ff (IN status mask, 1 = emulated ep ready for priming), 0xff00 (OUT mask, data received on emulated ep)
    _hydradancer_status_bytes = array('B', [0] * 4)
    hydradancer_status = {}
    hydradancer_status["ep_in_status"] = 0x00
    hydradancer_status["ep_out_status"] = 0x00
    hydradancer_status["ep_in_nak"] = 0x00
    hydradancer_status["other_events"] = 0x00

    timeout_ms_poll = 1

    # USB endpoints direction
    HOST_TO_DEVICE = 0
    DEVICE_TO_HOST = 1

    def init(self):
        """
        Get handles on the USB control board, and wait for Hydradancer to be ready
        """

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
                CTRL_TYPE_VENDOR | CTRL_RECIPIENT_DEVICE | CTRL_OUT, self.ENABLE_USB_CONNECTION_REQUEST_CODE)
        except (usb.core.USBTimeoutError, usb.core.USBError) as exception:
            logging.error(exception)
            raise HydradancerBoardFatalError("Error, unable to connect")

    def disconnect(self):
        """
        Disable the USB2 connection on the emulation board,
        and reset internal states on both control and emulation boards.
        """
        try:
            self.device.ctrl_transfer(
                CTRL_TYPE_VENDOR | CTRL_RECIPIENT_DEVICE | CTRL_OUT, self.DISABLE_USB)
            usb.util.dispose_resources(self.device)

            # Reset state just in case
            self.hydradancer_status["ep_in_status"] = 0x00
            self.hydradancer_status["ep_out_status"] = 0x00
            self.hydradancer_status["ep_in_nak"] = 0x00
            self.hydradancer_status["other_events"] = 0x00
            self.endpoints_mapping = {}  # emulated endpoint -> control board endpoint
            # control_board_endpoint -> emulated_endpoint
            self.reverse_endpoints_mapping = {}

        except (usb.core.USBTimeoutError, usb.core.USBError) as exception:
            logging.error(exception)
            raise HydradancerBoardFatalError("Error, unable to disconnect")

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
                "USB Error while waiting for Hydradancer go-ahead")

    def set_endpoint_mapping(self, ep_num):
        """
        Maps emulated endpoints (endpoints facing the target) to Facedancer's host endpoints (control board endpoints)
        """
        if ep_num not in self.SUPPORTED_EP_NUM:
            raise HydradancerBoardFatalError(
                f"Endpoint number {ep_num} not supported, supported numbers : {self.SUPPORTED_EP_NUM}")
        if not self.endpoints_pool:
            raise HydradancerBoardFatalError(
                f"All endpoints are already in use")

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
                f"Could not set mapping for ep {ep_num}")

    def set_usb2_speed(self, usb2_speed):
        """
        Set the speed of the USB2 device. Speed is physically determined by the host,
        so the emulation board must be configured.
        """
        try:
            self.device.ctrl_transfer(
                CTRL_TYPE_VENDOR | CTRL_RECIPIENT_DEVICE | CTRL_OUT, self.SET_SPEED, wValue=usb2_speed & 0x00ff)
        except (usb.core.USBTimeoutError, usb.core.USBError) as exception:
            logging.error(exception)
            raise HydradancerBoardFatalError("Error, unable to set speed")

    def do_bus_reset(self):
        """
        Set the speed of the USB2 device. Speed is physically determined by the host,
        so the emulation board must be configured.
        """
        try:
            self.device.ctrl_transfer(
                CTRL_TYPE_VENDOR | CTRL_RECIPIENT_DEVICE | CTRL_OUT, self.DO_BUS_RESET)
            self.hydradancer_status["other_events"] &= ~self.HYDRADANCER_STATUS_BUS_RESET
        except (usb.core.USBTimeoutError, usb.core.USBError) as exception:
            logging.error(exception)
            raise HydradancerBoardFatalError("Error, unable to do bus reset")

    def set_address(self, address, defer=False):
        """
        Set the USB address on the emulation board
        """
        try:
            self.device.ctrl_transfer(
                CTRL_TYPE_VENDOR | CTRL_RECIPIENT_DEVICE | CTRL_OUT, self.SET_ADDRESS_REQUEST_CODE, address)
        except (usb.core.USBTimeoutError, usb.core.USBError) as exception:
            logging.error(exception)
            raise HydradancerBoardFatalError(
                "Error, unable to set address on emulated device")

    def stall_endpoint(self, ep_num, direction=0):
        """
        Stall the ep_num endpoint on the emulation board.
        STALL will be cleared automatically after next SETUP packet received.
        Currently stalls both directions, because ep0 was STALLED only in one direction
        (TODO maybe separate ep0 from the rest, and double-check).
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
            raise HydradancerBoardFatalError(f"Could not stall ep {ep_num}")

    def send(self, ep_num, data, blocking=False):
        """
        Prime target endpoint ep_num. If blocking=True, it will wait for the endpoint's buffer to be empty.
        """
        try:
            self.ep_out[self.endpoints_mapping[ep_num]].write(
                data)
            self.hydradancer_status["ep_in_status"] &= ~(0x01 << ep_num)
            if blocking:
                while not self.IN_buffer_empty(ep_num):
                    self.fetch_events()
        except (usb.core.USBTimeoutError, usb.core.USBError):
            logging.error(f"could not send data on ep {ep_num}")

    def read(self, ep_num, blocking=False):
        """
        Read from target endpoint ep_num. If blocking=True, wait until the endpoint's buffer is full.
        """
        logging.debug(f"reading from ep {ep_num}")
        try:
            if blocking:
                while not self.OUT_buffer_available(ep_num):
                    self.fetch_events()
            if self.OUT_buffer_available(ep_num):
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
        for number in endpoint_numbers:
            self.set_endpoint_mapping(number)
        logging.info(f"Endpoints mapping {self.endpoints_mapping}")
        self.configured = True

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
                    CTRL_TYPE_VENDOR | CTRL_RECIPIENT_DEVICE | CTRL_IN, self.GET_EP_STATUS, data_or_wLength=self._hydradancer_status_bytes, timeout=self.timeout_ms_poll)
            else:
                read = self.ep_poll.read(
                    self._hydradancer_status_bytes, timeout=self.timeout_ms_poll)

            if read > 0:
                (new_ep_in_status, new_ep_out_status, new_ep_in_nak,
                 new_other_events) = self._hydradancer_status_bytes

                self.hydradancer_status["ep_in_status"] |= new_ep_in_status
                self.hydradancer_status["ep_out_status"] |= new_ep_out_status
                self.hydradancer_status["ep_in_nak"] |= new_ep_in_nak
                self.hydradancer_status["other_events"] |= new_other_events

                logging.debug(f"Hydradancer status {self.hydradancer_status}")
                return True
            return False
        except usb.core.USBTimeoutError:
            return False
        except usb.core.USBError as exception:
            logging.error(exception)
            raise HydradancerBoardFatalError("USB Error while fetching events")

    def IN_buffer_empty(self, ep_num):
        """
        Returns True if the IN buffer for target endpoint ep_num is ready for priming
        """
        return self.hydradancer_status["ep_in_status"] & (0x1 << ep_num)

    def OUT_buffer_available(self, ep_num):
        """
        Returns True if the OUT buffer for target endpoint ep_num is full
        """
        return self.hydradancer_status["ep_out_status"] & (0x1 << ep_num)

    def CONTROL_buffer_available(self):
        """
        Returns True if the IN buffer for the control endpoint is ready for priming. 
        Note that currently all control requests (whatever the endpoint num it arrived with) will end up here.
        """
        return self.IN_buffer_empty(0)

    def bus_reset_pending(self):
        """
        Returns True if the IN buffer for the control endpoint is ready for priming. 
        Note that currently all control requests (whatever the endpoint num it arrived with) will end up here.
        """
        return self.hydradancer_status["other_events"] & self.HYDRADANCER_STATUS_BUS_RESET
