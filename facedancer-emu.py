#!/usr/bin/env python3

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
from facedancer.dev.rawdiskimage import * 
from facedancer.dev.ums_doublefetch import *
from facedancer.dev.billboard import *
from facedancer.dev.cdc_dl import *
from facedancer.dev.hub import *
from facedancer.dev.printer import *
from facedancer.dev.mtp import *
from facedancer.dev.vendor_specific import *
from facedancer.dev.smartcard import *

def main(argv):
    if (len(argv)<2):
        print("\nFaceDancer USB-Emulator")
        print("-----------------------")
        print("Please run as: facedancer-emu.py [type]")
        print("\nSupported types are:")
        print(" Audio")
        print(" BillBoard")
        print(" CDC")
        print(" CDC-ACM")
        print(" CDC-DL")
        print(" EDL")
        print(" FTDI")
        print(" Hub")
        print(" Keyboard")
        print(" MassStorage")
        print(" MTP")
        print(" Printer")
        print(" Serial")
        print(" Smartcard")
        print(" SwitchTAS")
        print(" UMS-DoubleFetch")
        print(" Vendor")
        exit(0)

    u = FacedancerUSBApp(verbose=5)
    print(u)
    
    if type=="Audio":
        d = USBAudioDevice(u, verbose=4)
    elif type=="BillBoard":
        d = USBBillboardDevice(u, verbose=4)
    elif type=="CDC":
        d = USBCDCDevice(u, verbose=4)
    elif type=="CDC-ACM":
        d = USBCdcAcmDevice(u, verbose=4)
    elif type=="CDC-DL":
        d = USBCdcDlDevice(u, verbose=4)
    elif type=="EDL":
        d = USBSaharaDevice(u, verbose=4)
    elif type=="FTDI":
        d = USBFtdiDevice(u, verbose=6)
    elif type=="Hub":
        d = USBHubDevice(u, verbose=6)
    elif type=="Keyboard":
        d = USBKeyboardDevice(u, verbose=5)
    elif type=="Serial":
        d = USBSerialDevice(u, verbose=4)
    elif tpye=="Smartcard":
        d = USBSmartcardDevice(u, verbose=4)
    elif type=="SwitchTAS":
        d = USBSwitchTASDevice(u, verbose=5)
    elif type=="MassStorage":
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
        if len(sys.argv)<3:
            print("Usage: facedancer-emu.py MassStorage disk.img");
            sys.exit(1);
        i = RawDiskImage(sys.argv[2], 512, verbose=3)
        d = USBMassStorageDevice(u, i, verbose=3)
    elif type=="MTP":
        d = USBMtpDevice(u, verbose=4)
    elif type=="Printer":
        d = USBPrinterDevice(u, verbose=4)
    elif type=="UMS-DoubleFetch":
        if len(sys.argv)<4:
            print("Usage: facedancer-emu.py UMS-DoubleFetch valid_firmware hacked_firmware");
            sys.exit(1);
        i = DoubleFetchImage(sys.argv[2], sys.argv[3], verbose=2)
        d = USBMassStorageDevice(u, i, verbose=0)
    elif type=="Vendor":
        d = USBVendorSpecificDevice(u, verbose=4)
        
    d.connect()

    try:
        d.run()
    # SIGINT raises KeyboardInterrupt
    except KeyboardInterrupt:
        d.disconnect() 
        
if __name__ == '__main__':
  main(sys.argv)
