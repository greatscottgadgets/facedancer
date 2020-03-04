'''
USB Class definitions for Qualcomm QDLoader 9008 Firehose
(c) B. Kerler 2018
At least set up hwid and hash.
serial and sbversion is optional for testing.
Supports extraction of firehose/EDL loaders, saves as [hwid].bin in local directory
'''

import facedancer
import struct
import binascii
import time

from facedancer.USB import *
from facedancer.USBDevice import *
from facedancer.USBConfiguration import *
from facedancer.USBInterface import *
from facedancer.USBEndpoint import *
from facedancer.USBVendor import *

class USBSaharaVendor(USBVendor):
    name = "QC Sahara EDL"

    def setup_request_handlers(self):
        self.request_handlers = {
            # There are no vendor requests!
            #  0 : self.handle_reset_request,
            #  1 : self.handle_modem_ctrl_request,
            #  2 : self.handle_set_flow_ctrl_request,
            #  3 : self.handle_set_baud_rate_request,
            #  4 : self.handle_set_data_request,
            #  5 : self.handle_get_status_request,
            #  6 : self.handle_set_event_char_request,
            #  7 : self.handle_set_error_char_request,
            #  9 : self.handle_set_latency_timer_request,
            # 10 : self.handle_get_latency_timer_request
        }


