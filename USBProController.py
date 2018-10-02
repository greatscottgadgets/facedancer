"""
USBProController.py

Contains bare minimum code needed to initialize a Switch Pro Controller using a
GreatFET.

Copyright (c) 2018, wchill
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the organization nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import greatfet
import struct

from facedancer import HIDClass
from facedancer.USB import *
from facedancer.USBDevice import *
from facedancer.USBConfiguration import *
from facedancer.USBInterface import *
from facedancer.USBEndpoint import *


class USBProControllerInterface(USBInterface):
    name = "Fake Switch Pro Controller"

    # copied from a pro controller
    hid_descriptor = b'\x09\x21\x11\x01\x00\x01\x22\xcb\x00'
    report_descriptor = b'\x05\x01\x15\x00\x09\x04\xa1\x01\x85\x30\x05' \
                        b'\x01\x05\x09\x19\x01\x29\x0a\x15\x00\x25\x01' \
                        b'\x75\x01\x95\x0a\x55\x00\x65\x00\x81\x02\x05' \
                        b'\x09\x19\x0b\x29\x0e\x15\x00\x25\x01\x75\x01' \
                        b'\x95\x04\x81\x02\x75\x01\x95\x02\x81\x03\x0b' \
                        b'\x01\x00\x01\x00\xa1\x00\x0b\x30\x00\x01\x00' \
                        b'\x0b\x31\x00\x01\x00\x0b\x32\x00\x01\x00\x0b' \
                        b'\x35\x00\x01\x00\x15\x00\x27\xff\xff\x00\x00' \
                        b'\x75\x10\x95\x04\x81\x02\xc0\x0b\x39\x00\x01' \
                        b'\x00\x15\x00\x25\x07\x35\x00\x46\x3b\x01\x65' \
                        b'\x14\x75\x04\x95\x01\x81\x02\x05\x09\x19\x0f' \
                        b'\x29\x12\x15\x00\x25\x01\x75\x01\x95\x04\x81' \
                        b'\x02\x75\x08\x95\x34\x81\x03\x06\x00\xff\x85' \
                        b'\x21\x09\x01\x75\x08\x95\x3f\x81\x03\x85\x81' \
                        b'\x09\x02\x75\x08\x95\x3f\x81\x03\x85\x01\x09' \
                        b'\x03\x75\x08\x95\x3f\x91\x83\x85\x10\x09\x04' \
                        b'\x75\x08\x95\x3f\x91\x83\x85\x80\x09\x05\x75' \
                        b'\x08\x95\x3f\x91\x83\x85\x82\x09\x06\x75\x08' \
                        b'\x95\x3f\x91\x83\xc0'

    def __init__(self, spi_flash, verbose=0):
        descriptors = {
            USB.desc_type_hid: self.hid_descriptor,
            USB.desc_type_report: self.report_descriptor
        }

        self.in_endpoint = USBEndpoint(
            1,   # endpoint number
            USBEndpoint.direction_in,
            USBEndpoint.transfer_type_interrupt,
            USBEndpoint.sync_type_none,
            USBEndpoint.usage_type_data,
            64,  # max packet size
            8,   # polling interval
            self.handle_dev_to_host
        )

        self.out_endpoint = USBEndpoint(
            2,   # endpoint number
            USBEndpoint.direction_out,
            USBEndpoint.transfer_type_interrupt,
            USBEndpoint.sync_type_none,
            USBEndpoint.usage_type_data,
            64,  # max packet size
            8,   # polling interval
            self.handle_host_to_dev
        )

        self.report_mode = None
        self.timer = 0
        self.buttons = b'\x00\x00\x00'
        self.held = [0] * 12
        self.player_lights = 0
        # BT MAC address, big endian
        self.mac_addr = [0x12, 0x34, 0x56, 0x78, 0x90, 0xab]
        self.spi_flash = spi_flash

        USBInterface.__init__(
            self,
            0,                                  # interface number
            0,                                  # alternate setting
            HIDClass.HID_CLASS_NUMBER,          # interface class
            0,                                  # subclass
            0,                                  # protocol
            0,                                  # string index
            verbose,
            [self.in_endpoint, self.out_endpoint],
            descriptors
        )

    def handle_dev_to_host(self):
        if self.report_mode == 0x30:
            self.send_report_0x30()

    def handle_host_to_dev(self, data):
        if data == b'\x00\x00':
            # Not implemented (not sure what this does)
            print('[00 00] Ignoring')
        elif data[0] == 0x01:
            self.handle_01_command(data[1:])
        elif data[0] == 0x10:
            # Not implemented
            pass
        elif data[0] == 0x80:
            self.handle_80_command(data[1:])
        else:
            print('??? Got out data! {}'.format(data))

    def handle_01_command(self, data):
        subcommand = data[9]
        subcommand_data = data[10:]

        def log(s):
            print('[01 {}] {}'.format(subcommand, s))

        def ack_subcommand(ack_type, ack_data=b''):
            self.send_report_0x21(ack_type, subcommand, ack_data)

        if subcommand == 0x00:
            ack_subcommand(0x80, b'\x03')
        elif subcommand == 0x01:
            # Not implemented
            log('Request BT pairing')
            ack_subcommand(0x81, b'\x03')
        elif subcommand == 0x02:
            resp = b'\x03\x48\x03\x02' + bytes(self.mac_addr) + b'\x01\x01'
            log('Request device info - {}'.format(resp))
            ack_subcommand(0x82, resp)
        elif subcommand == 0x03:
            polling_modes = {
                0x00: 'NFC/IR camera active polling',
                0x01: 'NFC/IR MCU configuration active polling',
                0x02: 'NFC/IR data and configuration active polling',
                0x03: 'IR camera data active polling',
                0x23: 'MCU update state report',
                0x30: 'standard',
                0x31: 'NFC/IR mode',
                0x3f: 'simple HID mode'
            }
            self.report_mode = subcommand_data[0]
            current_mode = polling_modes.get(self.report_mode, 'unknown mode')
            log('Set input report mode - {} ({:02x})'
                .format(current_mode, self.report_mode))

            ack_subcommand(0x80)
        elif subcommand == 0x04:
            # FIXME: Properly implement this subcommand
            # currently it's hardcoded to hold L and R for about 2.5 seconds
            if self.buttons == b'\x40\x00\x40':
                self.held[0] += 1
                if self.held[0] >= 256:
                    self.held[0] = 0
                    self.held[1] += 1
                self.held[2] += 1
                if self.held[2] >= 256:
                    self.held[2] = 0
                    self.held[3] += 1

                if self.held[1] >= 1:
                    self.buttons = b'\x00\x00\x00'

            ack_subcommand(0x83, bytes(self.held))
        elif subcommand == 0x08:
            if subcommand_data[0] == 0x01:
                log('Enable shipment power state')
            else:
                log('Disable shipment power state')

            # TODO: Emulate SPI write
            self.send_report_0x21(0x80, 0x08)
        elif subcommand == 0x10:
            addr = struct.unpack('<I', subcommand_data[:4])[0]
            length = subcommand_data[4]
            spi_data = self.spi_flash.read(addr, length)
            log('Read SPI flash - addr {:04x}, len {:02x}, data {}'
                .format(addr, length, spi_data))

            ack_subcommand(0x90, subcommand_data[:5] + spi_data)

            # TODO: fix hack
            # A read to this address is the last thing to happen before
            # we need to press L and R
            if addr == 0x6020:
                self.buttons = b'\x40\x00\x40'
        elif subcommand == 0x11:
            addr = struct.unpack('<I', subcommand_data[:4])[0]
            length = subcommand_data[4]
            spi_data = subcommand_data[5:]
            log('Write SPI flash - addr {:04x}, len {}, data {}'
                .format(addr, length, spi_data))

            self.spi_flash.write(addr, spi_data)
            ack_subcommand(0x80, b'\x00')
        elif subcommand == 0x12:
            addr = struct.unpack('<I', subcommand_data[:4])[0]
            log('Erase SPI flash - addr {:04x}'.format(addr))

            self.spi_flash.erase(addr)
            ack_subcommand(0x80, b'\x00')
        elif subcommand == 0x30:
            self.player_lights = subcommand_data[0]
            log('Set player lights - value {:02x}'.format(self.player_lights))

            ack_subcommand(0x80)
        elif subcommand == 0x31:
            log('Request player lights - value {:02x}'
                .format(self.player_lights))

            ack_subcommand(0xb0, self.player_lights)
        elif subcommand == 0x38:
            log('Set HOME light')
        elif subcommand == 0x40:
            if subcommand_data[0] == 1:
                log('Enable 6-axis IMU')
            else:
                log('Disable 6-axis IMU')

            ack_subcommand(0x80)
        elif subcommand == 0x41:
            gyro_sens = [250, 500, 1000, 2000]
            accel_sens = [8, 4, 2, 16]
            gyro_perf = [833, 208]
            accel_aa_filter_bw = [200, 100]

            log('Set IMU sensitivity: +/-{}dps gyro @ {}Hz, +/-{}G accel @ {}Hz'
                .format(gyro_sens[subcommand_data[0]],
                        gyro_perf[subcommand_data[2]],
                        accel_sens[subcommand_data[1]],
                        accel_aa_filter_bw[subcommand_data[3]]))

            ack_subcommand(0x80)
        elif subcommand == 0x42:
            # Not implemented
            log('Write to IMU register - address {:04x} value {:02x}'
                .format(subcommand_data[0], subcommand_data[2]))
        elif subcommand == 0x43:
            # Not implemented
            log('Read from IMU registers - start address {:04x} len {:02x}'
                .format(subcommand_data[0], subcommand_data[1]))
        elif subcommand == 0x48:
            if subcommand_data[0] == 1:
                log('Enable vibration')
            else:
                log('Disable vibration')

            ack_subcommand(0x80)
        else:
            log('Unknown subcommand - data: {}'.format(subcommand_data))
            ack_subcommand(0x80)

    def handle_80_command(self, data):
        opcode = data[0]

        def log(s):
            print('[80 {}] {}'.format(opcode, s))

        if opcode == 0x01:
            log('Requested current connection status')
            # Fake connection status
            self.in_endpoint.send(
                b'\x81\x01\x00\x03' + bytes(self.mac_addr[::-1]))
        elif opcode == 0x02:
            log('Requested handshake with Broadcom chip')
            # Fake a response
            self.in_endpoint.send(b'\x81\x02')
        elif opcode == 0x03:
            log('Requested 3Mbps baudrate')
            # Fake a response
            self.in_endpoint.send(b'\x81\x03')
        elif opcode == 0x04:
            log('Forced USB connection only')
        elif opcode == 0x05:
            log('Allowed USB connection timeout')
        elif opcode == 0x06:
            # TODO: Implement? Is this even needed?
            log('Requested reset')
        elif opcode == 0x91:
            # TODO: Implement? Is this even needed?
            log('Requested pre-handshake')
        elif opcode == 0x92:
            # TODO: Implement? Is this even needed?
            log('Sent arbitrary UART command - {}'.format(data[1:]))

    def send_report_0x21(self, ack, subcmd_id, reply_data=b''):
        report_data = b'\x21'

        report_data += self.inc_and_get_timer()

        # Battery level = 9 (full, charging)
        # Connection info = 1 (pro controller, USB powered)
        report_data += b'\x91'

        # 3 byte button state
        report_data += self.get_buttons()

        # 3 byte left analog stick
        report_data += self.get_left_stick()

        # 3 byte right analog stick
        report_data += self.get_right_stick()

        # 1 byte vibration report
        report_data += self.get_vibrate_report()

        report_data += ack.to_bytes(1, byteorder='little')
        report_data += subcmd_id.to_bytes(1, byteorder='little')
        report_data += reply_data + (b'\x00' * (35 - len(reply_data)))
        self.in_endpoint.send(report_data)

    def send_report_0x30(self):
        report_data = b'\x30'

        report_data += self.inc_and_get_timer()

        # Battery level = 9 (full, charging)
        # Connection info = 1 (pro controller, USB powered)
        report_data += b'\x91'

        # 3 byte button state
        report_data += self.get_buttons()

        # 3 byte left analog stick
        report_data += self.get_left_stick()

        # 3 byte right analog stick
        report_data += self.get_right_stick()

        # 1 byte vibration report
        report_data += self.get_vibrate_report()

        report_data += (self.get_accel() + self.get_gyro()) * 3
        self.in_endpoint.send(report_data)

    # TODO: Add proper implementations for these functions
    def get_buttons(self):
        return self.buttons

    def set_buttons(self, buttons):
        self.buttons = buttons

    def get_left_stick(self):
        return b'\x00\x08\x80'

    def get_right_stick(self):
        return b'\x00\x08\x80'

    def get_accel(self):
        return b'\x00\x00\x00\x00\x00\x00'

    def get_gyro(self):
        return b'\x00\x00\x00\x00\x00\x00'

    def get_vibrate_report(self):
        return b'\x00'

    def inc_and_get_timer(self):
        ret = self.timer.to_bytes(1, byteorder='little')
        self.timer = (self.timer + 3) % 256
        return ret


class USBProControllerDevice(USBDevice):
    name = "Switch Pro Controller USB device"

    def __init__(self, maxusb_app, spi_flash, verbose=0):
        self._tas_interface = USBProControllerInterface(spi_flash)
        config = USBConfiguration(
            1,                      # index
            0,                      # string desc
            [self._tas_interface],  # interfaces
            0xa0,                   # attributes
            250                     # power
        )

        USBDevice.__init__(
            self,
            maxusb_app,
            0,                      # device class
            0,                      # device subclass
            0,                      # protocol release number
            64,                     # max packet size for endpoint 0
            0x057e,                 # vendor id
            0x2009,                 # product id
            0x0200,                 # device revision
            "Nintendo Co., Ltd",    # manufacturer string
            "Pro Controller",       # product string
            "000000000001",         # serial number string
            [config],
            verbose=verbose
        )
