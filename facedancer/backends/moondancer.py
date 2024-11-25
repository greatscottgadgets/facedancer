# MoondancerApp.py

import sys
import time
import codecs
import enum
import traceback

from typing           import List, Tuple

from ..core           import *
from ..device         import USBDevice
from ..configuration  import USBConfiguration
from ..request        import USBControlRequest
from ..types          import DeviceSpeed, USBDirection

from ..logging        import log

from .base            import FacedancerBackend


# Quirk flags
class QuirkFlag(enum.IntFlag):
    MANUAL_SET_ADDRESS: int = 0x01


# Cynthion interrupt events
class InterruptEvent:
    USB_BUS_RESET:       int = 10
    USB_RECEIVE_CONTROL: int = 11
    USB_RECEIVE_PACKET:  int = 12
    USB_SEND_COMPLETE:   int = 13

    def __init__(self, data: Tuple[int, int]):
        """
        Parses a tuple of two bytes representing an interrupt event into an InterruptEvent.

        Args:
            data : A tuple of two bytes. The first byte is the interrupt code, the second is the endpoint number.
        """
        if len(data) != 2:
            log.error(f"Invalid length for InterruptEvent: {len(data)}")
            raise ValueError(f"Invalid length for InterruptEvent: {len(data)}")

        event = data[0]
        endpoint_number = data[1]

        if event not in [
            InterruptEvent.USB_BUS_RESET,
            InterruptEvent.USB_RECEIVE_CONTROL,
            InterruptEvent.USB_RECEIVE_PACKET,
            InterruptEvent.USB_SEND_COMPLETE
        ]: raise ValueError(f"Unknown InterruptEvent id: {event}")

        self.event = event
        self.endpoint_number = endpoint_number

    def __eq__(self, rhs):
        return self.event == rhs

    def __repr__(self):
        name = "UNKNOWN"
        if self.event == InterruptEvent.USB_BUS_RESET:
            name = "USB_BUS_RESET"
        elif self.event == InterruptEvent.USB_RECEIVE_CONTROL:
            name = "USB_RECEIVE_CONTROL"
        elif self.event == InterruptEvent.USB_RECEIVE_PACKET:
            name = "USB_RECEIVE_PACKET"
        elif self.event == InterruptEvent.USB_SEND_COMPLETE:
            name = "USB_SEND_COMPLETE"
        return f"{name} {self.endpoint_number}"