class USBSaharaInterface(USBInterface):
    name = "QC Sahara interface"

    SAHARA_HELLO_REQ=0x1
    SAHARA_HELLO_RSP=0x2
    SAHARA_READ_DATA=0x3
    SAHARA_END_TRANSFER=0x4
    SAHARA_DONE_REQ=0x5
    SAHARA_DONE_RSP=0x6
    SAHARA_RESET_REQ=0x7
    SAHARA_RESET_RSP=0x8
    SAHARA_MEMORY_DEBUG=0x9
    SAHARA_MEMORY_READ=0xA
    SAHARA_CMD_READY=0xB
    SAHARA_SWITCH_MODE=0xC
    SAHARA_EXECUTE_REQ=0xD
    SAHARA_EXECUTE_RSP=0xE
    SAHARA_EXECUTE_DATA=0xF
    SAHARA_64BIT_MEMORY_DEBUG=0x10
    SAHARA_64BIT_MEMORY_READ=0x11
    SAHARA_64BIT_MEMORY_READ_DATA=0x12

    SAHARA_EXEC_CMD_NOP = 0x00
    SAHARA_EXEC_CMD_SERIAL_NUM_READ = 0x01
    SAHARA_EXEC_CMD_MSM_HW_ID_READ = 0x02
    SAHARA_EXEC_CMD_OEM_PK_HASH_READ = 0x03
    SAHARA_EXEC_CMD_SWITCH_TO_DMSS_DLOAD = 0x04
    SAHARA_EXEC_CMD_SWITCH_TO_STREAM_DLOAD = 0x05
    SAHARA_EXEC_CMD_READ_DEBUG_DATA = 0x06
    SAHARA_EXEC_CMD_GET_SOFTWARE_VERSION_SBL = 0x07
    
    SAHARA_MODE_IMAGE_TX_PENDING = 0x0
    SAHARA_MODE_IMAGE_TX_COMPLETE = 0x1
    SAHARA_MODE_MEMORY_DEBUG = 0x2
    SAHARA_MODE_COMMAND = 0x3
    
    def __init__(self, hash,serial,hwid,sblversion,verbose=0):
        descriptors = { }
        self.hwid=hwid
        self.hash=hash
        self.serial=serial
        self.sblversion=sblversion
        self.count=0
        self.timer=None
        self.switch=0
        self.bytestoread=0
        self.bytestotal=0
        self.curoffset=0
        self.buffer=bytes(b'')
        self.loader=bytes(b'')
        self.receive_buffer = bytes(b'')
        
        self.endpoints = [
        USBEndpoint(
                1,          # endpoint number
                USBEndpoint.direction_out,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                512,      # max packet size
                0,          # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available      # handler function
            ),
        USBEndpoint(
                3,          # endpoint number
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                512,      # max packet size
                0,          # polling interval, see USB 2.0 spec Table 9-13
                self.handle_buffer_available       # handler function
            )]

        # TODO: un-hardcode string index (last arg before "verbose")
        USBInterface.__init__(
                self,
                0,          # interface number
                0,          # alternate setting
                USBClass(), # interface class: vendor-specific
                0xff,       # subclass: vendor-specific
                0xff,       # protocol: vendor-specific
                0,          # string index
                verbose,
                self.endpoints,
                descriptors
        )

    def send_on_endpoint(self, ep, data):
        if ep==3:
            return self.endpoints[1].send(data)
        elif ep==1:
            return self.endpoints[0].send(data)
        assert("Send_on_endpoint: wrong endpoint given.")
        
    def send_data(self, data):
        #print ("TX: ")
        #rec=binascii.hexlify(data)
        #print(rec)
        self.send_on_endpoint(3,data)
        #self.txq.put(data)

    def bytes_as_hex(self, b, delim=" "):
        return delim.join(["%02x" % x for x in b])

    def handle_data_available(self, data):
        if (self.switch>=2):
            if (len(self.buffer)<self.bytestoread):
                self.buffer+=bytes(data)
                if (len(self.buffer)==self.bytestoread):
                   data=self.buffer
                   self.buffer=bytes(b'')
                   print("Complete RX")
                else:
                   print("Queueing, total: %x of %x" % (len(self.buffer),self.bytestoread))
                   return
            else:
                data=self.buffer
                self.buffer=bytes(b'')
                print("Complete RX")

        #print("RX: ")
        #rec=binascii.hexlify(data)
        #print(rec)
        if len(data) == 0:
            return
        opcode=data[0]
        if (self.switch==0 and opcode==0x3A):
            print("Got download request.")
            init= b"\x7E\x02\x6A\xD3\x7E"
            self.send_data(init)
        elif (self.switch==0):
            print ("Opcode : %x" % opcode)
            if (self.count==0):
                print("Pre init.")
                init = b"\x01\x00\x00\x00\x30\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                self.send_data(init)
                self.count += 1
            elif opcode == self.SAHARA_SWITCH_MODE: #0xC
                print("Got SAHARA_SWITCH_self.")
                request = struct.Struct('<III')
                req = request.unpack(bytes(data))
                '''
                if (req[2]==self.SAHARA_MODE_IMAGE_TX_PENDING): #0
                    request=request
                '''
                if (req[2]==self.SAHARA_MODE_IMAGE_TX_COMPLETE): #1
                    print("SAHARA_MODE_IMAGE_TX_COMPLETE")
                    reply = struct.Struct('<IIIIIIIIIIII')
                    packet = reply.pack(0x01,0x30,0x02,0x01,0x400,0x1,0x0,0x0,0x0,0x0,0x0,0x0)
                    self.send_data(packet)
                elif (req[2]==self.SAHARA_MODE_COMMAND): #3
                    print("SAHARA_MODE_COMMAND")
                    init = b"\x01\x00\x00\x00\x30\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                    self.send_on_endpoint(3, init)
                    #self.count=0
                    #self.switch=0
                '''
                elif (req[2]==self.SAHARA_MODE_MEMORY_DEBUG): #2
                    request=request
                '''
                print("Done SAHARA_SWITCH_self.")

            elif opcode==self.SAHARA_HELLO_RSP: #02
                print("Got SAHARA_HELLO_RSP")
                request = struct.Struct('<IIIIII')
                req = request.unpack(bytes(data[:24]))
                if (req[5]==0x3): #mode
                    packet = struct.pack('<II', 0xB, 0x8)
                    self.send_data(packet)
                elif (req[5]==0x0 or req[5]==0x1): #mode, send loader
                    packet = struct.pack('<IIIII', 0x3, 0x14, 0xD, 0x0, 0x50)
                    self.send_data(packet)
                    self.switch=1
                    self.bytestoread=0x50
                #elif (req[5]==0x1): #mode
                #    packet = struct.pack('<II', 0xB, 0x8)
                #    self.send_data(packet)
                print("Done SAHARA_HELLO_RSP.")
                self.count += 1
            elif opcode == self.SAHARA_EXECUTE_REQ: #0D
                print("Got SAHARA_EXECUTE_REQ")
                request = struct.Struct('<III')
                reply = struct.Struct('<IIII')
                req = request.unpack(bytes(data))
                '''
                if req[2] == self.SAHARA_EXEC_CMD_NOP:
                    packet = reply.pack(self.SAHARA_EXECUTE_RSP, 0x10, self.SAHARA_EXEC_CMD_NOP, 0x0) #Reply, unk, cmd, replysize
                '''
                if req[2] == self.SAHARA_EXEC_CMD_SERIAL_NUM_READ: #1
                    packet = reply.pack(self.SAHARA_EXECUTE_RSP, 0x10, self.SAHARA_EXEC_CMD_SERIAL_NUM_READ, 0x4) #Reply 0xE, unk, cmd, replysize
                elif req[2] == self.SAHARA_EXEC_CMD_MSM_HW_ID_READ: #2
                    packet = reply.pack(self.SAHARA_EXECUTE_RSP, 0x10, self.SAHARA_EXEC_CMD_MSM_HW_ID_READ, 0x18)
                elif req[2] == self.SAHARA_EXEC_CMD_OEM_PK_HASH_READ: #3
                    packet = reply.pack(self.SAHARA_EXECUTE_RSP, 0x10, self.SAHARA_EXEC_CMD_OEM_PK_HASH_READ, 0x60)
                elif req[2] == self.SAHARA_EXEC_CMD_GET_SOFTWARE_VERSION_SBL: #7
                    packet = reply.pack(self.SAHARA_EXECUTE_RSP, 0x10, self.SAHARA_EXEC_CMD_GET_SOFTWARE_VERSION_SBL, 0x4)
                '''
                elif req[2] == self.SAHARA_EXEC_CMD_SWITCH_TO_DMSS_DLOAD: #4
                    packet = reply.pack(self.SAHARA_EXECUTE_RSP, 0x10, self.SAHARA_EXEC_CMD_SWITCH_TO_DMSS_DLOAD, 0x40)
                elif req[2] == self.SAHARA_EXEC_CMD_SWITCH_TO_STREAM_DLOAD: #5
                    packet = reply.pack(self.SAHARA_EXECUTE_RSP, 0x10, self.SAHARA_EXEC_CMD_SWITCH_TO_STREAM_DLOAD, 0x40)
                elif req[2] == self.SAHARA_EXEC_CMD_READ_DEBUG_DATA: #6
                    packet = reply.pack(self.SAHARA_EXECUTE_RSP, 0x10, self.SAHARA_EXEC_CMD_READ_DEBUG_DATA, 0x40)
                '''
                
                self.send_data(packet)
                print("Done SAHARA_EXECUTE_REQ.")
            elif opcode == self.SAHARA_EXECUTE_DATA: #0xF
                print("Got SAHARA_EXECUTE_DATA.")
                request = struct.Struct('<III')
                req = request.unpack(bytes(data))
                if req[2] == self.SAHARA_EXEC_CMD_SERIAL_NUM_READ: #1
                    reply = struct.Struct('<I')
                    packet = reply.pack(self.serial)
                elif req[2] == self.SAHARA_EXEC_CMD_MSM_HW_ID_READ: #2
                    reply = struct.Struct('8s8s8s')
                    packet = reply.pack(self.hwid, self.hwid, self.hwid)
                elif req[2] == self.SAHARA_EXEC_CMD_OEM_PK_HASH_READ: #3
                    reply = struct.Struct('32s32s32s')
                    packet = reply.pack(self.hash, self.hash, self.hash)
                elif req[2] == self.SAHARA_EXEC_CMD_GET_SOFTWARE_VERSION_SBL: #7
                    reply = struct.Struct('<I')
                    packet = reply.pack(self.sblversion)
                '''
                elif req[2] == self.SAHARA_EXEC_CMD_SWITCH_TO_DMSS_DLOAD: #4
                    packet = reply.pack(self.SAHARA_EXECUTE_RSP, 0x10, self.SAHARA_EXEC_CMD_SWITCH_TO_DMSS_DLOAD, 0x40)
                elif req[2] == self.SAHARA_EXEC_CMD_SWITCH_TO_STREAM_DLOAD: #5
                    packet = reply.pack(self.SAHARA_EXECUTE_RSP, 0x10, self.SAHARA_EXEC_CMD_SWITCH_TO_STREAM_DLOAD, 0x40)
                elif req[2] == self.SAHARA_EXEC_CMD_READ_DEBUG_DATA: #6
                    packet = reply.pack(self.SAHARA_EXECUTE_RSP, 0x10, self.SAHARA_EXEC_CMD_READ_DEBUG_DATA, 0x40)
                '''
                self.send_data(packet)
                print("Done SAHARA_EXECUTE_DATA.")
        elif (self.switch==1):
                print("Loader read Init")
                request = struct.Struct('<IIIIIIII')
                req = request.unpack(bytes(data[0:32]))
                if req[0]==0x464c457F:
                    self.elfstart = struct.Struct('<I').unpack(bytes(data[0x20:0x24]))[0]
                    self.bytestotal=0x4000
                    self.switch=2
                    print("ELF Loader detected, ProgHdr start: %x" % self.elfstart)
                else:
                    print("QC Loader detected")
                    self.bytestotal=req[7]
                    self.reallen=req[7]
                    self.switch=3
                print("Reading length: "+hex(self.bytestotal))
                self.curoffset=0x50
                self.loader+=bytes(data)
                packet = struct.pack('<IIIII', 0x3, 0x13, 0xD, self.curoffset, 0x1000)
                self.bytestoread=0x1000
                self.send_data(packet)
        elif (self.switch==2):
                print("ELF read")
                x=self.elfstart
                self.loader+=bytes(data)
                self.bytestotal=0x0
                while (1):
                    start = struct.Struct('<Q').unpack(bytes(self.loader[(x+0x8):(x+0x8+0x8)]))[0]
                    length = struct.Struct('<Q').unpack(bytes(self.loader[(x+0x20):(x+0x20+0x8)]))[0]
                    if (start+length)==0:
                        break
                    self.bytestotal = start+length
                    #print("start : "+hex(start))
                    #print("length : "+hex(length))
                    x+=0x38
                print("Reading length: "+hex(self.bytestotal))
                self.reallen=self.bytestotal
                self.curoffset=0x1050
                self.bytestotal-=(0x1000-0x50)
                self.switch=3
                packet = struct.pack('<IIIII', 0x3, 0x13, 0xD, self.curoffset, 0x1000)
                self.bytestoread=0x1000
                self.send_data(packet)
        elif self.switch==3:
                print("Loader reading")
                self.loader+=bytes(data)
                self.bytestotal-=len(data)
                if (self.bytestotal<=0):
                   packet = struct.pack('<IIII', 0x4, 0x10, 0xD, 0x0)
                   self.send_data(packet)
                   self.switch=0
                   self.bytestoread=0
                   hwidstr=''.join('{:02X}'.format(x) for x in self.hwid)
                   with open(hwidstr+".bin","wb") as ft:
                        ft.write(self.loader[0:self.reallen])
                        print("We received all loader, stored as: %s" % (hwidstr+".bin"))
                   print("All loader done.")
                else:
                   toread=self.bytestotal
                   if (toread>0x1000):
                       toread=0x1000
                   self.curoffset+=toread
                   packet = struct.pack('<IIIII', 0x3, 0x14, 0xD, self.curoffset, 0x1000)
                   self.bytestoread=toread
                   self.send_data(packet)
                   print("Loader to read : %x" % self.bytestotal)

    def handle_buffer_available(self):
             if self.count==0:
                print("Buffer got called")
                init = b"\x01\x00\x00\x00\x30\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                self.send_on_endpoint(3,init)
                self.count += 1

