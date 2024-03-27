#!/usr/bin/env python3
# pylint: disable=unused-wildcard-import, wildcard-import
#
# This file is part of FaceDancer.
#

import logging

from facedancer import *
from facedancer import main

from base import VENDOR_ID, PRODUCT_ID, OUT_ENDPOINT, IN_ENDPOINT

DEVICE_SPEED = DeviceSpeed.FULL

@use_inner_classes_automatically
class StressTestDevice(USBDevice):
    product_string      : str = "Stress Test Device"
    manufacturer_string : str = "Facedancer"
    vendor_id           : int = VENDOR_ID
    product_id          : int = PRODUCT_ID
    device_speed        : DeviceSpeed = DEVICE_SPEED

    def __post_init__(self):
        self.in_transfer_length = 32
        self.last_out_transfer_data = bytearray()

        super().__post_init__()

    class MyConfiguration(USBConfiguration):

        class MyInterface(USBInterface):

            class MyOutEndpoint(USBEndpoint):
                number          : int          = OUT_ENDPOINT
                direction       : USBDirection = USBDirection.OUT
                max_packet_size : int          = 512 if DEVICE_SPEED == DeviceSpeed.HIGH else 64

                def handle_data_received(self: USBEndpoint, data):
                    self.get_device().last_out_transfer_data += bytes(data)
                    logging.info(f"device received {len(data)} bytes on bulk endpoint")

            class MyInEndpoint(USBEndpoint):
                number          : int          = IN_ENDPOINT & 0x7f
                direction       : USBDirection = USBDirection.IN
                max_packet_size : int          = 512 if DEVICE_SPEED == DeviceSpeed.HIGH else 64

                def handle_data_requested(self: USBEndpoint):
                    in_transfer_length = self.get_device().in_transfer_length
                    logging.info(f"device sending {in_transfer_length} bytes on bulk endpoint")
                    self.send(generate_data(in_transfer_length), blocking=False)

    @vendor_request_handler(number=10, direction=USBDirection.OUT)
    @to_device
    def out_vendor_request(self: USBDevice, request: USBControlRequest):
        self.last_out_transfer_data += bytes(request.data)
        length = int.from_bytes([request.index, request.value], byteorder="big")
        logging.info(f"device received {len(request.data)}/{length} bytes on control endpoint")
        request.ack()

    @vendor_request_handler(number=20, direction=USBDirection.IN)
    @to_device
    def in_vendor_request(self: USBDevice, request: USBControlRequest):
        length = int.from_bytes([request.index, request.value], byteorder="big")
        logging.info(f"device sending {length}/{self.in_transfer_length} bytes on control endpoint")
        request.reply(generate_data(self.in_transfer_length))

    # - device control --------------------------------------------------------

    @vendor_request_handler(number=1, direction=USBDirection.OUT)
    @to_device
    def set_in_transfer_length(self: USBDevice, request: USBControlRequest):
        length = int.from_bytes([request.index, request.value], byteorder="big")
        self.in_transfer_length = length
        logging.info(f"set_in_transfer_length: {length} bytes")
        request.ack()

    @vendor_request_handler(number=2, direction=USBDirection.IN)
    @to_device
    def get_last_out_transfer_data(self: USBDevice, request: USBControlRequest):
        logging.info(f"get_last_out_transfer_data: {len(self.last_out_transfer_data)} bytes")
        request.reply(self.last_out_transfer_data)
        self.last_out_transfer_data = bytearray()

    @vendor_request_handler(number=3, direction=USBDirection.OUT)
    @to_device
    def clear_last_out_transfer_data(self: USBDevice, request: USBControlRequest):
        logging.info(f"clear_last_out_transfer_data: {len(self.last_out_transfer_data)} bytes")
        self.last_out_transfer_data = bytearray()
        request.ack()

# - helpers -------------------------------------------------------------------

def generate_data(length):
    return bytes([(byte % 256) for byte in range(length)])


if __name__ == "__main__":
    main(StressTestDevice)
