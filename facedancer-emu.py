#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import sys
import os
import importlib
import logging
import time

from facedancer import FacedancerUSBApp
from devices.ums_doublefetch import USBUMSDoubleFetchImageDevice
from facedancer.utils.spiflash import SPIFlash
from devices.mass_storage import RawDiskImage
from kitty.remote.rpc import RpcClient

class FaceDancerEmu():

    def __init__(self, options):
        self.logger = logging.getLogger('facedancer')
        self.options=options
        self.count=0
        self.func=None

    def loaddevices(self):
        self.classinfo={}
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
                                self.classinfo[name]=[desc,impname,classfunc]
                                break

    def showdevices(self):
        print("\nSupported types are:")
        for entry in self.classinfo:
            print("\t\"%s\" %s = %s" % (entry,' '*(20-len(entry)),self.classinfo[entry][0]))


    def get_fuzzer(self):
        self.fuzzer = RpcClient(
            host=self.options.ip,
            port=int(self.options.port)
        )

        self.fuzzer.start()

    def should_stop_phy(self):
        if self.fuzzer:
            self.count = (self.count + 1) % 50
            self.check_connection_commands()
            if self.count == 0:
                self.send_heartbeat()
        return False

    def send_heartbeat(self):
        heartbeat_file = '/tmp/fd_kitty/heartbeat'
        if os.path.isdir(os.path.dirname(heartbeat_file)):
            with open(heartbeat_file, 'a'):
                os.utime(heartbeat_file, None)

    def check_connection_commands(self):
        '''
        :return: whether performed reconnection
        '''
        if self._should_disconnect():
            self.d.disconnect()
            self._clear_disconnect_trigger()
            # wait for reconnection request; no point in returning to service_irqs loop while not connected!
            while not self._should_reconnect():
                self._clear_disconnect_trigger()  # be robust to additional disconnect requests
                time.sleep(0.1)
        # now that we received a reconnect request, flow into the handling of it...
        # be robust to reconnection requests, whether received after a disconnect request, or standalone
        # (not sure this is right, might be better to *not* be robust in the face of possible misuse?)
        if self._should_reconnect():
            self.d.connect()
            self._clear_reconnect_trigger()
            return True
        return False

    def _should_reconnect(self):
        if self.fuzzer:
            if os.path.isfile('/tmp/fd_kitty/trigger_reconnect'):
                return True
        return False

    def _clear_reconnect_trigger(self):
        trigger = '/tmp/fd_kitty/trigger_reconnect'
        if os.path.isfile(trigger):
            os.remove(trigger)

    def _should_disconnect(self):
        if self.fuzzer:
            if os.path.isfile('/tmp/fd_kitty/trigger_disconnect'):
                return True
        return False

    def _clear_disconnect_trigger(self):
        trigger = '/tmp/fd_kitty/trigger_disconnect'
        if os.path.isfile(trigger):
            os.remove(trigger)

    def get_mutation(self, stage, data=None):
        if self.fuzzer:
            data = {} if data is None else data
            return self.fuzzer.get_mutation(stage=stage, data=data)
        return None

    def run(self):
        found = False

        self.phy = FacedancerUSBApp()
        if self.options.makestage != "":
            self.phy.setstage(self.options.makestage)
        print(self.phy)
        if self.options.fuzzer==True:
            self.get_fuzzer()
            self.phy.fuzzer = self.fuzzer
            self.phy.get_mutation = self.get_mutation
            self.phy.should_stop_phy = self.should_stop_phy
        else:
            self.fuzzer=False

        if self.options.device == "MassStorage":
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
            if self.options.filename == '':
                print("\nUsage: facedancer-emu.py -device MassStorage -file examples/fat32.3M.stick.img");
                sys.exit(1);
            i = RawDiskImage(self.options.filename, 512, verbose=int(self.options.verbose))
            self.d = self.func(self.phy, i)
        elif self.options.device == "UMSDoubleFetchImage":
            if self.options.filename == '' or self.options.filename2 == '':
                print(
                    "\nUsage: facedancer-emu.py -device UMSDoubleFetchImage -file valid_firmware -file2 hacked_firmware");
                sys.exit(1);
            i = USBUMSDoubleFetchImageDevice(self.options.filename, self.options.filename2)
            self.d = self.func(self.phy, i)
        elif self.options.device == "VendorSpecific":
            if self.options.vid == '' or self.options.pid == '':
                print("\nUsage: facedancer-emu.py -device VendorSpecific -vid 0x1234 -pid 0x5678");
                sys.exit(1);
            vvid = int(self.options.vid, 16)
            vpid = int(self.options.pid, 16)
            self.d = self.func(self.phy, vid=vvid, pid=vpid)
        elif self.options.device == "ProController":
            self.d = self.func(self.phy, spi_flash=SPIFlash())
        else:
            self.d = self.func(self.phy)

        self.d.connect()
        self.phy.set_log_level(int(self.options.verbose))

        try:
            self.d.run()
        # SIGINT raises KeyboardInterrupt
        except KeyboardInterrupt:
            self.d.disconnect()

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
        '--fuzzer', '-f',
        help='enable fuzzer',
        action="store_true")
    parser.add_argument(
        '--ip', '-i',
        help='hostname or IP of the fuzzer [default: 127.0.0.1]',
        default='127.0.0.1')
    parser.add_argument(
        '--port', '-p',
        help='port of the fuzzer [default: 26007]',
        default='26007')
    parser.add_argument(
        '--makestage', '-ms',
        help='Generate stage file',
        default='')
    parser.add_argument(
        '--verbose', '-verbose',
        help='Debug level',
        default='0')
        
    args = parser.parse_args()

    emu=FaceDancerEmu(args)
    emu.loaddevices()
    if args.device == '':
        print("\nFaceDancer USB-Emulator")
        print("-----------------------")
        print("Please run as: facedancer-emu.py -device [devicetype]")
        emu.showdevices()
        exit(0)

    found = False
    for entry in emu.classinfo:
        if args.device.lower() == entry.lower() or args.device == entry:
            args.device = entry
            emu.func = MyClass = getattr(importlib.import_module(emu.classinfo[entry][1]), emu.classinfo[entry][2])
            found = True
            break

    if not found:
        print("Wrong devicetype given.")
        emu.showdevices()
        exit(0)

    emu.run()
    

if __name__ == '__main__':
  main(sys.argv)
