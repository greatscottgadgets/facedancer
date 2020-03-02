#!/usr/bin/env python3
#
# This file is part of FaceDancer.
#

from facedancer             import main
from facedancer.future      import USBDevice, USBConfiguration, USBInterface, USBEndpoint
from facedancer.future      import use_inner_classes_automatically, vendor_request_handler


@use_inner_classes_automatically
class HackRF(USBDevice):

    # Show up as a HackRF.
    name                : str = "HackRF One"
    product_string      : str = "HackRF One"
    manufacturer_string : str = "Great Scott Gadgets"

    vendor_id      : int = 0x1d50
    product_id     : int = 0x6089

    class DefaultConfiguration(USBConfiguration):
        class DefaultInterface(USBInterface):
            pass


main(HackRF)
