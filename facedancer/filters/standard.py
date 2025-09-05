#
# This file is part of Facedancer.
#
""" Standard filters for USBProxy that should (almost) always be used. """

from ..            import *
from ..descriptor  import USBDescribable
from ..errors      import *
from ..logging     import log

from .             import USBProxyFilter


class USBProxySetupFilters(USBProxyFilter):
    SET_ADDRESS_REQUEST = 5
    SET_CONFIGURATION_REQUEST = 9
    SET_INTERFACE_REQUEST = 11
    GET_DESCRIPTOR_REQUEST = 6
    RECIPIENT_DEVICE = 0
    RECIPIENT_INTERFACE = 1

    DESCRIPTOR_DEVICE        = 0x01
    DESCRIPTOR_CONFIGURATION = 0x02

    MAX_PACKET_SIZE_EP0 = 64

    configurations: dict[int, USBDescriptor]

    def __init__(self, device, verbose=0):
        self.device = device
        self.configurations = {}
        self.verbose = verbose

    def filter_control_in(self, req, data, stalled):

        if stalled:
            return req, data, stalled

        # If this is a read of a valid configuration descriptor (and subordinate
        # descriptors, parse them and store the results for later).
        if req.request == self.GET_DESCRIPTOR_REQUEST:

            # Get the descriptor type and index.
            descriptor_type  = req.value >> 8
            descriptor_index = req.value & 0xFF

            # If this is a configuration descriptor, store information relevant
            # to the configuration. We'll need this to set up the endpoint
            # hardware on the facedancer device.
            if descriptor_type == self.DESCRIPTOR_CONFIGURATION and req.length >= 32:
                configuration = USBDescribable.from_binary_descriptor(data)
                self.configurations[configuration.number] = configuration
                if self.verbose > 2:
                    log.info("-- Storing configuration {} --".format(configuration))


            if descriptor_type == self.DESCRIPTOR_DEVICE and req.length >= 7:
                # Patch our data to overwrite the maximum packet size on EP0.
                # See USBProxy.connect for a rationale on this.
                device = USBDescribable.from_binary_descriptor(data)
                old = device.max_packet_size_ep0
                if old != 64:
                    device.max_packet_size_ep0 = 64
                    data = bytearray(device.get_descriptor())[:len(data)]
                    if self.verbose > 0:
                        log.info(f"-- Patched device descriptor. max_packet_size_ep0 {old} to 64 --")

        return req, data, stalled


    def filter_control_out(self, req, data):
        # Special case: if this is a SET_ADDRESS request,
        # handle it ourself, and absorb it.
        if req.get_recipient() == self.RECIPIENT_DEVICE and \
           req.request == self.SET_ADDRESS_REQUEST:
            log.info(f"setup: out - handle set_address {req}")
            req.acknowledge(blocking=True)
            self.device.set_address(req.value)
            return None, None

        # Special case: SET_CONFIGURATION_REQUEST
        # libusb1 recommends always calling setConfiguration() instead
        # of sending the control packet manually
        if req.get_recipient() == self.RECIPIENT_DEVICE and \
           req.request == self.SET_CONFIGURATION_REQUEST:
            configuration_index = req.value

            # If we have a known configuration for this index, apply it.
            if configuration_index in self.configurations:
                configuration = self.configurations[configuration_index]

                if self.verbose > 2:
                    log.info("-- Applying configuration {} --".format(configuration))
                elif self.verbose > 0:
                    log.info(f"-- Applying configuration {configuration.get_identifier()} --")

                self.device.configured(configuration)

            # Otherwise, the host has applied a configuration without ever reading
            # its descriptor. This is mighty strange behavior!
            else:
                log.warning("-- WARNING: Applying configuration {}, but we've never read that configuration's descriptor! --".format(configuration_index))

            return None, None

        # Special case: SET_INTERFACE_REQUEST
        # libusb1 recommends calling setInterfaceAlternative()
        if req.get_recipient() == self.RECIPIENT_INTERFACE and \
           req.request == self.SET_INTERFACE_REQUEST:
            interface_number = req.index
            alternate = req.value
            log.info(f"setup: out - handle SET_INTERFACE_REQUEST {req}")
            self.device.interface_changed(interface_number, alternate)

            return None, None

        return req, data
