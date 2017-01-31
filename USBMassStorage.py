# USBMassStorage.py 
#
# Contains class definitions to implement a USB mass storage device.

from mmap import mmap
import os

from facedancer.USB import *
from facedancer.USBDevice import *
from facedancer.USBConfiguration import *
from facedancer.USBInterface import *
from facedancer.USBEndpoint import *
from facedancer.USBVendor import *

def bytes_as_hex(b, delim=" "):
    return delim.join(["%02x" % x for x in b])

class USBMassStorageClass(USBClass):
    name = "USB mass storage class"

    def setup_request_handlers(self):
        self.request_handlers = {
            0xFF : self.handle_bulk_only_mass_storage_reset_request,
            0xFE : self.handle_get_max_lun_request
        }

    def handle_bulk_only_mass_storage_reset_request(self, req):
        self.interface.configuration.device.send_control_message(b'')

    def handle_get_max_lun_request(self, req):
        self.interface.configuration.device.send_control_message(b'\x00')


class USBMassStorageInterface(USBInterface):
    name = "USB mass storage interface"

    def __init__(self, disk_image, verbose=0):
        self.disk_image = disk_image
        descriptors = { }

        self.ep_from_host = USBEndpoint(
                1,          # endpoint number
                USBEndpoint.direction_out,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                1024,      # max packet size
                0,          # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available    # handler function
        )
        self.ep_to_host = USBEndpoint(
                3,          # endpoint number
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                1024,       # max packet size
                0,          # polling interval, see USB 2.0 spec Table 9-13
                None        # handler function
        )

        # TODO: un-hardcode string index (last arg before "verbose")
        USBInterface.__init__(
                self,
                0,          # interface number
                0,          # alternate setting
                8,          # interface class: Mass Storage
                6,          # subclass: SCSI transparent command set
                0x50,       # protocol: bulk-only (BBB) transport
                0,          # string index
                verbose,
                [ self.ep_from_host, self.ep_to_host ],
                descriptors
        )

        self.device_class = USBMassStorageClass()
        self.device_class.set_interface(self)

        self.is_write_in_progress = False
        self.write_cbw = None
        self.write_base_lba = 0
        self.write_length = 0
        self.write_data = b''

    def handle_data_available(self, data):
        print(self.name, "handling", len(data), "bytes of SCSI data")

        cbw = CommandBlockWrapper(data)
        opcode = cbw.cb[0]

        status = 0              # default to success
        response = None         # with no response data

        if self.is_write_in_progress:
            if self.verbose > 0:
                print(self.name, "got", len(data), "bytes of SCSI write data")

            self.write_data += data

            if len(self.write_data) < self.write_length:
                # more yet to read, don't send the CSW
                return

            self.disk_image.put_sector_data(self.write_base_lba, self.write_data)
            cbw = self.write_cbw

            self.is_write_in_progress = False
            self.write_data = b''

        elif opcode == 0x00:      # Test Unit Ready: just return OK status
            if self.verbose > 0:
                print(self.name, "got SCSI Test Unit Ready")

        elif opcode == 0x03:    # Request Sense
            if self.verbose > 0:
                print(self.name, "got SCSI Request Sense, data",
                        bytes_as_hex(cbw.cb[1:]))

            response = b'\x70\x00\xFF\x00\x00\x00\x00\x0A\x00\x00\x00\x00\xFF\xFF\x00\x00\x00\x00\x00\x00\x00\x00\x00'

        elif opcode == 0x12:    # Inquiry
            if self.verbose > 0:
                print(self.name, "got SCSI Inquiry, data",
                        bytes_as_hex(cbw.cb[1:]))

            response = bytes([
                0x00,       # 00 for Direct, 1F for "no floppy"
                0x00,       # make 0x80 for removable media, 0x00 for fixed
                0x00,       # Version
                0x01,       # Response Data Format
                0x14,       # Additional length.
                0x00, 0x00, 0x00
            ])

            response += b'GoodFET '         # vendor
            response += b'GoodFET '         # product id
            response += b'        '         # product revision
            response += b'0.01'

            # pad up to data_transfer_length bytes
            #diff = cbw.data_transfer_length - len(response)
            #response += bytes([0] * diff)

        elif opcode == 0x1a or opcode == 0x5a:    # Mode Sense (6 or 10)
            page = cbw.cb[2] & 0x3f

            if self.verbose > 0:
                print(self.name, "got SCSI Mode Sense, page code 0x%02x" % page)

            response = b'\x07\x00\x00\x00\x00\x00\x00\x1c'
            if page != 0x3f:
                print(self.name, "unkonwn page, returning empty page")
                response = b'\x07\x00\x00\x00\x00\x00\x00\x00'

        elif opcode == 0x1e:    # Prevent/Allow Removal: feign success
            if self.verbose > 0:
                print(self.name, "got SCSI Prevent/Allow Removal")

        #elif opcode == 0x1a or opcode == 0x5a:      # Mode Sense (6 or 10)
            # TODO

        elif opcode == 0x23:    # Read Format Capacity
            if self.verbose > 0:
                print(self.name, "got SCSI Read Format Capacity")

            response = bytes([
                0x00, 0x00, 0x00, 0x08,     # capacity list length
                0x00, 0x00, 0x10, 0x00,     # number of sectors (0x1000 = 10MB)
                0x10, 0x00,                 # reserved/descriptor code
                0x02, 0x00,                 # 512-byte sectors
            ])

        elif opcode == 0x25:    # Read Capacity
            if self.verbose > 0:
                print(self.name, "got SCSI Read Capacity, data",
                        bytes_as_hex(cbw.cb[1:]))

            lastlba = self.disk_image.get_sector_count()

            response = bytes([
                (lastlba >> 24) & 0xff,
                (lastlba >> 16) & 0xff,
                (lastlba >>  8) & 0xff,
                (lastlba      ) & 0xff,
                0x00, 0x00, 0x02, 0x00,     # 512-byte blocks
            ])

        elif opcode == 0x28:    # Read (10)
            base_lba = cbw.cb[2] << 24 \
                     | cbw.cb[3] << 16 \
                     | cbw.cb[4] << 8 \
                     | cbw.cb[5]

            num_blocks = cbw.cb[7] << 8 \
                       | cbw.cb[8]

            if self.verbose > 0:
                print(self.name, "got SCSI Read (10), lba", base_lba, "+",
                        num_blocks, "block(s)")
                        

            # Note that here we send the data directly rather than putting
            # something in 'response' and letting the end of the switch send
            for block_num in range(num_blocks):
                data = self.disk_image.get_sector_data(base_lba + block_num)
                self.ep_to_host.send(data)

        elif opcode == 0x2a:    # Write (10)
            if self.verbose > 0:
                print(self.name, "got SCSI Write (10), data",
                        bytes_as_hex(cbw.cb[1:]))

            base_lba = cbw.cb[1] << 24 \
                     | cbw.cb[2] << 16 \
                     | cbw.cb[3] <<  8 \
                     | cbw.cb[4]

            num_blocks = cbw.cb[7] << 8 \
                       | cbw.cb[8]

            if self.verbose > 0:
                print(self.name, "got SCSI Write (10), lba", base_lba, "+",
                        num_blocks, "block(s)")

            # save for later
            self.write_cbw = cbw
            self.write_base_lba = base_lba
            self.write_length = num_blocks * self.disk_image.block_size
            self.is_write_in_progress = True

            # because we need to snarf up the data from wire before we reply
            # with the CSW
            return

        elif opcode == 0x35:    # Synchronize Cache (10): blindly OK
            if self.verbose > 0:
                print(self.name, "got Synchronize Cache (10)")

        else:
            print(self.name, "received unsupported SCSI opcode 0x%x" % opcode)
            status = 0x02   # command failed
            if cbw.data_transfer_length > 0:
                response = bytes([0] * cbw.data_transfer_length)

        if response:
            if self.verbose > 2:
                print(self.name, "responding with", len(response), "bytes:",
                        bytes_as_hex(response))

            self.ep_to_host.send(response)

        csw = bytes([
            ord('U'), ord('S'), ord('B'), ord('S'),
            cbw.tag[0], cbw.tag[1], cbw.tag[2], cbw.tag[3],
            0x00, 0x00, 0x00, 0x00,
            status
        ])

        if self.verbose > 3:
            print(self.name, "responding with status =", status)

        self.ep_to_host.send(csw)


