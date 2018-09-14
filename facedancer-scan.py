#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import sys
import time
import traceback

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

targets=[
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
    ["Printer",USBPrinterDevice],
    ["Vendor",USBVendorSpecificDevice]
]

def showtypes():
    print("\nSupported types are:")
    for entry in targets:
        print("\t\"%s\"" % (entry[0]))

class ScanApp(FacedancerUSBApp):
    def __init__(self, options):
        super(ScanApp, self).__init__(options)
        self.current_usb_function_supported = False
        self.start_time = 0

    def usb_function_supported(self, reason=None):
        self.current_usb_function_supported = True

    def run(self):
        self.logger.always('Scanning host for supported devices')
        supported = []
            
        for device_name in targets:
            if device_name == 'Printer':
                # skip printer ATM
                continue
            self.logger.always('Testing support: %s' % (device_name))
            try:
                self.start_time = time.time()
                d = entry[1](self)
                d.connect()
                d.run()
                d.disconnect() 
            except:
                self.logger.error(traceback.format_exc())
            self.disconnect()
            if self.current_usb_function_supported:
                self.logger.always('Device is SUPPORTED')
                supported.append(device_name)
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
    phy = ScanApp(__doc__)
    phy.run()
    
if __name__ == '__main__':
  main(sys.argv)
