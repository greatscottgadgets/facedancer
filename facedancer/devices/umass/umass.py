# USBMassStorage.py
#
# Contains class definitions to implement a USB mass storage device.
#
""" Emulation of a USB Mass storage device. """

import asyncio
import os
import re
import struct
import sys
import time

from enum   import IntFlag
from typing import Union

from ..         import default_main

from ...        import *
from ...classes import USBDeviceClass

from ...logging import log


ENDPOINT_OUT = 1
ENDPOINT_IN  = 3

@use_inner_classes_automatically
class USBMassStorageDevice(USBDevice):
    """ Class implementing an emulated USB Mass Storage device. """

    name                 : str = "USB mass storage interface"

    vendor_id            : int = 0x8107 # Sandisk
    product_id           : int = 0x5051 # SDCZ2 Cruzer Mini Flash Drive (thin)
    device_revision      : int = 0x0003

    manufacturer_string  : str = "Facedancer"
    product_string       : str = "USB Mass Storage emulation"

    max_packet_size_ep0  : int = 64


    class _Configuration(USBConfiguration):
        configuration_string : str = "Mass Storage config"

        class _Interface(USBInterface):

            # This is a Mass Storage Class device
            class_number    : int = USBDeviceClass.MASS_STORAGE
            subclass_number : int = 0x06 # SCSI transparent command set
            protocol_number : int = 0x50 # bulk-only (BBB) transport

            class _OutEndpoint(USBEndpoint):
                number          : int             = ENDPOINT_OUT
                direction       : USBDirection    = USBDirection.OUT
                transfer_type   : USBTransferType = USBTransferType.BULK
                max_packet_size : int             = 64

            class _InEndpoint(USBEndpoint):
                number        : int               = ENDPOINT_IN
                direction     : USBDirection      = USBDirection.IN
                transfer_type : USBTransferType   = USBTransferType.BULK
                max_packet_size : int             = 64


    def __init__(self, disk_image):
        self.disk_image = disk_image

        super().__init__()


    #
    # Device overrides
    #

    def connect(self):
        super().connect()

        # instantiate our SCSI command handler
        self.scsi_command_handler = ScsiCommandHandler(self, self.disk_image, verbose=3)


    def disconnect(self):
        super().disconnect()

        # close our disk image
        self.disk_image.close()


    def handle_data_received(self, endpoint, data):
        if endpoint.number == ENDPOINT_OUT:
            # dispatch received data to our SCSI command handler
            self.scsi_command_handler.handle_data_received(data)
        else:
            log.warning(f"Received data on unexpected endpoint: {endpoint}")


    #
    # Class Request handlers.
    #

    @class_request_handler(number=254, direction=USBDirection.IN)
    @to_this_interface
    def handle_get_max_lun_request(self, request):
        request.reply(b'\x00')

    @class_request_handler(number=255, direction=USBDirection.IN)
    @to_this_interface
    def handle_bulk_only_mass_storage_reset_request(self, request):
        request.reply(b'')

    # TODO is this an internal event handler maybe?
    async def wait_for_host(self):
        """ Waits until the host connects by TODO. """

        while not True:
            await asyncio.sleep(0.1)



def bytes_as_hex(b, delim=" "):
    return delim.join(["%02x" % x for x in b])

