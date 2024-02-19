# MoondancerApp.py

import sys
import time
import codecs
import functools
import enum
import logging
import traceback

from ..core          import *
from ..constants     import DeviceSpeed
from ..future.types  import USBDirection


# add a TRACE level to logging
logging.TRACE = 5
logging.addLevelName(logging.TRACE, "TRACE")
logging.Logger.trace = functools.partialmethod(logging.Logger.log, logging.TRACE)
logging.trace = functools.partial(logging.log, logging.TRACE)

# Quirk flags
class QuirkFlag(enum.IntFlag):
    MANUAL_SET_ADDRESS = 0x01

# USB directions
class Direction(enum.IntFlag):
    HOST_TO_DEVICE = 0 # TARGET HOST TO DEVICE (OUT)
    DEVICE_TO_HOST = 1 # DEVICE TO TARGET HOST (IN)

# Cynthion interrupt messages
class InterruptEvent(enum.Enum):
    USB_BUS_RESET = 10
    USB_RECEIVE_CONTROL = 11
    USB_RECEIVE_PACKET = 12
    USB_SEND_COMPLETE = 13

    def parse(data):
        if len(data) != 2:
            logging.error(f"Invalid length for InterruptEvent: {len(data)}")
            raise ValueError(f"Invalid length for InterruptEvent: {len(data)}")
        message = InterruptEvent(data[0])
        message.endpoint_number = data[1]
        return message


