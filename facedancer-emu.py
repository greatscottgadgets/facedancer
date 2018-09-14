#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import sys

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

from umap2.fuzz.helpers import StageLogger, set_stage_logger

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
        '--vid', '-vid',
        help='Vendor ID',
        default='')
    parser.add_argument(
        '--pid', '-pid',
        help='Product ID',
        default='')
    
    parser.add_argument(
        '--makestage', '-ms',
        help='Make fuzzing stage file',
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
    if args.makestage!="":
        phy.setstage(args.makestage)
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
            print("\nUsage: facedancer-emu.py -device MassStorage -file examples/fat32.3M.stick.img");
            sys.exit(1);
        i = RawDiskImage(args.filename, 512, verbose=int(args.verbose))
        d = func(phy, i)
    elif args.device=="MassStorage-DoubleFetch":
        if args.filename=='' or args.filename2=='':
            print("\nUsage: facedancer-emu.py -device MassStorage-DoubleFetch -file valid_firmware -file2 hacked_firmware");
            sys.exit(1);
        i = DoubleFetchImage(args.filename, args.filename2)
        d = func(phy, i)
    elif args.device=="Vendor":
        if args.vid=='' or args.pid=='':
            print("\nUsage: facedancer-emu.py -device Vendor -vid 0x1234 -pid 0x5678");
            sys.exit(1);
        vvid = int(args.vid, 16)
        vpid = int(args.pid, 16)
        d = func(phy, vid=vvid, pid=vpid)
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