#
# Moondancer backend implementation
#
class MoondancerApp(FacedancerApp, FacedancerBackend):
    """
    Backend for using Cynthion devices as Facedancers.
    """

    app_name = "Moondancer"

    # Number of supported USB endpoints.
    SUPPORTED_ENDPOINTS = 16

    def __init__(self, device: USBDevice=None, verbose: int=0, quirks: List[str]=[]):
        """
        Sets up a new Cynthion-backed Facedancer (Moondancer) application.

        Args:
            device  : The Cynthion device that will act as our Moondancer.
            verbose : The verbosity level of the given application.
        """

        log.info("Using the Moondancer backend.")

        import cynthion

        if device is None:
            device = cynthion.Cynthion()

        self.device = device

        self.device.comms.get_exclusive_access()

        FacedancerApp.__init__(self, device, verbose)
        self.connected_device = None

        # Grab the raw API object from the Cynthion object.
        # This has the low-level RPCs used for raw USB control.
        self.api = self.device.apis.moondancer

        # Initialize a dictionary that will store the last setup
        # whether each endpoint is currently stalled.
        self.endpoint_stalled = {}
        for i in range(self.SUPPORTED_ENDPOINTS):
            self.endpoint_stalled[i] = False

        # Assume a max packet size of 64 until configured otherwise.
        self.max_packet_size_ep0 = 64

        # Start off by assuming we're not waiting for an OUT control transfer's
        # data stage.  # See handle_setup_complete_on_endpoint for details.
        self.pending_control_request = None

        # Store a reference to the device's active configuration,
        # which we'll use to know which endpoints we'll need to check
        # for data transfer readiness.
        self.configuration = None

        #
        # Store our list of quirks to handle.
        #
        if quirks:
            self.quirks = quirks
        else:
            self.quirks = []

        # Maintain a list of configured endpoints with form: (address, max_packet_size, USBTransferType)
        self.configured_endpoints = dict()


    # - Facedancer backend methods --------------------------------------------

    @classmethod
    def appropriate_for_environment(cls, backend_name: str) -> bool:
        """
        Determines if the current environment seems appropriate
        for using the Moondancer backend.
        """

        # Check: if we have a backend name other than moondancer,
        # the user is trying to use something else. Abort!
        if backend_name and backend_name != "cynthion":
            return False

        # If we're not explicitly trying to use something else,
        # see if there's a connected Cynthion.
        try:
            import cynthion
            device = cynthion.Cynthion()
            return device.supports_api('moondancer')
        except ImportError:
            log.info("Skipping Cynthion-based devices, as the cynthion python module isn't installed.")
            return False
        except IOError:
            log.warning("Found Cynthion-based device, but could not access it. (Check permissions?)")
            return False
        except:
            return False


    def get_version(self):
        """
        Returns information about the active Moondancer version.
        """
        # TODO: Return the Cynthion software version, or something indicating
        # the Cynthion API number?
        raise NotImplementedError()


    def connect(self, usb_device: USBDevice, max_packet_size_ep0: int=64, device_speed: DeviceSpeed=DeviceSpeed.FULL):
        """
        Prepares Cynthion to connect to the target host and emulate
        a given device.

        Args:
            usb_device : The USBDevice object that represents the device to be
                         emulated.
        """

        if device_speed not in [DeviceSpeed.FULL, DeviceSpeed.HIGH]:
            log.warning(f"Moondancer only supports USB Full and High Speed. Ignoring requested speed: {device_speed.name}")

        log.debug(f"moondancer.connect(max_packet_size_ep0:{max_packet_size_ep0}, device_speed:{device_speed}, quirks:{self.quirks})")

        self.max_packet_size_ep0 = max_packet_size_ep0

        # compute our quirk flags
        quirks = 0
        if 'manual_set_address' in self.quirks:
            log.warning("Handling SET_ADDRESS on the target host side!")
            quirks |= QuirkFlag.MANUAL_SET_ADDRESS

        # connect to target host
        self.api.connect(self.max_packet_size_ep0, device_speed, quirks)
        self.connected_device = usb_device

        # get device name
        device_name = f"{type(self.connected_device).__module__}.{type(self.connected_device).__qualname__}"

        log.info(f"Connected {device_speed.name} speed device '{device_name}' to target host.")


    def disconnect(self):
        """ Disconnects Cynthion from the target host. """

        log.info("Disconnecting from target host.")

        self.device.comms.release_exclusive_access()

        # disconnect from target host
        self.api.disconnect()
        self.connected_device = None


    def reset(self):
        """
        Triggers the Cynthion to handle its side of a bus reset.
        """

        log.debug(f"moondancer.bus_reset()")

        self.api.bus_reset()


    def set_address(self, address: int, defer: bool=False):
        """
        Sets the device address of Moondancer. Usually only used during
        initial configuration.

        Args:
            address : The address that Moondancer should assume.
            defer   : True iff the set_address request should wait for an active transaction to finish.
        """

        log.debug(f"moondancer.set_address({address}, {defer})")

        self.api.set_address(address, 1 if defer else 0)


    def configured(self, configuration: USBConfiguration):
        """
        Callback that's issued when a USBDevice is configured, e.g. by the
        SET_CONFIGURATION request. Allows us to apply the new configuration.

        Args:
            configuration : The USBConfiguration object applied by the SET_CONFIG request.
        """

        log.debug(f"moondancer.configured({configuration})")

        if configuration is None:
            log.error("Target host configuration could not be applied.")
            return

        # If we need to issue a configuration command, issue one.
        # (If there are no endpoints other than control, this command will be
        #  empty, and we can skip this.)
        endpoint_triplets = []

        for interface in configuration.get_interfaces():
            for endpoint in interface.get_endpoints():

                log.debug(f"Configuring endpoint: {endpoint}.")

                triple = (endpoint.get_address(), endpoint.max_packet_size, endpoint.transfer_type,)
                endpoint_triplets.append(triple)

        if len(endpoint_triplets):
            self.api.configure_endpoints(*endpoint_triplets)
            for triplet in endpoint_triplets:
                self.configured_endpoints[triplet[0]] = triplet

        # save configuration
        self.configuration = configuration

        # If we've just set up endpoints, check to see if any of them
        # have NAKs waiting.
        nak_status = self.api.get_nak_status()
        self.handle_ep_in_nak_status(nak_status)

        log.info("Target host configuration complete.")


    def read_from_endpoint(self, endpoint_number: int) -> bytes:
        """
        Reads a block of data from the given endpoint.

        Args:
            endpoint_number : The number of the OUT endpoint on which data is to be rx'd.
        """

        log.debug(f"moondancer.read_from_endpoint({endpoint_number})")

        # Read from the given endpoint...
        data = self.api.read_endpoint(endpoint_number)

        # Re-enable OUT interface to receive data again...
        self.api.ep_out_interface_enable()

        log.trace(f"  moondancer.api.read_endpoint({endpoint_number}) -> {len(data)} '{data}'")

        # Finally, return the result.
        return data


    def send_on_control_endpoint(self, endpoint_number: int, in_request: USBControlRequest, data: bytes, blocking: bool=True):
        """
        Sends a collection of USB data in response to a IN control request by the host.

        Args:
            endpoint_number  : The number of the IN endpoint on which data should be sent.
            requested_length : The number of bytes requested by the host.
            data             : The data to be sent.
            blocking         : If true, this function should wait for the transfer to complete.
        """
        requested_length = in_request.length
        self.api.write_control_endpoint(endpoint_number, requested_length, blocking, bytes(data))

        log.debug(f"moondancer.send_on_control_endpoint({endpoint_number}, {requested_length}, {len(data)}, {blocking})")
        log.trace(f"  moondancer.api.write_control_endpoint({endpoint_number}, {requested_length}, {blocking}, {len(data)})")


    def send_on_endpoint(self, endpoint_number: int, data: bytes, blocking: bool=True):
        """
        Sends a collection of USB data on a given endpoint.

        Args:
            endpoint_number : The number of the IN endpoint on which data should be sent.
            data     : The data to be sent.
            blocking : If true, this function will wait for the transfer to complete.
        """

        self.api.write_endpoint(endpoint_number, blocking, bytes(data))

        log.debug(f"moondancer.send_on_endpoint({endpoint_number}, {len(data)}, {blocking})")
        log.trace(f"  moondancer.api.write_endpoint({endpoint_number}, {blocking}, {len(data)})")


    # TODO this is only used by USBProxy - replace with "backend.ep_prime_for_receive" and "backend.send_zlp"
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

        log.debug(f"moondancer.ack_status_stage({direction.name}, {endpoint_number}, {blocking})")

        if direction == USBDirection.OUT: # HOST_TO_DEVICE
            # If this was an OUT request, we'll prime the output buffer to
            # respond with the ZLP expected during the status stage.
            self.api.write_endpoint(endpoint_number, blocking, bytes([]))

            log.trace(f"  moondancer.api.write_endpoint({endpoint_number}, {blocking}, [])")

        else: # DEVICE_TO_HOST (IN)
            # If this was an IN request, we'll need to set up a transfer descriptor
            # so the status phase can operate correctly. This effectively reads the
            # zero length packet from the STATUS phase.
            self.api.ep_out_prime_receive(endpoint_number)

            log.trace(f"  moondancer.api.ep_out_prime_receive({endpoint_number})")


    def stall_endpoint(self, endpoint_number:int, direction: USBDirection=USBDirection.OUT):
        """
        Stalls the provided endpoint, as defined in the USB spec.

        Args:
            endpoint_number : The number of the endpoint to be stalled.
        """

        endpoint_address = (endpoint_number | 0x80) if direction else endpoint_number
        log.debug(f"Stalling EP{endpoint_number} {USBDirection(direction).name} (0x{endpoint_address:x})")

        # Mark endpoint number as stalled.
        self.endpoint_stalled[endpoint_number] = True

        # Stall endpoint address.
        if direction:
            self.api.stall_endpoint_in(endpoint_number)
            log.debug(f"  moondancer.api.stall_endpoint_in({endpoint_number})")
        else:
            self.api.stall_endpoint_out(endpoint_number)
            log.debug(f"  moondancer.api.stall_endpoint_out({endpoint_number})")


    def clear_halt(self, endpoint_number: int, direction: USBDirection):
        """ Clears a halt condition on the provided non-control endpoint.

        Args:
            endpoint_number : The endpoint number
            direction       : The endpoint direction; or OUT if not provided.
        """

        endpoint_address = (endpoint_number | 0x80) if direction else endpoint_number
        log.debug(f"Clearing halt EP{endpoint_number} {USBDirection(direction).name} (0x{endpoint_address:x})")

        self.api.clear_feature_endpoint_halt(endpoint_number, direction)
        log.debug(f"  moondancer.api.clear_feature_endpoint_halt({endpoint_number}, {direction})")


    def service_irqs(self):
        """
        Core routine of the Facedancer execution/event loop. Continuously monitors the
        Moondancer's execution status, and reacts as events occur.
        """

        # Get latest interrupt events
        events: List[Tuple[int, int]] = self.api.get_interrupt_events()

        # Handle interrupt events.
        if len(events) > 0:

            # gcp doesn't seem to return a nested tuple if it's only one event
            if isinstance(events[0], int):
                events = [ events ]

            parsed_events = [InterruptEvent(event) for event in events]

            for event in parsed_events:
                log.debug(f"MD IRQ => {event}")
                if event == InterruptEvent.USB_BUS_RESET:
                    self.handle_bus_reset()
                elif event == InterruptEvent.USB_RECEIVE_CONTROL:
                    self.handle_receive_control(event.endpoint_number)
                elif event == InterruptEvent.USB_RECEIVE_PACKET and event.endpoint_number == 0:
                    # TODO support endpoints other than EP0
                    self.handle_receive_control_packet(event.endpoint_number)
                elif event == InterruptEvent.USB_RECEIVE_PACKET:
                    self.handle_receive_packet(event.endpoint_number)
                elif event == InterruptEvent.USB_SEND_COMPLETE:
                    self.handle_send_complete(event.endpoint_number)
                else:
                    log.error(f"Unhandled interrupt event: {event}")

        # Check EP_IN NAK status for pending data requests
        else:
            nak_status = self.api.get_nak_status()
            if nak_status != 0:
                self.handle_ep_in_nak_status(nak_status)

    # - Interrupt event handlers ----------------------------------------------

    # USB0_BUS_RESET
    def handle_bus_reset(self):
        """
        Triggers Moondancer to perform its side of a bus reset.
        """

        if self.connected_device:
            self.connected_device.handle_bus_reset()
        else:
            self.api.bus_reset()


    # USB0_RECEIVE_CONTROL
    def handle_receive_control(self, endpoint_number: int):
        """
        Handles a known outstanding control event on a given endpoint.

        endpoint_number: The endpoint number for which a control event should be serviced.
        """

        log.debug(f"handle_receive_control({endpoint_number})")

        # HACK: to maintain API compatibility with the existing facedancer API,
        # we need to know if a stall happens at any point during our handler.
        self.endpoint_stalled[endpoint_number] = False

        # Read the data from the SETUP stage...
        data    = bytearray(self.api.read_control())
        request = self.connected_device.create_request(data)

        log.debug(f"  moondancer.api.read_control({endpoint_number}) -> {len(data)} '{request}'")

        is_out   = request.get_direction() == USBDirection.OUT # HOST_TO_DEVICE
        has_data = (request.length > 0)
        log.trace(f"  is_out:{is_out}  has_data:{has_data}")

        # Special case: if this is an OUT request with a data stage, we won't
        # handle the request until the data stage has been completed. Instead,
        # we'll stash away the data received in the setup stage, prime the
        # endpoint for the data stage, and then wait for the data stage to
        # complete, triggering a corresponding code path in
        # in handle_transfer_complete_on_endpoint.
        if is_out and has_data:
            log.debug(f"  setup packet has data - queueing read")
            self.pending_control_request = request
            self.api.ep_out_prime_receive(endpoint_number)
            return

        # Pass the request to the emulated device for handling.
        log.trace(f"  connected_device.handle_request({request})")
        self.connected_device.handle_request(request)

        # If it was an IN request with a data stage we now need to
        # prime the endpoint to receive a ZLP from the host
        # acknowledging receipt of our response.
        if has_data and not is_out and not self.endpoint_stalled[endpoint_number]:
            log.debug(f"  CONTROL IN -> prime ep to receive zlp")
            self.api.ep_out_prime_receive(endpoint_number)


    # USB0_RECEIVE_PACKET(0)
    def handle_receive_control_packet(self, endpoint_number: int):
        log.debug(f"moondancer.handle_receive_control_packet({endpoint_number}) pending:{self.pending_control_request}")

        # Handle packet if we don't have a pending control request
        if not self.pending_control_request:
            data = self.api.read_endpoint(endpoint_number)
            if len(data) == 0:
                # It's a zlp following an IN control transfer, re-enable interface for reception on other endpoints.
                self.api.ep_out_interface_enable()
            else:
                log.error(f"Discarding {len(data)} bytes on control endpoint with no pending control request")
            return

        # We have a pending control request with a data stage...
        # Read the rest of the data from the endpoint, completing the control request.
        new_data = self.api.read_endpoint(endpoint_number)

        log.debug(f"  handling control data stage: {len(new_data)} bytes")
        log.trace(f"  moondancer.api.read_endpoint({endpoint_number}) -> {len(new_data)}")

        if len(new_data) == 0:
            # It's a zlp following a control IN transfer, re-enable interface for reception on other endpoints.
            self.api.ep_out_interface_enable()
            log.debug(f"ZLP ending Control IN transfer on ep: {endpoint_number}")
            return

        # Append our new data to the pending control request.
        self.pending_control_request.data.extend(new_data)

        all_data_received = len(self.pending_control_request.data) == self.pending_control_request.length
        is_short_packet   = len(new_data) < self.max_packet_size_ep0

        if all_data_received or is_short_packet:
            # Handle the completed setup request...
            self.connected_device.handle_request(self.pending_control_request)

            # And clear our pending setup data.
            self.pending_control_request = None

            # Finally, re-enable interface for reception on other endpoints.
            self.api.ep_out_interface_enable()

            return

        # Finally, re-prime our control endpoint to receive the rest of the control data.
        self.api.ep_out_prime_receive(endpoint_number)


    # USB0_RECEIVE_PACKET(1...15)
    def handle_receive_packet(self, endpoint_number: int):
        """
        Handles a known-completed transfer on a given endpoint.

        Args:
            endpoint_number : The endpoint number for which the transfer should be serviced.
        """

        log.debug(f"moondancer.handle_receive_packet({endpoint_number})")

        # Read the data from the endpoint
        data = self.api.read_endpoint(endpoint_number)

        log.trace(f"  moondancer.api.read_endpoint({endpoint_number}) -> {len(data)}")

        # Ignore it if it's a ZLP ack as Facedancer devices don't handle it.
        if len(data) == 0:
            # Finally, Prime endpoint to receive again.
            self.api.ep_out_interface_enable()
            log.debug(f"  ZLP ending Bulk IN transfer on ep: {endpoint_number}")
            return

        # Pass it to the device's handler
        self.connected_device.handle_data_available(endpoint_number, data)

        # Finally, re-enable other OUT endpoints so we can receive on them again.
        self.api.ep_out_interface_enable()


    # USB0_SEND_COMPLETE
    def handle_send_complete(self, endpoint_number: int):
        log.debug(f"handle_send_complete({endpoint_number})")
        pass

    # Handle pending data requests on EP_IN
    def handle_ep_in_nak_status(self, nak_status: int):
        nakked_endpoints = [epno for epno in range(self.SUPPORTED_ENDPOINTS) if (nak_status >> epno) & 1]
        for endpoint_number in nakked_endpoints:
            if endpoint_number != 0:
                log.trace(f"Received IN NAK on ep{endpoint_number}")
                self.connected_device.handle_nak(endpoint_number)
