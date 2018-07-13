'''
USB Class definitions for Qualcomm QDLoader 9008 Firehose
(c) B. Kerler 2018
At least set up hwid and hash.
serial and sbversion is optional for testing.
Supports extraction of firehose/EDL loaders, saves as [hwid].bin in local directory
'''

import time
try:
    from six.moves.queue import Queue # Python 3
except ImportError:
    from six.moves.queue import queue as Queue # Python 2

import binascii
from facedancer.usb.USBDevice import *
from facedancer.usb.USBConfiguration import *
from facedancer.usb.USBInterface import *
from facedancer.usb.USBEndpoint import *
from facedancer.usb.USBVendor import *

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
    
    def __init__(self, phy, hash,serial,hwid,sblversion):
        self.phy=phy
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

        endpoints = [
        USBEndpoint(
                phy=phy,
                number=1,          # endpoint number
                direction=USBEndpoint.direction_out,
                transfer_type=USBEndpoint.transfer_type_bulk,
                sync_type=USBEndpoint.sync_type_none,
                usage_type=USBEndpoint.usage_type_data,
                max_packet_size=64,      # max packet size
                interval=0,          # polling interval, see USB 2.0 spec Table 9-13
                handler=self.handle_data_available      # handler function
            ),
        USBEndpoint(
                phy=phy,
                number=3,          # endpoint number
                direction=USBEndpoint.direction_in,
                transfer_type=USBEndpoint.transfer_type_bulk,
                sync_type=USBEndpoint.sync_type_none,
                usage_type=USBEndpoint.usage_type_data,
                max_packet_size=64,      # max packet size
                interval=0,          # polling interval, see USB 2.0 spec Table 9-13
                handler=self.handle_buffer_available       # handler function
            )]

        # TODO: un-hardcode string index
        super(USBSaharaInterface, self).__init__(
                phy=phy,
                interface_number=0,          # interface number
                interface_alternate=0,          # alternate setting
                interface_class=0xff,
                interface_subclass=0xff,       # subclass: vendor-specific
                interface_protocol=0xff,       # protocol: vendor-specific
                interface_string_index=0,          # string index
                endpoints=endpoints,
                usb_class=None
        )

    def bytes_as_hex(self, b, delim=" "):
        return delim.join(["%02x" % x for x in b])

    def handle_payload(self,data):
        #print("RX: ")
        #rec=binascii.hexlify(data)
        #print(rec)
        if type(data[0])==int:
            opcode=data[0]
        else:
            opcode=ord(data[0])
            
        if (self.switch==0 and opcode==0x3A):
            self.info("Got download request.")
            init= b"\x7E\x02\x6A\xD3\x7E"
            return init
        elif (self.switch==0):
            self.info("Opcode : %x" % opcode)
            if (self.count==0):
                self.info("Pre init.")
                init = b"\x01\x00\x00\x00\x30\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                self.count += 1
                return init
            elif opcode == self.SAHARA_SWITCH_MODE: #0xC
                self.info("Got SAHARA_SWITCH_self.")
                request = struct.Struct('<III')
                req = request.unpack(bytes(data))
                '''
                if (req[2]==self.SAHARA_MODE_IMAGE_TX_PENDING): #0
                    request=request
                '''
                if (req[2]==self.SAHARA_MODE_IMAGE_TX_COMPLETE): #1
                    self.info("SAHARA_MODE_IMAGE_TX_COMPLETE")
                    reply = struct.Struct('<IIIIIIIIIIII')
                    packet = reply.pack(0x01,0x30,0x02,0x01,0x400,0x1,0x0,0x0,0x0,0x0,0x0,0x0)
                    return packet
                elif (req[2]==self.SAHARA_MODE_COMMAND): #3
                    self.info("SAHARA_MODE_COMMAND")
                    init = b"\x01\x00\x00\x00\x30\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                    return init
                    #self.count=0
                    #self.switch=0
                '''
                elif (req[2]==self.SAHARA_MODE_MEMORY_DEBUG): #2
                    request=request
                '''

            elif opcode==self.SAHARA_HELLO_RSP: #02
                self.info("Got SAHARA_HELLO_RSP")
                request = struct.Struct('<IIIIII')
                req = request.unpack(bytes(data[:24]))
                if (req[5]==0x3): #mode
                    packet = struct.pack('<II', 0xB, 0x8)
                    self.count += 1
                    return packet
                elif (req[5]==0x0 or req[5]==0x1): #mode, send loader
                    packet = struct.pack('<IIIII', 0x3, 0x14, 0xD, 0x0, 0x50)
                    self.switch=1
                    self.bytestoread=0x50
                    self.count += 1
                    return packet
                #elif (req[5]==0x1): #mode
                #    packet = struct.pack('<II', 0xB, 0x8)
                #    self.send_data(packet)
            elif opcode == self.SAHARA_EXECUTE_REQ: #0D
                self.info("Got SAHARA_EXECUTE_REQ")
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
                
                return packet
            elif opcode == self.SAHARA_EXECUTE_DATA: #0xF
                self.info("Got SAHARA_EXECUTE_DATA.")
                request = struct.Struct('<III')
                req = request.unpack(bytes(data))
                if req[2] == self.SAHARA_EXEC_CMD_SERIAL_NUM_READ: #1
                    reply = struct.Struct('<I')
                    packet = reply.pack(self.serial)
                elif req[2] == self.SAHARA_EXEC_CMD_MSM_HW_ID_READ: #2
                    reply = struct.Struct('8s8s8s')
                    hwidstr=struct.pack("<Q",self.hwid)
                    if type(hwidstr)==str:
                        hwidstr=str(hwidstr)
                    packet = reply.pack(hwidstr, hwidstr, hwidstr)
                elif req[2] == self.SAHARA_EXEC_CMD_OEM_PK_HASH_READ: #3
                    reply = struct.Struct('32s32s32s')
                    if type(self.hash)==str:
                        hash=str(self.hash)
                    else:
                        hash=self.hash
                    packet = reply.pack(hash, hash, hash)
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
                return packet
        elif self.switch==1:
                self.info("Loader read Init")
                request = struct.Struct('<IIIIIIII')
                req = request.unpack(bytes(data[0:32]))
                if req[0]==0x464c457F:
                    self.elfstart = struct.Struct('<I').unpack(bytes(data[0x20:0x24]))[0]
                    self.bytestotal=0x4000
                    self.switch=2
                    self.info("ELF Loader detected, ProgHdr start: %x" % self.elfstart)
                else:
                    self.info("QC Loader detected")
                    self.bytestotal=req[7]
                    self.reallen=req[7]
                    self.switch=3
                self.info("Reading length: "+hex(self.bytestotal))
                self.curoffset=0x50
                self.loader+=bytes(data)
                packet = struct.pack('<IIIII', 0x3, 0x13, 0xD, self.curoffset, 0x1000)
                self.bytestoread=0x1000
                return packet
        elif self.switch==2:
                self.info("ELF read")
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
                self.info("Reading length: "+hex(self.bytestotal))
                self.reallen=self.bytestotal
                self.curoffset=0x1050
                self.bytestotal-=(0x1000-0x50)
                self.switch=3
                packet = struct.pack('<IIIII', 0x3, 0x13, 0xD, self.curoffset, 0x1000)
                self.bytestoread=0x1000
                return packet
        elif self.switch==3:
                self.loader+=bytes(data)
                self.bytestotal-=len(data)
                if (self.bytestotal>0):
                   toread=self.bytestotal
                   if (toread>0x1000):
                       toread=0x1000
                   self.curoffset+=toread
                   self.bytestoread=toread
                   self.info("Bytes left for reading : %x" % self.bytestotal)
                else:
                    self.switch = 0
                    self.bytestoread = 0
                    hwidf = "{0:0{1}X}".format(self.hwid,16)+".bin"
                    with open(hwidf, "wb") as ft:
                        ft.write(self.loader[0:self.reallen])
                        self.info("We received all loader, stored as: %s" % (hwidf))
                    self.info("All loader done.")
                    return (struct.pack('<IIII', 0x4, 0x10, 0xD, 0x0))
                    
    def handle_data_available(self, data):
        if len(data) == 0:
            return
        if (self.switch>=2):
            if (len(self.buffer)<self.bytestoread):
                self.buffer+=bytes(data)
                if (len(self.buffer)==self.bytestoread):
                   data=self.buffer
                   self.buffer=bytes(b'')
                   self.debug("Complete RX, sending ack")
                   packet = struct.pack('<IIIII', 0x3, 0x14, 0xD, self.curoffset, 0x1000)
                   self.send_on_endpoint(3, packet)
                else:
                   self.verbose("Queueing, total: %x of %x" % (len(self.buffer),self.bytestoread))
                   return
            else:
                data=self.buffer
                self.buffer=bytes(b'')
                self.debug("Complete RX")

        resp=self.handle_payload(data)
        if resp:
            self.debug("TX: "+str(binascii.hexlify(resp)))
            self.send_on_endpoint(3, resp)
            #self.endpoints[1].send(resp)

    def handle_buffer_available(self):
        if self.count==0:
            self.info("Buffer got called")
            init = b"\x01\x00\x00\x00\x30\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            self.endpoints[1].send(init)
            #self.send_on_endpoint(3,init)
            self.count += 1
               

