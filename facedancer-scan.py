#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import sys
import time
import traceback
import logging

from facedancer import FacedancerUSBApp
from devices.audio import USBAudioDevice
from devices.cdc import USBCDCDevice
from devices.cdc_acm import USBCdcAcmDevice
from devices.cdc_dl import USBCdcDlDevice
from devices.qc_edl import USBSaharaDevice
from devices.ftdi import USBFtdiDevice
from devices.keyboard import USBKeyboardDevice
from devices.iphone import USBiPhoneDevice
from devices.serial import USBSerialDevice
from devices.switch_TAS import USBSwitchTASDevice
from devices.mass_storage import USBMassStorageDevice, RawDiskImage
from devices.ums_doublefetch import DoubleFetchImage
from devices.billboard import USBBillboardDevice

from devices.hub import USBHubDevice
from devices.printer import USBPrinterDevice
from devices.mtp import USBMtpDevice
from devices.vendor_specific import USBVendorSpecificDevice
from devices.smartcard import USBSmartcardDevice
from devices.usbprocontroller import USBProControllerDevice
from facedancer.utils.spiflash import SPIFlash

targets=[
    ["Vendor",USBVendorSpecificDevice],
    ["Audio", USBAudioDevice],
    ["Billboard", USBBillboardDevice],
    ["CDC",USBCDCDevice],
    ["CDC-ACM",USBCdcAcmDevice],
    ["CDC-DL",USBCdcDlDevice],
    ["EDL",USBSaharaDevice],
    ["FTDI",USBFtdiDevice],
    ["Hub",USBHubDevice],
    ["iPhone",USBiPhoneDevice],
    ["Keyboard",USBKeyboardDevice],
    ["MassStorage",USBMassStorageDevice],
    ["MassStorage-DoubleFetch",USBMassStorageDevice],
    ["Serial",USBSerialDevice],
    ["Smartcard",USBSmartcardDevice],
    ["SwitchTAS",USBSwitchTASDevice],
    ["MTP",USBMtpDevice],
    ["Printer",USBPrinterDevice]
]

def showtypes():
    print("\nSupported types are:")
    for entry in targets:
        print("\t\"%s\"" % (entry[0]))

class ScanApp():
    def __init__(self,phy):
        self.phy = phy
        self.current_usb_function_supported = False
        self.start_time = 0
        self.logger = logging.getLogger('facedancer')

    def usb_function_supported(self, reason=None):
        self.current_usb_function_supported = True

    def run(self):
        self.logger.always('Scanning host for supported devices')
        supported = []

        self.phy.should_stop_phy=self.should_stop_phy

        self.phy.set_log_level(int(100))

        for device in targets:
            if device[0] in ['Printer','MassStorage-DoubleFetch']:
                # skip those devices ATM
                continue
            self.logger.always('Testing support: %s' % (device[0]))
            self.start_time = time.time()
            try:
                func=device[1]
                if device[0] == "ProController":
                    d = func(self.phy, spi_flash=SPIFlash())
                elif device[0] == "MassStorage":
                    rdi = RawDiskImage("examples/fat32.3M.stick.img", 512)
                    d = func(self.phy, rdi)
                elif device[0] == "Vendor":
                    vvid = int("0x1234", 16)
                    vpid = int("0x5678", 16)
                    d = func(self.phy, vid=vvid, pid=vpid)
                else:
                    d = func(self.phy)
                d.connect()
                d.run()
                d.disconnect()
            except:
                self.logger.error(traceback.format_exc())
                d.disconnect()
            if "current_usb_function_supported" in dir(d.phy):
                if d.phy.current_usb_function_supported:
                    self.logger.always('Device is SUPPORTED')
                    supported.append(device[0])
            self.current_usb_function_supported = False
            time.sleep(2)
        if len(supported):
            self.logger.always('---------------------------------')
            self.logger.always('Found %s supported device(s):' % (len(supported)))
            for i, device_name in enumerate(supported):
                self.logger.always('%d. %s' % (i + 1, device_name))
        self.logger.warning('Note: printer is not tested at the moment')

    def should_stop_phy(self):
        stop_phy = False
        passed = int(time.time() - self.start_time)
        if passed > 5:
            self.logger.info('have been waiting long enough (over %d secs.), disconnect' % (passed))
            stop_phy = True
        return stop_phy

def main(argv):
    t = ScanApp(FacedancerUSBApp())
    t.run()
    
if __name__ == '__main__':
  main(sys.argv)