#
# Moondancer backend implementation
#
class MoondancerApp(FacedancerApp):
    """
    Backend for using Cynthion devices as FaceDancers.
    """

    app_name = "Moondancer"
    app_num = 0x00 # This doesn't have any meaning for us.

    # Number of supported USB endpoints.
    # TODO: bump this up when we develop support using USB0 (cables flipped)
    SUPPORTED_ENDPOINTS = 16

    def __init__(self, device=None, verbose=0, quirks=None):
        """
        Sets up a new Cynthion-backed Facedancer (Moondancer) application.

        device: The Cynthion device that will act as our Moondancer.
        verbose: The verbosity level of the given application.
        """

        #logging.getLogger().setLevel(logging.DEBUG)

        logging.info("Using the Moondancer backend.")

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
        self.max_ep0_packet_size = 64

        # Start off by assuming we're not waiting for an OUT control transfer's
        # data stage.  # See handle_setup_complete_on_endpoint for details.
        self.pending_control_request = None

        # Store a reference to the device's active configuration,
        # which we'll use to know which endpoints we'll need to check
        # for data transfer readiness.
        self.configuration = None

        # By default, Cynthion's target port operates at High speed.
        self.device_speed = DeviceSpeed.HIGH

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
    def appropriate_for_environment(cls, backend_name):
        """
        Determines if the current environment seems appropriate
        for using the Moondancer backend.
        """

        # Check: if we have a backend name other than moondancer,
        # the user is trying to use something else. Abort!
        if backend_name and backend_name != "moondancer":
            return False

        # If we're not explicitly trying to use something else,
        # see if there's a connected Cynthion.
        try:
            import cynthion
            device = cynthion.Cynthion()
            return device.supports_api('moondancer')
        except ImportError:
            logging.debug("Skipping Cynthion-based devices, as the cynthion python module isn't installed.")
            return False
        except:
            return False


    def init_commands(self):
        """
        API compatibility function; not necessary for Moondancer.
        """
        pass


    def get_version(self):
        """
        Returns information about the active Moondancer version.
        """
        # TODO: Return the Cynthion software version, or something indicating
        # the Cynthion API number?
        raise NotImplementedError()


    def set_device_speed(self, device_speed):
        """
        Sets the speed to be used when connecting Cynthion's target port.

        device_speed: a constants.DeviceSpeed value.
        """
        self.device_speed = device_speed


    def connect(self, usb_device, max_ep0_packet_size=64):
        """
        Prepares Cynthion to connect to the target host and emulate
        a given device.

        usb_device: The USBDevice object that represents the device to be
                    emulated.
        """

        logging.debug(f"moondancer.connect(max_ep0_packet_size:{max_ep0_packet_size}, device_speed:{self.device_speed}, quirks:{self.quirks})")

        self.max_ep0_packet_size = max_ep0_packet_size

        # compute our quirk flags
        quirks = 0
        if 'manual_set_address' in self.quirks:
            logging.warn("Handling SET_ADDRESS on the target host side!")
            quirks |= QuirkFlag.MANUAL_SET_ADDRESS

        # connect to target host
        self.api.connect(self.max_ep0_packet_size, self.device_speed, quirks)
        self.connected_device = usb_device

        # get device name
        device_name = f"{type(self.connected_device).__module__}.{type(self.connected_device).__qualname__}"

        logging.info(f"Connected '{device_name}' to target host.")


    def disconnect(self):
        """ Disconnects Cynthion from the target host. """

        logging.info("Disconnecting from target host.")

        self.device.comms.release_exclusive_access()

        # disconnect from target host
        self.api.disconnect()
        self.connected_device = None


    def reset(self):
        """
        Triggers the Cynthion to handle its side of a bus reset.
        """

        logging.debug(f"moondancer.bus_reset()")

        self.api.bus_reset()


    def set_address(self, address, defer=False):
        """
        Sets the device address of Moondancer. Usually only used during
        initial configuration.

        address: The address that Moondancer should assume.
        defer: True iff the set_address request should wait for an active transaction to finish.
        """

        logging.debug(f"moondancer.set_address({address}, {defer})")

        self.api.set_address(address, 1 if defer else 0)


    def configured(self, configuration):
        """
        Callback that's issued when a USBDevice is configured, e.g. by the
        SET_CONFIGURATION request. Allows us to apply the new configuration.

        configuration: The USBConfiguration object applied by the SET_CONFIG request.
        """

        logging.debug("fmoondancer.configured({configuration})")

        if configuration is None:
            logging.error("Target host configuration could not be applied.")
            return

        # If we need to issue a configuration command, issue one.
        # (If there are no endpoints other than control, this command will be
        #  empty, and we can skip this.)
        endpoint_triplets = []

        for interface in configuration.get_interfaces():
            for endpoint in interface.get_endpoints():

                logging.debug(f"Configuring endpoint: {endpoint}.")

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

        logging.info("Target host configuration complete.")


    def read_from_endpoint(self, endpoint_number):
        """
        Reads a block of data from the given endpoint.

        endpoint_number: The number of the OUT endpoint on which data is to be rx'd.
        """

        logging.debug(f"moondancer.read_from_endpoint({endpoint_number})")

        # Read from the given endpoint...
        data = self.api.read_endpoint(endpoint_number)

        # Prime endpoint to receive data again...
        self.api.ep_out_prime_receive(endpoint_number)

        logging.trace(f"  moondancer.api.read_endpoint({endpoint_number}) -> {len(data)} '{data}'")

        # Finally, return the result.
        return data


    def send_on_endpoint(self, endpoint_number, data, blocking=True):
        """
        Sends a collection of USB data on a given endpoint.

        endpoint_number: The number of the IN endpoint on which data should be sent.
        data: The data to be sent.
        blocking: If true, this function will wait for the transfer to complete.
        """

        logging.debug(f"moondancer.send_on_endpoint({endpoint_number}, {len(data)}, {blocking})")

        self.api.write_endpoint(endpoint_number, blocking, bytes(data))

        logging.trace(f"  moondancer.api.write_endpoint({endpoint_number}, {blocking}, {data})")


    def ack_status_stage(self, direction=Direction.HOST_TO_DEVICE, endpoint_number=0, blocking=False):
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

        logging.debug(f"moondancer.ack_status_stage({direction.name}, {endpoint_number}, {blocking})")

        if direction == Direction.HOST_TO_DEVICE: # 0 = HOST_TO_DEVICE (OUT)
            # If this was an OUT request, we'll prime the output buffer to
            # respond with the ZLP expected during the status stage.
            self.api.write_endpoint(endpoint_number, blocking, bytes([]))

            logging.trace(f"  moondancer.api.write_endpoint({endpoint_number}, {blocking}, [])")

        else: # 1 = DEVICE_TO_HOST (IN)
            # If this was an IN request, we'll need to set up a transfer descriptor
            # so the status phase can operate correctly. This effectively reads the
            # zero length packet from the STATUS phase.
            self.api.ep_out_prime_receive(endpoint_number)

            logging.trace(f"  moondancer.api.ep_out_prime_receive({endpoint_number})")


    def stall_endpoint(self, endpoint_number, direction=0):
        """
        Stalls the provided endpoint, as defined in the USB spec.

        endpoint_number: The number of the endpoint to be stalled.
        """

        # USBDirection.OUT = 0
        # USBDirection.IN  = 1

        endpoint_address = (endpoint_number | 0x80) if direction else endpoint_number
        logging.debug(f"Stalling EP{endpoint_number} {USBDirection(direction).name} (0x{endpoint_address:x})")

        # Mark endpoint number as stalled.
        self.endpoint_stalled[endpoint_number] = True

        # Stall endpoint address.
        if direction:
            self.api.stall_endpoint_in(endpoint_number)
            logging.debug(f"  moondancer.api.stall_endpoint_in({endpoint_number})")
        else:
            self.api.stall_endpoint_out(endpoint_number)
            logging.debug(f"  moondancer.api.stall_endpoint_out({endpoint_number})")


    def stall_ep0(self, direction=0):
        """
        Convenience function that stalls the control endpoint zero.
        """

        self.stall_endpoint(0, direction)


    def service_irqs(self):
        """
        Core routine of the Facedancer execution/event loop. Continuously monitors the
        Moondancer's execution status, and reacts as events occur.
        """

        # poll manually until we decide whether to support NAK events for eptri interface
        # for k, (endpoint_address, max_packet_size, transfer_type) in self.configured_endpoints.items():
        #     is_in = (endpoint_address & 0x80) != 0
        #     if is_in:
        #         endpoint_number = endpoint_address & 0xf
        #         self.connected_device.handle_nak(endpoint_number)

        # Check EP_IN NAK status for pending data requests
        nak_status = self.api.get_nak_status()
        self.handle_ep_in_nak_status(nak_status)

        events = self.api.get_interrupt_events()
        if len(events) == 0:
            return

        # TODO gcp doesn't seem to return a nested tuple if it's only one event
        if isinstance(events[0], int):
            events = [ events ]

        events = list(map(InterruptEvent.parse, events))

        # Handle interrupt events.
        for event in events:
            logging.trace(f"MD IRQ => {event}")
            if event == InterruptEvent.USB_BUS_RESET:
                self.handle_bus_reset()
            elif event == InterruptEvent.USB_RECEIVE_CONTROL:
                self.handle_receive_control(event.endpoint_number)
            elif event == InterruptEvent.USB_RECEIVE_PACKET:
                self.handle_receive_packet(event.endpoint_number)
            elif event == InterruptEvent.USB_SEND_COMPLETE:
                self.handle_send_complete(event.endpoint_number)
            else:
                logging.error(f"Unhandled interrupt event: {event}")


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
    def handle_receive_control(self, endpoint_number):
        """
        Handles a known outstanding control event on a given endpoint.

        endpoint_number: The endpoint number for which a control event should be serviced.
        """

        logging.debug(f"handle_receive_control({endpoint_number})");

        # HACK: to maintain API compatibility with the existing facedancer API,
        # we need to know if a stall happens at any point during our handler.
        self.endpoint_stalled[endpoint_number] = False

        # Read the data from the SETUP stage...
        data    = bytearray(self.api.read_control())
        request = self.connected_device.create_request(data)

        logging.debug(f"  moondancer.api.read_control({endpoint_number}) -> {len(data)} '{request}'")

        # If this is an OUT request, handle the data stage,
        # and add it to the request.
        is_out   = request.get_direction() == Direction.HOST_TO_DEVICE
        has_data = (request.length > 0)
        logging.trace(f"  is_out:{is_out}  has_data:{has_data}")

        # Special case: if this is an OUT request with a data stage, we won't
        # handle the request until the data stage has been completed. Instead,
        # we'll stash away the data received in the setup stage, prime the
        # endpoint for the data stage, and then wait for the data stage to
        # complete, triggering a corresponding code path in
        # in handle_transfer_complete_on_endpoint.
        if is_out and has_data:
            logging.info(f"  setup packet has data - queueing read")
            self.pending_control_request = request
            return

        logging.trace(f"  connected_device.handle_request({request})")
        self.connected_device.handle_request(request)

        if not is_out and not self.endpoint_stalled[endpoint_number]:
            logging.trace(f"  IN packet -> ack_status_stage(DEVICE_TO_HOST) ACK STATUS STAGE")
            self.ack_status_stage(direction=Direction.DEVICE_TO_HOST)


    # USB0_RECEIVE_PACKET
    def handle_receive_packet(self, endpoint_number):
        """
        Handles a known-completed transfer on a given endpoint.

        endpoint_number: The endpoint number for which the transfer should be serviced.
        """

        logging.debug(f"handle_receive_packet({endpoint_number}) pending:{self.pending_control_request}")

        # If we have a pending control request with a data stage...
        # TODO support endpoints other than EP0
        if self.pending_control_request and endpoint_number == 0:

            # Read the rest of the data from the endpoint, completing the control request.
            new_data = self.api.read_endpoint(endpoint_number)

            logging.debug(f"  handling control data stage: {len(new_data)} bytes")

            # Append our new data to the pending control request.
            self.pending_control_request.data.extend(new_data)

            all_data_received = len(self.pending_control_request.data) == self.pending_control_request.length
            is_short_packet   = len(new_data) < self.max_ep0_packet_size

            if all_data_received or is_short_packet:
                # Handle the completed setup request...
                self.connected_device.handle_request(self.pending_control_request)

                # And clear our pending setup data.
                self.pending_control_request = None

            # Finally, prime endpoint to receive next packet.
            self.api.ep_out_prime_receive(endpoint_number)

            return

        # Read the data from the endpoint
        data = self.api.read_endpoint(endpoint_number)

        # Prime endpoint to receive again.
        self.api.ep_out_prime_receive(endpoint_number)

        logging.debug(f"  moondancer.api.read_endpoint({endpoint_number}) -> {len(data)}")

        if len(data) == 0:
            # it's an ack
            logging.trace("  received ACK")
            return

        # Finally, pass it to the device's handler
        self.connected_device.handle_data_available(endpoint_number, data)


    # USB0_SEND_COMPLETE
    def handle_send_complete(self, endpoint_number):
        logging.debug(f"handle_send_complete({endpoint_number})")
        pass

    # Handle pending data requests on EP_IN
    def handle_ep_in_nak_status(self, nak_status):
        nakked_endpoints = [epno for epno in range(self.SUPPORTED_ENDPOINTS) if (nak_status >> epno) & 1]
        for endpoint_number in nakked_endpoints:
            logging.trace(f"Received IN NAK: {endpoint_number}")
            if endpoint_number != 0:
                self.connected_device.handle_nak(endpoint_number)