class USBSaharaDevice(USBDevice):
    name = "USB QC Sahara EDL Device"

    def __init__(self, phy):
    
        #z ultra c 6833 msm8974_23_4_aid_4
        #hash = bytearray.fromhex("49109A8016C239CD8F76540FE4D5138C87B2297E49C6B30EC31852330BDDB177")
        #hwid = 0x04000100E1007B00
        #serial = 0x01678739
        #sblversion = 0x00000000

        #oneplus one 3t
        hash = bytearray.fromhex("c0c66e278fe81226585252b851370eabf8d4192f0f335576c3028190d49d14d4")
        serial = 0x8d3e01ed
        hwid = 0x0005F0E12A703DB9
        sblversion = 0x00000002


        #Unfused hash:
        #hash = bytearray.fromhex("CC3153A80293939B90D02D3BF8B23E0292E452FEF662C74998421ADAD42A380F"
        #hash = bytearray.fromhex("1801000F43240892D02F0DC96313C81351B40FD5029ED98FF9EC7074DDAE8B05CDC8E1")
        #hash = bytearray.fromhex("5A93232B8EF5567752D0CB5554835215D1C473502E6F1052A78A6715B8B659AA")

        interface = USBSaharaInterface(phy,hash,serial,hwid,sblversion)

        config = [ 
                USBConfiguration(
                phy=phy,
                configuration_index=1,                                          # index
                configuration_string_or_index="Sahara",                                   # string desc
                interfaces=[ interface ]                               # interfaces
                )
        ]

        super(USBSaharaDevice, self).__init__(
                phy=phy,
                device_class=USBClass.Unspecified,                      # device class
                device_subclass=0,                      # device subclass
                protocol_rel_num=0,                      # protocol release number
                max_packet_size_ep0=64,                     # max packet size for endpoint 0
                vendor_id=0x05C6,                 # vendor id
                product_id=0x9008,                 # product id
                device_rev=0x0100,                 # device revision
                manufacturer_string="Qualcomm CDMA Technologies MSM",                # manufacturer string
                product_string="QHUSB__BULK",               # product string
                serial_number_string="12345",   # serial number string
                configurations=config,
                usb_vendor = USBSaharaVendor(phy=phy)
        )
