#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse

from facedancer import FacedancerUSBApp
from facedancer.dev.audio import *
from facedancer.dev.cdc import *
from facedancer.dev.cdc_acm import *
from facedancer.dev.qc_edl import *
from facedancer.dev.ftdi import *
from facedancer.dev.keyboard import *
from facedancer.dev.serial import *
from facedancer.dev.switch_TAS import *
from facedancer.dev.mass_storage import *
from facedancer.dev.ums_doublefetch import *
from facedancer.dev.billboard import *
from facedancer.dev.cdc_dl import *
from facedancer.dev.hub import *
from facedancer.dev.printer import *
from facedancer.dev.mtp import *
from facedancer.dev.vendor_specific import *
from facedancer.dev.smartcard import *

targets=[
    ["Audio", USBAudioDevice],
    ["Billboard", USBBillboardDevice],
    ["CDC",USBCDCDevice],
    ["CDC-ACM",USBCdcAcmDevice],
    ["CDC-DL",USBCdcDlDevice],
    ["EDL",USBSaharaDevice],
    ["FTDI",USBFtdiDevice],
    ["Hub",USBHubDevice],
    ["Keyboard",USBKeyboardDevice],
    ["MassStorage",USBMassStorageDevice],
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

def main(argv):
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description='Facedancer Emulator')

    parser.add_argument(
        '--device', '-device',
        help='USB Device to emulate',
        default='')
    parser.add_argument(
        '--filename', '-file',
        help='Filename',
        default='')
    parser.add_argument(
        '--filename2', '-file2',
        help='Additional Filename',
        default='')

    parser.add_argument(
        '--verbose', '-verbose',
        help='Debug level',
        default='0')
        
    args = parser.parse_args()

    if args.device == '':
        print("\nFaceDancer USB-Emulator")
        print("-----------------------")
        print("Please run as: facedancer-emu.py -device [devicetype]")
        showtypes()
        exit(0)

    found=False
    for entry in targets:
        if args.device==entry[0]:
            func=entry[1]
            found=True
            break

    if not found:
        print("Wrong devicetype given.")
        showtypes()
        exit(0)
        
    phy = FacedancerUSBApp()
    print(phy)
    
    if args.device=="MassStorage":
        #
        # Creating a disk image under linux:
        #
        #   # fallocate -l 100M disk.img
        #   # fdisk disk.img
        #   # losetup -f --show disk.img
        #   # kpartx -a /dev/loopX
        #   # mkfs.XXX /dev/mapper/loopXpY
        #   # mount /dev/mapper/loopXpY /mnt/point
        #       do stuff on /mnt/point
        #   # umount /mnt/point
        #   # kpartx -d /dev/loopX
        #   # losetup -d /dev/loopX
        if args.filename=='':
            print("Usage: facedancer-emu.py -device MassStorage -file disk.img");
            sys.exit(1);
        i = RawDiskImage(args.filename, 512, verbose=int(args.verbose))
        d = func(phy, i)
    elif args.device=="UMS-DoubleFetch":
        if args.filename=='' or args.filename2=='':
            print("Usage: facedancer-emu.py -device UMS-DoubleFetch -file valid_firmware -file2 hacked_firmware");
            sys.exit(1);
        i = DoubleFetchImage(args.filename, args.filename2)
        d = func(phy, i)
    else:
        d = func(phy)

    d.connect()
    phy.set_log_level(int(args.verbose))

    try:
        d.run()
    # SIGINT raises KeyboardInterrupt
    except KeyboardInterrupt:
        d.disconnect() 
        
if __name__ == '__main__':
  main(sys.argv)