class USBSaharaDevice(USBDevice):
    name = "USB QC Sahara EDL Device"

    def __init__(self, maxusb_app, verbose=0):
    
        #z ultra c 6833 msm8974_23_4_aid_4
        #hash = bytearray.fromhex("49109A8016C239CD8F76540FE4D5138C87B2297E49C6B30EC31852330BDDB177")
        #hwid = 0x04000100E1007B00
        #serial = 0x01678739
        #sblversion = 0x00000000

        #oneplus one 3t
        hash = bytearray.fromhex("c0c66e278fe81226585252b851370eabf8d4192f0f335576c3028190d49d14d4")
        serial = 0x8d3e01ed
        hwid = bytearray.fromhex("B93D702AE1F00500")
        sblversion = 0x00000002

        #Unfused hash:
        #hash = bytearray.fromhex("CC3153A80293939B90D02D3BF8B23E0292E452FEF662C74998421ADAD42A380F"
        #hash = bytearray.fromhex("1801000F43240892D02F0DC96313C81351B40FD5029ED98FF9EC7074DDAE8B05CDC8E1")
        #hash = bytearray.fromhex("5A93232B8EF5567752D0CB5554835215D1C473502E6F1052A78A6715B8B659AA")

        interface = USBSaharaInterface(hash,serial,hwid,sblversion,verbose=verbose)

        config = USBConfiguration(
                1,                                          # index
                "Sahara",                                   # string desc
                [ interface ]                               # interfaces
        )

        USBDevice.__init__(
                self,
                maxusb_app,
                0,                      # device class
                0,                      # device subclass
                0,                      # protocol release number
                64,                     # max packet size for endpoint 0
                0x05C6,                 # vendor id: HP
                0x9008,                 # product id: HP50G
                0x0100,                 # device revision
                "Qualcomm CDMA Technologies MSM", # manufacturer string
                "QHUSB__BULK",        # product string
                "",                # serial number string
                [ config ],
                verbose=verbose
        )

        self.device_vendor = USBSaharaVendor()
        self.device_vendor.set_device(self)

