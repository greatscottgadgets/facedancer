#!/usr/bin/env python3
# pylint: disable=unused-wildcard-import, wildcard-import
#
# This file is part of FaceDancer.
#

import logging

from facedancer import *
from facedancer import main

# TODO some way to declare device speed

@use_inner_classes_automatically
class MyDevice(USBDevice):
    product_string      : str = "Example USB Device"
    manufacturer_string : str = "Facedancer"
    vendor_id           : int = 0x1209
    product_id          : int = 0x0001

    class MyConfiguration(USBConfiguration):

        class MyInterface(USBInterface):

            class MyInEndpoint(USBEndpoint):
                number    : int          = 1
                direction : USBDirection = USBDirection.IN

                def handle_data_requested(self: USBEndpoint):
                    self.send(b"device sent response on bulk endpoint", blocking=True)

            class MyOutEndpoint(USBEndpoint):
                number    : int          = 1
                direction : USBDirection = USBDirection.OUT

                def handle_data_received(self: USBEndpoint, data):
                    logging.info(f"device received '{data}' on bulk endpoint")

    @vendor_request_handler(number=1, direction=USBDirection.IN)
    @to_device
    def my_vendor_request_handler(self: USBDevice, request: USBControlRequest):
        request.reply(b"device sent response on control endpoint")

    @vendor_request_handler(number=2, direction=USBDirection.OUT)
    @to_device
    def my_other_vendor_request_handler(self: USBDevice, request: USBControlRequest):
        logging.info(f"device received '{request.index}' '{request.value}' '{request.data}' on control endpoint")
        request.ack()


main(MyDevice)
