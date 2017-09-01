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

    def __init__(self, device, verbose=0):
        self.device = device
        self.configuration = None
        self.verbose = verbose

    def filter_control_in(self, req, data, stalled):

        # FIXME: replace Dominic's wonderful shotgun parser :)

        if stalled:
            return req, data, stalled

        if req.request == self.GET_DESCRIPTOR_REQUEST and \
           req.value == 0x0200 and req.length >= 32:
            cfg = data[:data[0]]
            rest = data[data[0]:]
            iface = rest[:rest[0]]
            rest = rest[rest[0]:]
            x = iface[4]
            eps = []
            while x:
                eps.append(rest[:rest[0]])
                rest = rest[rest[0]:]
                x -= 1
            endpoints = [
                USBEndpoint(
                    ep[2],
                    (ep[2]&0x80)>>7,
                    ep[3]&0x03,
                    (ep[3]>>2)&0x03,
                    (ep[3]>>4)&0x03,
                    ep[4] | ep[5]<<8,
                    ep[6],
                    None
                )
                for ep in eps
            ]
            interface = USBInterface(
                iface[2],
                iface[3],
                iface[5],
                iface[6],
                iface[7],
                iface[8],
                endpoints = endpoints
            )

            self.configuration = USBConfiguration(
                cfg[5],
                "",
                [interface]
            )
            if self.verbose > 1:
                print("-- Storing configuration: {} --".format(self.configuration))

        return req, data, stalled

    def filter_control_out(self, req, data):
        # Special case: if this is a SET_ADDRESS request,
        # handle it ourself, and absorb it.
        if req.get_recipient() == self.RECIPIENT_DEVICE and \
           req.request == self.SET_ADDRESS_REQUEST:
            self.device.handle_set_address_request(req)
            return None, None

        if req.get_recipient() == self.RECIPIENT_DEVICE and \
           req.request == self.SET_CONFIGURATION_REQUEST:
            if self.configuration and self.verbose > 1:
                print("-- Applying configuration {} --".format(self.configuration))
            elif self.verbose > 0:
                print("-- WARNING: no configuration to apply! --")

            if self.configuration:
                self.device.maxusb_app.configured(self.configuration)
        return req, data
