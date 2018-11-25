# GreatDancerApp.py

import sys
import time
import codecs
import traceback

from ..core import *
from ..USB import *
from ..USBDevice import USBDeviceRequest
from ..USBEndpoint import USBEndpoint

class GreatDancerApp(FacedancerApp):
    """
    Backend for using GreatFET devices as FaceDancers.
    """

    app_name = "GreatDancer"
    app_num = 0x00 # This doesn't have any meaning for us.

    # Interrupt register (USBSTS) bits masks.
    USBSTS_D_UI   = (1 <<  0)
    USBSTS_D_URI  = (1 <<  6)
    USBSTS_D_NAKI = (1 << 16)

    # Number of supported USB endpoints.
    # TODO: bump this up when we develop support using USB0 (cables flipped)
    SUPPORTED_ENDPOINTS = 4

    # USB directions
    HOST_TO_DEVICE = 0
    DEVICE_TO_HOST = 1

    # Get status command indexes
    GET_USBSTS         = 0
    GET_ENDPTSETUPSTAT = 1
    GET_ENDPTCOMPLETE  = 2
    GET_ENDPTSTATUS    = 3
    GET_ENDPTNAK       = 4

    # Quirk flags
    QUIRK_MANUAL_SET_ADDRESS = 0x01

    @classmethod
    def appropriate_for_environment(cls, backend_name):
        """
        Determines if the current environment seems appropriate
        for using the GreatDancer backend.
        """

        # Check: if we have a backend name other than greatfet,
        # the user is trying to use something else. Abort!
        if backend_name and backend_name != "greatfet":
            return False

        # If we're not explicitly trying to use something else,
        # see if there's a connected GreatFET.
        try:
            import greatfet
            gf = greatfet.GreatFET()
            return gf.supports_api('greatdancer')
        except ImportError:
            sys.stderr.write("NOTE: Skipping GreatFET-based devices, as the greatfet python module isn't installed.\n")
            return False
        except:
            return False


    def __init__(self, device=None, verbose=0, quirks=None):
        """
        Sets up a new GreatFET-backed Facedancer (GreatDancer) application.

        device: The GreatFET device that will act as our GreatDancer.
        verbose: The verbosity level of the given application.
        """

        import greatfet

        if device is None:
            device = greatfet.GreatFET()

        FacedancerApp.__init__(self, device, verbose)
        self.connected_device = None

        # Grab the raw API object from the GreatFET object.
        # This has the low-level RPCs used for raw USB control.
        self.api = device.apis.greatdancer

        # Initialize a dictionary that will store the last setup
        # whether each endpoint is currently stalled.
        self.endpoint_stalled = {}
        for i in range(self.SUPPORTED_ENDPOINTS):
            self.endpoint_stalled[i] = False

        # Start off by assuming we're not waiting for an OUT control transfer's
        # data stage.  # See _handle_setup_complete_on_endpoint for details.
        self.pending_control_packet_data = None

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


    def init_commands(self):
        """
        API compatibility fucntion; not necessary for GreatDancer.
        """
        pass


    def get_version(self):
        """
        Returns information about the active GreatDancer version.
        """
        # TODO: Return the GreatFET software version, or something indicating
        # the GreatFET API number?
        raise NotImplementedError()


    def ack_status_stage(self, direction=HOST_TO_DEVICE, endpoint_number=0, blocking=False):
        """
            Handles the status stage of a correctly completed control request,
            by priming the appropriate endpint to handle the status phase.

            direction: Determines if we're ACK'ing an IN or OUT vendor request.
                (This should match the direcion of the DATA stage.)
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


    def _generate_endpoint_config_arguments(self, config):
        """
        Generates the data content for an Endpoint Configuration command that will
        set up the GreatDancer's endpoints to match the active configuration.

        config: A USBConfiguration object that represents the configuration being
            applied to the GreatDancer.
        """
        arguments = []

        for interface in config.interfaces:
            for endpoint in interface.endpoints:

                if self.verbose > 0:
                    print ("Setting up endpoint {} (direction={}, transfer_type={})".format(endpoint.number, endpoint.direction, endpoint.transfer_type))

                triple = (endpoint.get_address(), endpoint.max_packet_size, endpoint.transfer_type,)
                arguments.append(triple)

        return arguments


    def connect(self, usb_device, max_ep0_packet_size=64):
        """
        Prepares the GreatDancer to connect to the target host and emulate
        a given device.

        usb_device: The USBDevice object that represents the device to be
            emulated.
        """

        quirks = 0

        # Compute our quirk flags.
        if 'manual_set_address' in self.quirks:
            if self.verbose > 0:
                print("Handling SET_ADDRESS on the host side!")

            quirks |= self.QUIRK_MANUAL_SET_ADDRESS

        self.api.connect(max_ep0_packet_size, quirks)
        self.connected_device = usb_device

        if self.verbose > 0:
            print(self.app_name, "connected device", self.connected_device.name)


    def disconnect(self):
        """ Disconnects the GreatDancer from its target host. """
        self.api.disconnect()


    def _wait_until_ready_to_send(self, ep_num):

        # If we're already ready, we don't need to do anything. Abort.
        if self._is_ready_for_priming(ep_num, self.DEVICE_TO_HOST):
            return

        # Otherwise, wait until we're ready to send...
        while not self._is_ready_for_priming(ep_num, self.DEVICE_TO_HOST):
            pass

        # ... and since we've blocked the app from cleaning up any transfer
        # descriptors automatically by spinning in this thread, we'll clean up
        # the relevant transfers here.
        self._clean_up_transfers_for_endpoint(ep_num, self.DEVICE_TO_HOST)


    def send_on_endpoint(self, ep_num, data, blocking=True):
        """
        Sends a collection of USB data on a given endpoint.

        ep_num: The number of the IN endpoint on which data should be sent.
        data: The data to be sent.
        blocking: If true, this function will wait for the transfer to complete.
        """
        if self.verbose > 3:
            print("sending on {}: {}".format(ep_num, data))

        self._wait_until_ready_to_send(ep_num)
        self.api.send_on_endpoint(ep_num, bytes(data))

        # If we're blocking, wait until the transfer completes.
        if blocking:
            while not self._transfer_is_complete(ep_num, self.DEVICE_TO_HOST):
                pass

        self._clean_up_transfers_for_endpoint(ep_num, self.DEVICE_TO_HOST)


    def read_from_endpoint(self, ep_num):
        """
        Reads a block of data from the given endpoint.

        ep_num: The number of the OUT endpoint on which data is to be rx'd.
        """

        # Start a nonblocking read from the given endpoint...
        self._prime_out_endpoint(ep_num)

        # ... and wait for the transfer to complete.
        while not self._transfer_is_complete(ep_num, self.HOST_TO_DEVICE):
            pass

        # Finally, return the result.
        return self._finish_primed_read_on_endpoint(ep_num)


    @staticmethod
    def _endpoint_address(ep_num, direction):
        """
        Returns the endpoint number that corresponds to a given directio
        and address.
        """
        if direction:
            return ep_num | 0x80
        else:
            return ep_num


    def stall_endpoint(self, ep_num, direction=0):
        """
        Stalls the provided endpoint, as defined in the USB spec.

        ep_num: The number of the endpoint to be stalled.
        """

        if self.verbose > 2:
            in_vs_out = "IN" if direction else "OUT"
            print("Stalling EP{} {}".format(ep_num, in_vs_out))

        self.endpoint_stalled[ep_num] = True
        self.api.stall_endpoint(self._endpoint_address(ep_num, direction))


    def stall_ep0(self):
        """
        Conveneince function that stalls the control endpoint zero.
        """
        self.stall_endpoint(0)


    def set_address(self, address, defer=False):
        """
        Sets the device address of the GreatDancer. Usually only used during
        initial configuration.

        address: The address that the GreatDancer should assume.
        defer: True iff the set_addres request should wait for an active transaction to finish.
        """

        self.api.set_address(address, 1 if defer else 0)


    @staticmethod
    def _decode_usb_register(transfer_result):
        """
        Decodes a raw 32-bit register value from a form encoded
        for transit as a USB control request.

        transfer_result: The value returned by the vendor request.
        returns: The raw integer value of the given register.
        """
        status_hex = codecs.encode(transfer_result[::-1], 'hex')
        return int(status_hex, 16)


    def _fetch_irq_status(self):
        """
        Fetch the USB controller's pending-IRQ bitmask, which indicates
        which interrupts need to be serviced.

        returns: A raw integer bitmap.
        """
        return self.api.get_status(self.GET_USBSTS)


    def _fetch_setup_status(self):
        """
        Fetch the USB controller's "pending setup packet" bitmask, which
        indicates which endpoints have setup packets to be read.

        returns: A raw integer bitmap.
        """
        return self.api.get_status(self.GET_ENDPTSETUPSTAT)


    def _handle_setup_events(self):
        """
        Handles any outstanding setup events on the USB controller.
        """

        # Determine if we have setup packets on any of our endpoints.
        status = self._fetch_setup_status()

        # If we don't, abort.
        if not status:
            return

        # Otherwise, figure out which endpoints have outstanding setup events,
        # and handle them.
        for i in range(self.SUPPORTED_ENDPOINTS):
            if status & (1 << i):
                self._handle_setup_event_on_endpoint(i)


    def _handle_setup_event_on_endpoint(self, endpoint_number):
        """
        Handles a known outstanding setup event on a given endpoint.

        endpoint_number: The endpoint number for which a setup event should be serviced.
        """

        # HACK: to maintain API compatibility with the existing facedancer API,
        # we need to know if a stall happens at any point during our handler.
        self.endpoint_stalled[endpoint_number] = False

        # Read the data from the SETUP stage...
        data = self.api.read_setup(endpoint_number)
        request = USBDeviceRequest(data)

        # If this is an OUT request, handle the data stage,
        # and add it to the request.
        is_out   = request.get_direction() == self.HOST_TO_DEVICE
        has_data = (request.length > 0)

        # Special case: if this is an OUT request with a data stage, we won't
        # handle the request until the data stage has been complete. Instead,
        # we'll stash away the data recieved in the setup stage, prime the
        # endpoint for the data stage, and then wait for the data stage to
        # complete, triggering a corresponding code path in
        # in _handle_transfer_complete_on_endpoint.
        if is_out and has_data:
            self._prime_out_endpoint(endpoint_number)
            self.pending_control_packet_data = data
            return

        request = USBDeviceRequest(data)
        self.connected_device.handle_request(request)

        if not is_out and not self.endpoint_stalled[endpoint_number]:
            self.ack_status_stage(direction=self.DEVICE_TO_HOST)


    def _fetch_transfer_status(self):
        """
        Fetch the USB controller's "completed transfer" bitmask, which
        indicates which endpoints have recently completed transactions.

        returns: A raw integer bitmap.
        """
        return self.api.get_status(self.GET_ENDPTCOMPLETE)


    def _transfer_is_complete(self, endpoint_number, direction):
        """
        Returns true iff a given endpoint has just completed a transfer.
        Can be used to check for completion of a non-blocking transfer.

        endpoint_number: The endpoint number to be queried.
        direction:
            The direction of the transfer. Should be self.HOST_TO_DEVICE or
            self.DEVICE_TO_HOST.
        """
        status = self._fetch_transfer_status()

        # From the LPC43xx manual: out endpoint completions start at bit zero,
        # while in endpoint completions start at bit 16.
        out_is_ready = (status & (1 << endpoint_number))
        in_is_ready  = (status & (1 << (endpoint_number + 16)))

        if direction == self.HOST_TO_DEVICE:
            return out_is_ready
        else:
            return in_is_ready


    def _handle_transfer_events(self):
        """
        Handles any outstanding setup events on the USB controller.
        """

        # Determine if we have ready packets on any of our endpoints.
        status = self._fetch_transfer_status()

        # If we don't, abort.
        if not status:
            return

        if self.verbose > 5:
            print("Out status: {}".format(bin(status & 0x0F)))
            print("IN status: {}".format(bin(status >> 16)))

        # Figure out which endpoints have recently completed transfers,
        # and clean up any transactions on those endpoints. It's important
        # that this be done /before/ the _handle_transfer_complete... section
        # below, as those can generate further events which will need the freed
        # transfer descriptors.
        # [Note that it's safe to clean up the transfer descriptors before reading,
        #  here-- the GreatFET's USB controller has transparently moved any data
        #  from OUT transactions into a holding buffer for us. Nice of it!]
        for i in range(self.SUPPORTED_ENDPOINTS):
            if status & (1 << i):
                self._clean_up_transfers_for_endpoint(i, self.HOST_TO_DEVICE)

            if status & (1 << (i + 16)):
                self._clean_up_transfers_for_endpoint(i, self.DEVICE_TO_HOST)

        # Now that we've cleaned up all relevant transfer descriptors, trigger
        # any events that should occur due to the completed transaction.
        for i in range(self.SUPPORTED_ENDPOINTS):
            if status & (1 << i):
                self._handle_transfer_complete_on_endpoint(i, self.HOST_TO_DEVICE)

            if status & (1 << (i + 16)):
                self._handle_transfer_complete_on_endpoint(i, self.DEVICE_TO_HOST)


        # Finally, after completing all of the above, we may now have idle
        # (unprimed) endpoints. For OUT endpoints, we'll need to re-prime them
        # so we're ready for reciept; for IN endpoints, we'll want to give the
        # emulated device a chance to provide new data.
        self._handle_transfer_readiness()


    def _finish_primed_read_on_endpoint(self, endpoint_number):
        """
        Completes a non-blocking (primed) read on an OUT endpoint by reading any data
        received since the endpoint was primed. See read_from_endpoint for an example
        of proper use.

        endpoint_number: The endpoint to read from.
        """

        return self.api.finish_nonblocking_read(endpoint_number)


    def _clean_up_transfers_for_endpoint(self, endpoint_number, direction):
        """
        Cleans up any outstanding transfers on the given endpoint. This must be
        called for each completed transaction so the relevant transfer descriptors
        can be re-used.

        There's no harm in calling this if a transaction isn't complete, but it _must_
        be called at least once for each completed transaction.

        endpoint_number: The endpoint number whose transfer desctiprots should be cleaned
            up.
        direction: The endpoint direction for which TD's should be cleaned.
        """

        if self.verbose > 5:
            print("Cleaning up transfers on {}".format(endpoint_number))

        # Ask the device to clean up any transaction descriptors related to the transfer.
        self.api.clean_up_transfer(self._endpoint_address(endpoint_number, direction))


    def _is_control_endpoint(self, endpoint_number):
        """
        Returns true iff the given endpoint number corresponds to a control endpoint.
        """

        # FIXME: Support control endpoints other than EP0.
        return endpoint_number == 0


    def _handle_transfer_complete_on_endpoint(self, endpoint_number, direction):
        """
        Handles a known-compelted transfer on a given endpoint.

        endpoint_number: The endpoint number for which a setup event should be serviced.
        """

        # If a transfer has just completed on an OUT endpoint, we've just received data
        # that we need to handle.
        if direction == self.HOST_TO_DEVICE:

            # Special case: if we've just recieved data on a control endpoint,
            # we're completing a control request.
            if self._is_control_endpoint(endpoint_number):

                # If we recieved a setup packet to handle, handle it.
                if self.pending_control_packet_data:

                    # Read the rest of the data from the endpoint, completing
                    # the control request.
                    new_data = self._finish_primed_read_on_endpoint(endpoint_number)
                    data     = self.pending_control_packet_data[:]

                    # Build a new control request packet from the setup data
                    # and the request body.
                    data.extend(new_data)
                    request = USBDeviceRequest(data)

                    # Handle the setup request...
                    self.connected_device.handle_request(request  )

                    # And clear our pending setup data.
                    self.pending_control_packet_data = None

            # Typical case: this isn't a control endpoint, so we don't have a
            # defined packet format. Read the data and issue the corresponding
            # callback.
            else:
                data = self._finish_primed_read_on_endpoint(endpoint_number)
                self.connected_device.handle_data_available(endpoint_number, data)


    def _fetch_transfer_readiness(self):
        """
        Queries the GreatFET for a bitmap describing the endpoints that are not
        currently primed, and thus ready to be primed again.
        """
        return self.api.get_status(self.GET_ENDPTSTATUS)


    def _fetch_endpoint_nak_status(self):
        """
        Queries the GreatFET for a bitmap describing the endpoints that have issued
        a NAK since the last time this was checked.
        """
        return self.api.get_status(self.GET_ENDPTNAK)


    def _prime_out_endpoint(self, endpoint_number):
        """
        Primes an out endpoint, allowing it to recieve data the next time the host chooses to send it.

        endpoint_number: The endpoint that should be primed.
        """
        self.api.start_nonblocking_read(endpoint_number)


    def _handle_transfer_readiness(self):
        """
        Check to see if any non-control IN endpoints are ready to
        accept data from our device, and handle if they are.
        """

        # If we haven't been configured yet, we can't have any
        # endpoints other than the control endpoint, and we don't n
        if not self.configuration:
            return

        # Fetch the endpoint status.
        status = self._fetch_transfer_readiness()

        # Check the status of every endpoint /except/ endpoint zero,
        # which is always a control endpoint and set handled by our
        # control transfer handler.
        for interface in self.configuration.interfaces:
            for endpoint in interface.endpoints:

                # Check to see if the endpoint is ready to be primed.
                if self._is_ready_for_priming(endpoint.number, endpoint.direction):

                    # If this is an IN endpoint, we're ready to accept data to be
                    # presented on the next IN token.
                    if endpoint.direction == USBEndpoint.direction_in:
                        self.connected_device.handle_buffer_available(endpoint.number)

                    # If this is an OUT endpoint, we'll need to prime the endpoint to
                    # accept new data. This provides a place for data to go once the
                    # host sends an OUT token.
                    else:
                        self._prime_out_endpoint(endpoint.number)


    def _is_ready_for_priming(self, ep_num, direction):
        """
        Returns true iff the endpoint is ready to be primed.

        ep_num: The endpoint number in question.
        direction: The endpoint direction in question.
        """

        # Fetch the endpoint status.
        status = self._fetch_transfer_readiness()

        ready_for_in  = (not status & (1 << (ep_num + 16)))
        ready_for_out = (not status & (1 << (ep_num)))

        if direction == self.HOST_TO_DEVICE:
            return ready_for_out
        else:
            return ready_for_in


    @classmethod
    def _has_issued_nak(cls, ep_nak, ep_num, direction):
        """
        Interprets an ENDPTNAK status result to determine
        whether a given endpoint has NAK'd.

        ep_nak: The status work read from the ENDPTNAK register
        ep_num: The endpoint number in question.
        direction: The endpoint direction in question.
        """

        in_nak  = (ep_nak & (1 << (ep_num + 16)))
        out_nak = (ep_nak & (1 << (ep_num)))

        if direction == cls.HOST_TO_DEVICE:
            return out_nak
        else:
            return in_nak


    def _bus_reset(self):
        """
        Triggers the GreatDancer to perform its side of a bus reset.
        """

        if self.verbose > 0:
            print("-- Reset requested! --")

        self.api.bus_reset()


    def _handle_nak_events(self):
        """
        Handles an event in which the GreatDancer has NAK'd an IN token.
        """

        # If we haven't been configured yet, we can't have any
        # endpoints other than the control endpoint, and we don't need to
        # handle any NAKs.
        if not self.configuration:
            return

        # Fetch the endpoint status.
        status = self._fetch_endpoint_nak_status()

        # Iterate over each usable endpoint.
        for interface in self.configuration.interfaces:
            for endpoint in interface.endpoints:

                # If the endpoint has NAK'd, issued the relevant callback.
                if self._has_issued_nak(status, endpoint.number, endpoint.direction):
                    self.connected_device.handle_nak(endpoint.number)



    def _configure_endpoints(self, configuration):
        """
        Configures the GreatDancer's endpoints to match the provided configuration.

        configurate: The USBConfigruation object that describes the endpoints provided.
        """
        endpoint_triplets = self._generate_endpoint_config_arguments(configuration)

        # If we need to issue a configuration command, issue one.
        # (If there are no endpoints other than control, this command will be
        #  empty, and we can skip this.)
        if endpoint_triplets:
            self.api.set_up_endpoints(*endpoint_triplets)


    def configured(self, configuration):
        """
        Callback that's issued when a USBDevice is configured, e.g. by the
        SET_CONFIGRUATION request. Allows us to apply the new configuration.

        configuration: The configruation applied by the SET_CONFIG request.
        """
        self._configure_endpoints(configuration)
        self.configuration = configuration

        # If we've just set up endpoints, check to see if any of them
        # need to be primed, or have NAKs waiting.
        self._handle_transfer_readiness()
        self._handle_nak_events()


    def service_irqs(self):
        """
        Core routine of the Facedancer execution/event loop. Continuously monitors the
        GreatDancer's execution status, and reacts as events occur.
        """

        status = self._fetch_irq_status()

        # Other bits that may be of interest:
        # D_SRI = start of frame received
        # D_PCI = port change detect (switched between low, full, high speed state)
        # D_SLI = device controller suspend
        # D_UEI = USB error; completion of transaction caused error, see usb1_isr in firmware
        # D_NAKI = both the tx/rx NAK bit and corresponding endpoint NAK enable are set

        if status & self.USBSTS_D_UI:
            self._handle_setup_events()
            self._handle_transfer_events()

        if status & self.USBSTS_D_URI:
            self._bus_reset()

        if status & self.USBSTS_D_NAKI:
            self._handle_nak_events()

