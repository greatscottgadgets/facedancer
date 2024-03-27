#!/usr/bin/env python3
# pylint: disable=unused-wildcard-import, wildcard-import
#
# This file is part of FaceDancer.
#

import logging

from facedancer import *
from facedancer import main

@use_inner_classes_automatically
class MyDevice(USBDevice):
    product_string      : str = "Example USB Device"
    manufacturer_string : str = "Facedancer"
    vendor_id           : int = 0x1209
    product_id          : int = 0x0001
    device_speed        : DeviceSpeed = DeviceSpeed.FULL

    class MyConfiguration(USBConfiguration):

        class MyInterface(USBInterface):

            class MyInEndpoint(USBEndpoint):
                number          : int          = 1
                direction       : USBDirection = USBDirection.IN
                max_packet_size : int          = 64

                def handle_data_requested(self: USBEndpoint):
                    logging.info("handle_data_requested")
                    self.send(b"device on bulk endpoint")

            class MyOutEndpoint(USBEndpoint):
                number          : int          = 1
                direction       : USBDirection = USBDirection.OUT
                max_packet_size : int          = 64

                def handle_data_received(self: USBEndpoint, data):
                    logging.info(f"device received {data} on bulk endpoint")

    @vendor_request_handler(number=1, direction=USBDirection.IN)
    @to_device
    def my_in_vendor_request_handler(self: USBDevice, request: USBControlRequest):
        logging.info("my_in_vendor_request_handler")
        request.reply(b"device on control endpoint")

    @vendor_request_handler(number=2, direction=USBDirection.OUT)
    @to_device
    def my_out_vendor_request_handler(self: USBDevice, request: USBControlRequest):
        logging.info(f"device received {request.index} {request.value} {bytes(request.data)} on control endpoint")
        request.ack()


main(MyDevice)