class ScsiCommandHandler:
    name : str = "SCSI Command Handler"

    STATUS_OKAY       = 0x00
    STATUS_FAILURE    = 0x02 # TODO: Should this be 0x01?
    STATUS_INCOMPLETE = -1   # Special case status that aborts before response.

    def __init__(self, device, disk_image, verbose=0):
        self.device = device
        self.disk_image = disk_image
        self.verbose = verbose

        self.is_write_in_progress = False
        self.write_cbw = None
        self.write_base_lba = 0
        self.write_length = 0
        self.write_data = b''

        self._register_scsi_commands()


    def handle_data_received(self, data):
        if self.is_write_in_progress:
            cbw = self.write_cbw
            status, response = self.continue_write(cbw, data)
        else:
            cbw = CommandBlockWrapper(data)
            status, response = self.handle_scsi_command(cbw)

        # If we weren't able to complete the operation, return without
        # transmitting a response.
        if status == self.STATUS_INCOMPLETE:
            return

        # If we have a response payload to transmit, transmit it.
        if response:
            if self.verbose > 2:
                print("--> responding with", len(response),
                      "bytes [{}], status={}".format(bytes_as_hex(response), status))

            self.device.send(ENDPOINT_IN, response, blocking=True)

        # Otherwise, respond with our status.
        csw = bytes([
            ord('U'), ord('S'), ord('B'), ord('S'),
            cbw.tag[0], cbw.tag[1], cbw.tag[2], cbw.tag[3],
            0x00, 0x00, 0x00, 0x00,
            status
        ])

        self.device.send(ENDPOINT_IN, csw, blocking=True)


    def handle_scsi_command(self, cbw):
        """
            Handles an SCSI command.
        """

        opcode = cbw.cb[0]
        direction = cbw.flags >> 7

        # If we have a handler for this routine, handle it.
        if opcode in self.commands:

            # Extract the command's data.
            command = self.commands[opcode]
            name    = command['name']
            handler = command['handler']
            direction_name = 'IN' if direction else 'OUT'
            direction_arrow = "<--" if direction else "-->"
            expected_length = cbw.data_transfer_length

            if self.verbose > 0:
                print("{} handling {} ({}) {}:[{}]".format(direction_arrow, name.upper(), direction_name, expected_length, bytes_as_hex(cbw.cb[1:])))

            # Delegate to its handler function.
            return handler(cbw)

        # Otherwise, run the unknown command handler.
        else:
            return self.handle_unknown_command(cbw)


    def handle_unknown_command(self, cbw):
        """
            Handles unsupported SCSI commands.
        """
        print(self.name, "received unsupported SCSI opcode 0x%x" % cbw.cb[0])

        # Generate an empty response to the relevant command.
        if cbw.data_transfer_length > 0:
            response = bytes([0] * cbw.data_transfer_length)
        else:
            response = None

        # Return failure.
        return self.STATUS_FAILURE, response


    def handle_ignored_event(self, cbw):
        """
            Handles SCSI events that we can safely ignore.
        """

        # Always return success, and no response.
        return self.STATUS_OKAY, None


    def handle_sense(self, cbw):
        """
            Handles SCSI sense requests.
        """
        response = b'\x70\x00\xFF\x00\x00\x00\x00\x0A\x00\x00\x00\x00\xFF\xFF\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        return self.STATUS_OKAY, response


    def handle_inquiry(self, cbw):
        opcode, flags, page_code, allocation_length, control = struct.unpack(">BBBHB", cbw.cb[0:6])

        # Print out the details of our inquiry.
        if self.verbose > 1:
            print("-- INQUIRY ({}) flags: {} page_code: {} allocation_length: {} control: {}". \
                  format(opcode, flags, page_code, allocation_length, control))

        response = bytes([
            0x00,       # 0x00 = device present, and provides direct access to blocks
            0x00,       # 0x00 = media not removable, 0x80 = media removable
            0x05,       # 0 = no standards compliance, 3 = SPC compliant, 4 = SPC-2 compliant, 5 = SCSI compliant :)
            0x02,       # 0x02 = data responses follow the spec
            0x14,       # Additional length.
            0x00, 0x00, 0x00
        ])

        response += b'GoodFET '         # vendor
        response += b'GoodFET '         # product id
        response += b'        '         # product revision
        response += b'0.01'

        # pad up to data_transfer_length bytes
        diff = cbw.data_transfer_length - len(response)
        response += bytes([0] * diff)

        return self.STATUS_OKAY, response


    def handle_mode_sense_6(self, cbw):
        page = cbw.cb[2] & 0x3f

        response = b'\x03\x00\x00\x1c'
        if page != 0x3f:
            print(self.name, "unknown page, returning empty page")
            response = b'\x03\x00\x00\x00'

        return self.STATUS_OKAY, response


    def handle_mode_sense_10(self, cbw):
        page = cbw.cb[2] & 0x3f

        response = b'\x07\x00\x00\x00\x00\x00\x00\x1c'
        if page != 0x3f:
            print(self.name, "unknown page, returning empty page")
            response = b'\x07\x00\x00\x00\x00\x00\x00\x00'

        return self.STATUS_OKAY, response


    def handle_service_action_in(self, cbw):
        opcode = cbw.cb[0]

        if opcode == 0x9e:
            return self.handle_get_read_capacity_16(cbw)
        else:
            # Always return success, and no response.
            return self.STATUS_OKAY, None


    def handle_get_format_capacity(self, cbw):
        response = bytes([
            0x00, 0x00, 0x00, 0x08,     # capacity list length
            0x00, 0x00, 0x10, 0x00,     # number of sectors (0x1000 = 10MB)
            0x10, 0x00,                 # reserved/descriptor code
            0x02, 0x00,                 # 512-byte sectors
        ])
        return self.STATUS_OKAY, response


    def handle_get_read_capacity(self, cbw):
        lastlba = self.disk_image.get_sector_count()
        if lastlba > 0xffffffff:
            lastlba = 0xffffffff

        response = bytes([
            (lastlba >> 24) & 0xff,
            (lastlba >> 16) & 0xff,
            (lastlba >>  8) & 0xff,
            (lastlba      ) & 0xff,
            0x00, 0x00, 0x02, 0x00,     # 512-byte blocks
        ])
        return self.STATUS_OKAY, response


    def handle_get_read_capacity_16(self, cbw):
        lastlba = self.disk_image.get_sector_count()

        response = bytes([
            (lastlba >> 56) & 0xff,
            (lastlba >> 48) & 0xff,
            (lastlba >> 40) & 0xff,
            (lastlba >> 32) & 0xff,
            (lastlba >> 24) & 0xff,
            (lastlba >> 16) & 0xff,
            (lastlba >>  8) & 0xff,
            (lastlba      ) & 0xff,
            0x00, 0x00, 0x02, 0x00,     # 512-byte blocks
        ])
        return self.STATUS_OKAY, response


    def handle_read(self, cbw):
        base_lba = cbw.cb[2] << 24 \
                 | cbw.cb[3] << 16 \
                 | cbw.cb[4] << 8 \
                 | cbw.cb[5]

        num_blocks = cbw.cb[7] << 8 \
                   | cbw.cb[8]

        if self.verbose > 0:
            print("<-- performing READ (10), lba", base_lba, "+", num_blocks, "block(s)")

        # Note that here we send the data directly rather than putting
        # something in 'response' and letting the end of the switch send
        for block_num in range(num_blocks):
            data = self.disk_image.get_sector_data(base_lba + block_num)
            self.device.send(ENDPOINT_IN, data, blocking=True)

        if self.verbose > 3:
            print("--> responded with {} bytes".format(cbw.data_transfer_length))

        return self.STATUS_OKAY, None


    def handle_read_16(self, cbw):
        base_lba = cbw.cb[2] << 56 \
                 | cbw.cb[3] << 48 \
                 | cbw.cb[4] << 40 \
                 | cbw.cb[5] << 32 \
                 | cbw.cb[6] << 24 \
                 | cbw.cb[7] << 16 \
                 | cbw.cb[8] << 8 \
                 | cbw.cb[9]

        num_blocks = cbw.cb[10] << 24 \
                   | cbw.cb[11] << 16 \
                   | cbw.cb[12] << 8  \
                   | cbw.cb[13]

        if self.verbose > 0:
            print("<-- performing READ (16), lba", base_lba, "+", num_blocks, "block(s)")

        # Note that here we send the data directly rather than putting
        # something in 'response' and letting the end of the switch send
        for block_num in range(num_blocks):
            data = self.disk_image.get_sector_data(base_lba + block_num)
            self.ep_to_host.send_packet(data, blocking=True)

        if self.verbose > 3:
            print("--> responded with {} bytes".format(cbw.data_transfer_length))

        return self.STATUS_OKAY, None


    def handle_write(self, cbw):
        base_lba = cbw.cb[2] << 24 \
                 | cbw.cb[3] << 16 \
                 | cbw.cb[4] <<  8 \
                 | cbw.cb[5]

        num_blocks = cbw.cb[7] << 8 \
                   | cbw.cb[8]

        if self.verbose > 0:
            print("--> performing WRITE (10), lba", base_lba, "+", num_blocks, "block(s)")

        # save for later
        self.write_cbw = cbw
        self.write_base_lba = base_lba
        self.write_length = num_blocks * self.disk_image.get_sector_size()
        self.is_write_in_progress = True

        # because we need to snarf up the data from wire before we reply
        # with the CSW
        return self.STATUS_INCOMPLETE, None


    def handle_write_16(self, cbw):
        base_lba = cbw.cb[2] << 56 \
                 | cbw.cb[3] << 48 \
                 | cbw.cb[4] << 40 \
                 | cbw.cb[5] << 32 \
                 | cbw.cb[6] << 24 \
                 | cbw.cb[7] << 16 \
                 | cbw.cb[8] << 8 \
                 | cbw.cb[9]

        num_blocks = cbw.cb[10] << 24 \
                   | cbw.cb[11] << 16 \
                   | cbw.cb[12] << 8  \
                   | cbw.cb[13]

        if self.verbose > 0:
            print("--> performing WRITE (16), lba", base_lba, "+", num_blocks, "block(s)")

        # save for later
        self.write_cbw = cbw
        self.write_base_lba = base_lba
        self.write_length = num_blocks * self.disk_image.get_sector_size()
        self.is_write_in_progress = True

        # because we need to snarf up the data from wire before we reply
        # with the CSW
        return self.STATUS_INCOMPLETE, None


    def continue_write(self, cbw, data):
        if self.verbose > 3:
            print("--> continue write with {} more bytes of data".format(len(data)))

        self.write_data += data

        if len(self.write_data) < self.write_length:
            # more yet to read, don't send the CSW
            return self.STATUS_INCOMPLETE, None

        self.disk_image.put_data(self.write_base_lba, self.write_data)

        self.is_write_in_progress = False
        self.write_data = b''

        return self.STATUS_OKAY, None


    def _register_scsi_commands(self):
        self.commands = {}

        self._register_scsi_command(0x00, "Test Unit Ready", self.handle_ignored_event)
        self._register_scsi_command(0x03, "Request Sense", self.handle_sense)
        self._register_scsi_command(0x12, "Inquiry", self.handle_inquiry)
        self._register_scsi_command(0x1a, "Mode Sense (6)", self.handle_mode_sense_6)
        self._register_scsi_command(0x5a, "Mode Sense (10)", self.handle_mode_sense_10)
        self._register_scsi_command(0x1e, "Prevent/Allow Removal", self.handle_ignored_event)
        self._register_scsi_command(0x23, "Get Format Capacity", self.handle_get_format_capacity)
        self._register_scsi_command(0x25, "Get Read Capacity", self.handle_get_read_capacity)
        self._register_scsi_command(0x28, "Read", self.handle_read)
        self._register_scsi_command(0x88, "Read (16)", self.handle_read_16)
        self._register_scsi_command(0x2a, "Write (10)", self.handle_write)
        self._register_scsi_command(0x8a, "Write (16)", self.handle_write_16)
        self._register_scsi_command(0x36, "Synchronize Cache", self.handle_ignored_event)
        self._register_scsi_command(0x9e, "Service Action In", self.handle_service_action_in)


    def _register_scsi_command(self, number, name, handler=None):
        if handler is None:
            handler = self.handle_unknown_command

        descriptor = {
            "number": number,
            "name": name,
            "handler": handler,
        }
        self.commands[number] = descriptor


class CommandBlockWrapper:
    def __init__(self, bytestring):
        self.signature              = bytestring[0:4]
        self.tag                    = bytestring[4:8]
        self.data_transfer_length   = bytestring[8] \
                                    | bytestring[9] << 8 \
                                    | bytestring[10] << 16 \
                                    | bytestring[11] << 24
        self.flags                  = int(bytestring[12])
        self.lun                    = int(bytestring[13] & 0x0f)
        self.cb_length              = int(bytestring[14] & 0x1f)
        self.cb                     = bytestring[15:]

    def __str__(self):
        s  = "sig: " + bytes_as_hex(self.signature) + "\n"
        s += "tag: " + bytes_as_hex(self.tag) + "\n"
        s += "data transfer len: " + str(self.data_transfer_length) + "\n"
        s += "flags: " + str(self.flags) + "\n"
        s += "lun: " + str(self.lun) + "\n"
        s += "command block len: " + str(self.cb_length) + "\n"
        s += "command block: " + bytes_as_hex(self.cb) + "\n"

        return s


if __name__ == "__main__":
    default_main(USBMassStorageDevice)
