#
# Standard filters for USBProxy that should (almost) always be used
#

from ..USBProxy import USBProxyFilter

from ..USB import *
from ..USBDevice import *
from ..USBConfiguration import *
from ..USBInterface import *
from ..USBEndpoint import *
from ..USBVendor import *
from ..errors import *


class USBProxySetupFilters(USBProxyFilter):

    SET_ADDRESS_REQUEST = 5
    SET_CONFIGURATION_REQUEST = 9
    GET_DESCRIPTOR_REQUEST = 6
    RECIPIENT_DEVICE = 0

    DESCRIPTOR_CONFIRGUATION = 0x02

    def __init__(self, device, verbose=0):
        self.device = device
        self.configurations = {}
        self.verbose = verbose

    def filter_control_in(self, req, data, stalled):

        if stalled:
            return req, data, stalled


        # If this is a read of a valid configuration descriptor (and subordinate
        # descriptors, parse them and store the results for late).
        if req.request == self.GET_DESCRIPTOR_REQUEST:

            # Get the descriptor type and index.
            descriptor_type  = req.value >> 8
            descriptor_index = req.value & 0xFF

            # If this is a configuration descriptor, store information relevant
            # to the configuration. We'll need this to set up the endpoint
            # hardware on the facedancer device.
            if descriptor_type == self.DESCRIPTOR_CONFIRGUATION and req.length >= 32:
                configuration = USBDescribable.from_binary_descriptor(data)
                self.configurations[configuration.configuration_index] = configuration

                if self.verbose > 1:
                    print("-- Storing configuration {} --".format(configuration))


        return req, data, stalled


    def filter_control_out(self, req, data):
        # Special case: if this is a SET_ADDRESS request,
        # handle it ourself, and absorb it.
        if req.get_recipient() == self.RECIPIENT_DEVICE and \
           req.request == self.SET_ADDRESS_REQUEST:
            self.device.handle_set_address_request(req)
            return None, None

        # Special case: if this is a SET_CONFIGURATION_REQUEST,
        # pass it through, but also set up the Facedancer hardware
        # in response.
        if req.get_recipient() == self.RECIPIENT_DEVICE and \
           req.request == self.SET_CONFIGURATION_REQUEST:
            configuration_index = req.value

            # If we have a known configuration for this index, apply it.
            if configuration_index in self.configurations:
                configuration = self.configurations[configuration_index]

                if self.verbose > 0:
                    print("-- Applying configuration {} --".format(configuration))

                self.device.configured(configuration)

            # Otherwise, the host has applied a configruation without ever reading
            # its descriptor. This is mighty strange behavior!
            elif self.verbose > 0:
                print("-- WARNING: Applying configuration {}, but we've never read that configuration's descriptor! --".format(configuration_index))

        return req, data
