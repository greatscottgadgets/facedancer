#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import sys
import os
import importlib

from facedancer import FacedancerUSBApp
from devices.ums_doublefetch import USBUMSDoubleFetchImageDevice
from facedancer.utils.spiflash import SPIFlash
from devices.mass_storage import RawDiskImage

def loadmodules():
    classinfo={}

    for root, dirs, files in os.walk('devices'):
        for file in files:
            if ".py" in file[-3:]:
                with open(os.path.join('devices',file),'r') as rf:
                    line='-1'
                    while (line!=''):
                        line=rf.readline()
                        if "class USB" in line and "Device" in line:
                            classfunc=line.split("class ")[1].split("(")[0]
                            name=classfunc.replace("USB","").replace("Device","")
                            while (line!=''):
                                line=rf.readline()
                                if "name" in line:
                                    if "\"" in line:
                                        desc=line.split("\"")[1]
                                    elif "\'" in line:
                                        desc=line.split("\'")[1]
                                    break
                            impname="devices."+file[:-3]
                            MyClass = getattr(importlib.import_module(impname), classfunc)
                            classinfo[name]=[desc,MyClass]
                            break
    return classinfo

def showtypes(classinfo):
    print("\nSupported types are:")
    for entry in classinfo:
        print("\t\"%s\" %s = %s" % (entry,' '*(20-len(entry)),classinfo[entry][0]))

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
    classinfo=loadmodules()
    if args.device == '':
        print("\nFaceDancer USB-Emulator")
        print("-----------------------")
        print("Please run as: facedancer-emu.py -device [devicetype]")
        showtypes(classinfo)
        exit(0)

    found=False
    for entry in classinfo:
        if args.device.lower()==entry.lower() or args.device==entry:
            args.device=entry
            func=classinfo[entry][1]
            found=True
            break

    if not found:
        print("Wrong devicetype given.")
        showtypes(classinfo)
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
    elif args.device=="UMSDoubleFetchImage":
        if args.filename=='' or args.filename2=='':
            print("\nUsage: facedancer-emu.py -device UMSDoubleFetchImage -file valid_firmware -file2 hacked_firmware");
            sys.exit(1);
        i = USBUMSDoubleFetchImageDevice(args.filename, args.filename2)
        d = func(phy, i)
    elif args.device=="VendorSpecific":
        if args.vid=='' or args.pid=='':
            print("\nUsage: facedancer-emu.py -device VendorSpecific -vid 0x1234 -pid 0x5678");
            sys.exit(1);
        vvid = int(args.vid, 16)
        vpid = int(args.pid, 16)
        d = func(phy, vid=vvid, pid=vpid)
    elif args.device=="ProController":
        d = func(phy, spi_flash=SPIFlash())
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