class DiskImage:
    def __init__(self, filename, block_size):
        self.filename = filename
        self.block_size = block_size

        statinfo = os.stat(self.filename)
        self.size = statinfo.st_size

        self.file = open(self.filename, 'r+b')
        self.image = mmap(self.file.fileno(), 0)

    def close(self):
        self.image.flush()
        self.image.close()

    def get_sector_count(self):
        return int(self.size / self.block_size) - 1

    def get_sector_data(self, address):
        block_start = address * self.block_size
        block_end   = (address + 1) * self.block_size   # slices are NON-inclusive

        return self.image[block_start:block_end]

    def put_sector_data(self, address, data):
        block_start = address * self.block_size
        block_end   = (address + 1) * self.block_size   # slices are NON-inclusive

        self.image[block_start:block_end] = data[:self.block_size]
        self.image.flush()


class CommandBlockWrapper:
    def __init__(self, bytestring):
        self.signature              = bytestring[0:4]
        self.tag                    = bytestring[4:8]
        self.data_transfer_length   = bytestring[8] \
                                    | bytestring[9] << 8 \
                                    | bytestring[10] << 16 \
                                    | bytestring[11] << 24
        self.flags                  = int(bytestring[12])
        self.lun                    = int(bytestring[13] & 0x0f)
        self.cb_length              = int(bytestring[14] & 0x1f)
        #self.cb                     = bytestring[15:15+self.cb_length]
        self.cb                     = bytestring[15:]

    def __str__(self):
        s  = "sig: " + bytes_as_hex(self.signature) + "\n"
        s += "tag: " + bytes_as_hex(self.tag) + "\n"
        s += "data transfer len: " + str(self.data_transfer_length) + "\n"
        s += "flags: " + str(self.flags) + "\n"
        s += "lun: " + str(self.lun) + "\n"
        s += "command block len: " + str(self.cb_length) + "\n"
        s += "command block: " + bytes_as_hex(self.cb) + "\n"

        return s


class USBMassStorageDevice(USBDevice):
    name = "USB mass storage device"

    def __init__(self, maxusb_app, disk_image_filename, verbose=0):
        self.disk_image = DiskImage(disk_image_filename, 512)

        interface = USBMassStorageInterface(self.disk_image, verbose=verbose)

        config = USBConfiguration(
                1,                                          # index
                "Maxim umass config",                       # string desc
                [ interface ]                               # interfaces
        )

        USBDevice.__init__(
                self,
                maxusb_app,
                0,                      # device class
                0,                      # device subclass
                0,                      # protocol release number
                64,                     # max packet size for endpoint 0
                0x8107,                 # vendor id: Sandisk
                0x5051,                 # product id: SDCZ2 Cruzer Mini Flash Drive (thin)
                0x0003,                 # device revision
                "Maxim",                # manufacturer string
                "MAX3420E Enum Code",   # product string
                "S/N3420E",             # serial number string
                [ config ],
                verbose=verbose
        )

    def disconnect(self):
        self.disk_image.close()
        USBDevice.disconnect(self)

