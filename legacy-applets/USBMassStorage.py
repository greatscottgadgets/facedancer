# USBMassStorage.py
#
# Contains class definitions to implement a USB mass storage device.

from mmap import mmap

import re
import os
import sys
import struct
import time

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

    UMS_CLASS_NUMBER            = 8
    DESCRIPTOR_TYPE_NUMBER      = 0

    def __init__(self):
        super().__init__(self.UMS_CLASS_NUMBER, None, self.DESCRIPTOR_TYPE_NUMBER)

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

    STATUS_OKAY       = 0x00
    STATUS_FAILURE    = 0x02 # TODO: Should this be 0x01?
    STATUS_INCOMPLETE = -1   # Special case status that aborts before response.

    def __init__(self, disk_image, verbose=0):
        self.disk_image = disk_image
        descriptors = { }

        self.ep_from_host = USBEndpoint(
                1,          # endpoint number
                USBEndpoint.direction_out,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                64,         # max packet size
                0,          # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available    # handler function
        )
        self.ep_to_host = USBEndpoint(
                3,          # endpoint number
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                64,         # max packet size
                0,          # polling interval, see USB 2.0 spec Table 9-13
                None        # handler function
        )

        dclass = USBMassStorageClass()

        # TODO: un-hardcode string index (last arg before "verbose")
        USBInterface.__init__(
                self,
                0,          # interface number
                0,          # alternate setting
                dclass,     # interface class: Mass Storage
                6,          # subclass: SCSI transparent command set
                0x50,       # protocol: bulk-only (BBB) transport
                0,          # string index
                verbose,
                [ self.ep_from_host, self.ep_to_host ],
                descriptors
        )

        self.device_class = dclass
        self.device_class.set_interface(self)

        self.is_write_in_progress = False
        self.write_cbw = None
        self.write_base_lba = 0
        self.write_length = 0
        self.write_data = b''

        self._initialize_scsi_commands()


    def _register_scsi_command(self, number, name, handler=None):

        if handler is None:
            handler = self.handle_unknown_command

        descriptor = {
            "number": number,
            "name": name,
            "handler": handler
        }

        self.commands[number] = descriptor


    def _initialize_scsi_commands(self):
        self.commands = {}

        self._register_scsi_command(0x00, "Test Unit Ready", self.handle_ignored_event)
        self._register_scsi_command(0x03, "Request Sense", self.handle_sense)
        self._register_scsi_command(0x12, "Inquiry", self.handle_inquiry)
        self._register_scsi_command(0x1a, "Mode Sense (6)", self.handle_mode_sense)
        self._register_scsi_command(0x5a, "Mode Sense (10)", self.handle_mode_sense)
        self._register_scsi_command(0x1e, "Prevent/Allow Removal", self.handle_ignored_event)
        self._register_scsi_command(0x23, "Get Format Capacity", self.handle_get_format_capacity)
        self._register_scsi_command(0x25, "Get Read Capacity", self.handle_get_read_capacity)
        self._register_scsi_command(0x28, "Read", self.handle_read)
        self._register_scsi_command(0x2a, "Write (10)", self.handle_write)
        self._register_scsi_command(0x36, "Synchronize Cache", self.handle_ignored_event)


    def handle_scsi_command(self, cbw):
        """
            Handles an SCSI command.
        """

        opcode = cbw.cb[0]
        direction = cbw.flags >> 7

        # If we have a handler for this routine, handle it.
        if opcode in self.commands:

            # Extract the command's data.
            command = self.commands[opcode]
            name    = command['name']
            handler = command['handler']
            direction_name = 'IN' if direction else 'OUT'
            direction_arrow = "<--" if direction else "-->"
            expected_length = cbw.data_transfer_length

            if self.verbose > 0:
                print("{} handling {} ({}) {}:[{}]".format(direction_arrow, name.upper(), direction_name, expected_length, bytes_as_hex(cbw.cb[1:])))

            # Delegate to its handler funciton.
            return handler(cbw)

        # Otherwise, run the unknown command handler.
        else:
            return self.handle_unknown_command(cbw)


    def handle_unknown_command(self, cbw):
        """
            Handles unsupported SCSI commands.
        """
        print(self.name, "received unsupported SCSI opcode 0x%x" % cbw.cb[0])

        # Generate an empty response to the relevant command.
        if cbw.data_transfer_length > 0:
            response = bytes([0] * cbw.data_transfer_length)
        else:
            response = None

        # Return failure.
        return self.STATUS_FAILURE, response


    def handle_ignored_event(self, cbw):
        """
            Handles SCSI events that we can safely ignore.
        """

        # Always return success, and no response.
        return self.STATUS_OKAY, None


    def handle_sense(self, cbw):
        """
            Handles SCSI sense requests.
        """
        response = b'\x70\x00\xFF\x00\x00\x00\x00\x0A\x00\x00\x00\x00\xFF\xFF\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        return self.STATUS_OKAY, response


    def handle_inquiry(self, cbw):
        opcode, flags, page_code, allocation_length, control = struct.unpack(">BBBHB", cbw.cb[0:6])

        # Print out the details of our inquiry.
        if self.verbose > 1:
            print("-- INQUIRY ({}) flags: {} page_code: {} allocation_length: {} control: {}". \
                  format(opcode, flags, page_code, allocation_length, control))

        response = bytes([
            0x00,       # 0x00 = device present, and provides direct access to blocks
            0x00,       # 0x00 = media not removable, 0x80 = media removable
            0x05,       # 0 = no standards compliance, 3 = SPC compliant, 4 = SPC-2 compliant, 5 = SCSI compliant :)
            0x02,       # 0x02 = data responses follow the spec
            0x14,       # Additional length.
            0x00, 0x00, 0x00
        ])

        response += b'GoodFET '         # vendor
        response += b'GoodFET '         # product id
        response += b'        '         # product revision
        response += b'0.01'

        # pad up to data_transfer_length bytes
        diff = cbw.data_transfer_length - len(response)
        response += bytes([0] * diff)

        return self.STATUS_OKAY, response


    def handle_mode_sense(self, cbw):
        page = cbw.cb[2] & 0x3f

        response = b'\x07\x00\x00\x00\x00\x00\x00\x1c'
        if page != 0x3f:
            print(self.name, "unkonwn page, returning empty page")
            response = b'\x07\x00\x00\x00\x00\x00\x00\x00'

        return self.STATUS_OKAY, response


    def handle_get_format_capacity(self, cbw):
        response = bytes([
            0x00, 0x00, 0x00, 0x08,     # capacity list length
            0x00, 0x00, 0x10, 0x00,     # number of sectors (0x1000 = 10MB)
            0x10, 0x00,                 # reserved/descriptor code
            0x02, 0x00,                 # 512-byte sectors
        ])
        return self.STATUS_OKAY, response


    def handle_get_read_capacity(self, cbw):
        lastlba = self.disk_image.get_sector_count()

        response = bytes([
            (lastlba >> 24) & 0xff,
            (lastlba >> 16) & 0xff,
            (lastlba >>  8) & 0xff,
            (lastlba      ) & 0xff,
            0x00, 0x00, 0x02, 0x00,     # 512-byte blocks
        ])
        return self.STATUS_OKAY, response


    def handle_read(self, cbw):
        base_lba = cbw.cb[2] << 24 \
                 | cbw.cb[3] << 16 \
                 | cbw.cb[4] << 8 \
                 | cbw.cb[5]

        num_blocks = cbw.cb[7] << 8 \
                   | cbw.cb[8]

        if self.verbose > 0:
            print("<-- performing READ (10), lba", base_lba, "+", num_blocks, "block(s)")

        # Note that here we send the data directly rather than putting
        # something in 'response' and letting the end of the switch send
        for block_num in range(num_blocks):
            data = self.disk_image.get_sector_data(base_lba + block_num)
            self.ep_to_host.send_packet(data, blocking=True)

        if self.verbose > 3:
            print("--> responded with {} bytes".format(cbw.data_transfer_length))

        return self.STATUS_OKAY, None


    def handle_write(self, cbw):
        base_lba = cbw.cb[2] << 24 \
                 | cbw.cb[3] << 16 \
                 | cbw.cb[4] <<  8 \
                 | cbw.cb[5]

        num_blocks = cbw.cb[7] << 8 \
                   | cbw.cb[8]

        if self.verbose > 0:
            print("--> performing WRITE (10), lba", base_lba, "+", num_blocks, "block(s)")

        # save for later
        self.write_cbw = cbw
        self.write_base_lba = base_lba
        self.write_length = num_blocks * self.disk_image.get_sector_size()
        self.is_write_in_progress = True

        # because we need to snarf up the data from wire before we reply
        # with the CSW
        return self.STATUS_INCOMPLETE, None


    def continue_write(self, cbw, data):
        if self.verbose > 3:
            print("--> continue write with {} more bytes of data".format(len(data)))

        self.write_data += data

        if len(self.write_data) < self.write_length:
            # more yet to read, don't send the CSW
            return self.STATUS_INCOMPLETE, None

        self.disk_image.put_data(self.write_base_lba, self.write_data)

        self.is_write_in_progress = False
        self.write_data = b''

        return self.STATUS_OKAY, None


    def handle_data_available(self, data):

        if self.is_write_in_progress:
            cbw = self.write_cbw
            status, response = self.continue_write(cbw, data)
        else:
            cbw = CommandBlockWrapper(data)
            status, response = self.handle_scsi_command(cbw)

        # If we weren't able to complete the operation, return without
        # transmitting a response.
        if status == self.STATUS_INCOMPLETE:
            return

        # If we have a response payload to transmit, transmit it.
        if response:
            if self.verbose > 2:
                print("--> responding with", len(response),
                      "bytes [{}], status={}".format(bytes_as_hex(response), status))

            self.ep_to_host.send_packet(response, blocking=True)

        # Otherwise, respond with our status.
        csw = bytes([
            ord('U'), ord('S'), ord('B'), ord('S'),
            cbw.tag[0], cbw.tag[1], cbw.tag[2], cbw.tag[3],
            0x00, 0x00, 0x00, 0x00,
            status
        ])

        self.ep_to_host.send_packet(csw, blocking=True)


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

    def __init__(self, maxusb_app, disk_image, verbose=0):
        self.disk_image = disk_image

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


class DiskImage:
    """
        Class representing an arbitrary disk image, which can be procedurally generated,
        or which can be rendered from e.g. a file.

        Currently limited to representing disk with 512-byte sectors.
    """

    def close(self):
        """ Closes and cleans up any resources held by the disk image. """
        pass

    def get_sector_size(self):
        return 512

    def get_sector_count(self):
        """ Returns the disk's sector count. """
        raise NotImplementedError()

    def get_data(self, address, length):
        data_to_read = length
        sector_size  = self.get_sector_size()
        data         = bytes()

        while data_to_read > 0:
            data.extend(self.get_sector_data(address))
            data_to_read -= sector_size

            address += 1

        return data


    def get_sector_data(self, address):
        """ Returns the raw binary data for a given sector. """
        raise NotImplementedError()


    def put_data(self, address, data):
        sector_size   = self.get_sector_size()

        while data:
            sector = data[:sector_size]
            data   = data[sector_size:]

            self.put_sector_data(address, sector)
            address += 1

        return data

    def put_sector_data(self, address, data):
        """ Sets the raw binary data for a given disk sector. """
        sys.stderr.write("WARNING: UMS write ignored; this type of image does not support writing.\n")


class FAT32DiskImage(DiskImage):
    """
    Class for manufacturing synthetic FAT32 disk images.
    """

    CLUSTER_SIZE         = 512

    MBR_SECTOR           = 0
    BPB_SECTOR           = 2048   # set by our MBR partition entry
    FSINFO_SECTOR        = 2049   # set by our BPB entry
    FAT_START            = 2080   # specified by our BPB entry (partition start + reserved sectors)
    FAT_END              = 6113   # specified by our BPB entry (fat start + fat size)
    DATA_SECTION_START   = 10146  # specified by our BPB entry (fat start + num_fats * fat_size)
    ROOT_DIR_ENTRY       = 10146  # specified by our BPB entry (we put the directory at the very start)

    def __init__(self, size = 1024 * 1024 * 256, verbose=0):
        self.verbose = verbose
        self.size = size

        # Initialize the commands we'll use to handle sector writes.
        self._initialize_sector_handlers()


    def _register_sector_handler(self, sector_or_lambda, name, handler=None):

        if handler is None:
            handler = self.handle_unhandled_sector

        descriptor = {
            "sector_or_lambda": sector_or_lambda,
            "name": name,
            "handler": handler
        }

        self.sector_handlers.append(descriptor)


    def _initialize_sector_handlers(self):
        self.sector_handlers = []

        # Handlers for disk special sectors...
        self._register_sector_handler(self.MBR_SECTOR, "MBR/partition table", self.handle_mbr_read)
        self._register_sector_handler(self.BPB_SECTOR, "BIOS Parameter Block", self.handle_bpb_read)
        self._register_sector_handler(self.FSINFO_SECTOR, "FSINFO Block", self.handle_fsinfo_read)
        self._register_sector_handler(lambda x : x >= self.FAT_START and x < self.FAT_END, "File Allocation Table", self.handle_fat_read)
        self._register_sector_handler(self.ROOT_DIR_ENTRY, "Root Directory", self.handle_root_dir_read)


    def handle_mbr_read(self, address):
        """
        Returns a master boot record directing the target device to our
        emulated FAT32 partition.
        """

        response  = 440 * b'\0'                           # bootstrap code + timestamp
        response += b'\xDE\xAD\xBE\xEF'                   # disk signature (we're making one up)
        response += b'\x00\x00'                           # 0 = not copy protected
        response += self._generate_fat_partition_entry()  # partition entry for our FAT32 partition
        response += (16 * 3) * b'\0'                      # three empty partition slots
        response += b'\x55\xAA'                           # end of sector signature
        return response


    def handle_bpb_read(self, address):
        """
            Returns a valid Boot Parameter Block, which tells the device how to
            interpret our FAT filesystem.
        """

        response  = b'\xEB\x00\x90'     # jump to bootloader (oddly, checked on some non-x86 uCs)
        response += b'MSWIN4.1'         # OEM name (this one seems broadly compatible)

        # Bytes per disk sector.
        response += self.get_sector_size().to_bytes(2, byteorder='little')

        # Sectors per cluster.
        response += self._sectors_per_cluster().to_bytes(1, byteorder='little')

        response += b'\x20\x00'          # reserved sectors
        response += b'\x02'              # number of FATs (must be 2)
        response += b'\x00\x00'          # root entries (must be 0 for fat32)
        response += b'\x00\x00'          # total 16-bit count of sectors (must be 0 for fat32)
        response += b'\xF8'              # media type: hard drive (0xF8)
        response += b'\x00\x00'          # sectors per FAT (must be 0 for fat32)
        response += b'\x00\x00'          # sectors per track (most likely ignored)
        response += b'\x00\x00'          # number of heads (most likely ignored)
        response += b'\x00\x00\x00\x00'  # hidden sectors (most likely ignored)

        # The total number of sectors in the volume.
        response += self.get_partition_sectors().to_bytes(4, byteorder='little')

        response += b'\xC1\x0F\x00\x00'  # sectors per FAT
        response += b'\x00\x00'          # flags
        response += b'\x00\x00'          # filesystem revision
        response += b'\x02\x00\x00\x00'  # cluster for the root directory
        response += b'\x01\x00'          # address of the fsinfo sector
        response += b'\x06\x00'          # address of the backup of the boot sector
        response += 12 * b'\x00'         # reserved space
        response += b'\x80'              # drive number for PC-BIOS (0x80 = hard disk)
        response += b'\x00'              # reserved space
        response += b'\x29'              # boot signature (from mkfs.vfat)
        response += b'0000'              # disk serial number (for volume tracking)
        response += b'Facedancer '       # volume label (must be 11 bytes; spaces for padding)
        response += b'FAT32   '          # should be "FAT32" for FAT32, padded to eight bytes
        response += 420 * b'\x00'        # reserved space
        response += b'\x55\xAA'          # end of sector marker

        return response


    def handle_fsinfo_read(self, address):
        """
            Returns a valid filesystem info block, which is used to cache information
            about free sectors on the filesystem. We don't actually sport writing,
            so we return a valid-but-useless block.
        """

        response  = b'\x52\x52\x61\x41'  # fsinfo block signature (magic number)
        response += 480 * b'\x00'        # reserved for future use
        response += b'\x72\x72\x41\x61'  # second signature (magic number)
        response += b'\xFF\xFF\xFF\xFF'  # free sector count (-1 = "don't know")
        response += b'\xFF\xFF\xFF\xFF'  # next free sector (-1 = "don't know")
        response += 12 * b'\x00'         # reserved for future use
        response += b'\x00\x00\x55\xAA'  # final signature (magic number)

        return response

    def _generate_directory_entry(self, filename, file_size, cluster_number, flags=b'\x00'):

        # TODO: automatically convert filename, filesize to bytes
        # TODO: support long form name entries?


        cluster_number_bytes = cluster_number.to_bytes(4, byteorder='little')
        cluster_number_low   = cluster_number_bytes[:2]
        cluster_number_high  = cluster_number_bytes[2:]

        entry  = filename             # short name (first 8 are name; last three are extension)
        entry += flags                # file attributes
        entry += b'\x00'              # reserved byte
        entry += 5 * b'\x00'          # dir creation date/time
        entry += 2 * b'\x00'          # last access date
        entry += cluster_number_high  # high word of the entry's first cluster number
        entry += 4 * b'\x00'          # last write date/time
        entry += cluster_number_low   # low word of the entry's first cluster number
        entry += file_size.to_bytes(4, byteorder='little')
        return entry


    def _short_filename_checksum(self, short_filename):
        """
        Generates a long-form name checksum for a given 8.3 short filename.
        """
        sum = 0

        for byte in short_filename:

            # I'm sorry. This is copied directly from the bloody spec.
            # Don't judge me. Judge them.
            sum = (((sum & 1) << 7) | ((sum & 0xfe) >> 1)) + byte

        return sum & 0xFF


    def _is_valid_83_char(self, c):
        """
        Returns true iff the given character is a valid 8-3 filename character.
        """

        if c in " !#$%&'()-@^_`{}~'":
            return True
        if c.isupper() or c.isdigit():
            return True

        return False


    def _is_valid_83_name(self, long_filename):
        """
        Returns true iff the given filename is a valid filename.
        """
        if len(long_filename) != 11:
            return False

        return all([self._is_valid_83_char(c) for c in long_filename])


    def _short_filename_from_long(self, long_filename):
        """
        Generates short-form filenames from a long-form name.
        """

        # TODO: Generalize this to behave like Windows
        if self._is_valid_83_name(long_filename):
            return long_filename.encode('utf-8')
        else:
            # FIXME: This breaks in lots of cases; it's just Good Enough (TM)
            # for now.
            prefix = re.sub(r'\W+', '', long_filename)[:6]
            extension = long_filename[-3:]

            short_name = '{}~1{}'.format(prefix, extension)
            return short_name.encode('utf-8')


    def _generate_long_directory_entries(self, long_filename, short_filename):
        """
        Generate long-form directory entries for a long filename.
        Should be called immediately before calling the short_form directory
        entry functions.
        """
        index = 1
        entries = []

        # Null terminate our long filename, as the filesystem expects.
        long_filename += "\0"

        while long_filename:
            entry_file      = long_filename[:13]
            long_filename   = long_filename[13:]

            # If this is the final entry, set the sixth bit of the index,
            # indicating that this is the final index present.
            if not long_filename:
                index |= 0x40

            # Compute the checksum for the short filename.
            checksum = self._short_filename_checksum(short_filename)

            # Encode the filename in UTF-8, padded with FFs as necessary.
            entry_file = bytes(entry_file.encode('utf-16'))[2:]
            entry_file = entry_file.ljust(26, b'\xFF')

            # Generate the entry itself.
            entry  = index.to_bytes(1, byteorder='little')    # index of this entry
            entry += entry_file[:10]                          # first five characters
            entry += b'\x0F'                                  # attribute indicating this is a long filename
            entry += b'\x00'                                  # always zeroes for VFAT LFNs
            entry += checksum.to_bytes(1, byteorder='little') # checksum of the short name
            entry += entry_file[10:22]                        # next six characters of the filename
            entry += b'\x00\x00'                              # always zeroes
            entry += entry_file[22:]                          # the final two characters of the filename

            # Move to the next entry...
            index += 1
            entries.append(entry)

        # Reverse the order of the entries, and convert them to a byte string.
        return b''.join(entries[::-1])


    def handle_root_dir_read(self, address):
        """
            Returns a valid entry describing the root directory of our FAT filesystem.
        """

        # Generate the volume label entry.
        response = self._generate_directory_entry(b'Facedancer ', 0, 0, flags=b'\x08')

        return response


    def _generate_fat_partition_entry(self):
        """
        Returns a partition entry pointing to our synthetic FAT partition.
        """

        response  = b'\x00'           # Status: 0x00 = not bootable, 0x80 = bootable
        response += b'\x00\x00\x00'   # CHS address of the partition's first sector; typically ignored
        response += b'\x0B'           # disk type: FAT32 with CHS/LBA addressing
        response += b'\x00\x00\x00'   # CHS address of the partition's end; typically ignored

        # LBA of our first sector.
        response += self.BPB_SECTOR.to_bytes(4, byteorder='little')

        # Report the size of the partition, in sectors. We'll use up all "unallocated"
        # space on the drive with our FAT partition.
        response += self.get_partition_sectors().to_bytes(4, byteorder='little')

        return response

    def _sectors_per_cluster(self):
        """
        Returns the number of sectors in a cluster.
        """
        return int(self.CLUSTER_SIZE / self.get_sector_size())



    def handle_fat_read(self, address):
        """
        Handles an access to the device's file allocaiton table.
        """

        # TODO: Create general method for reading from the FAT based on
        # virtual files, and methods to add those files!
        raise NotImplementedError()




    def handle_unhandled_sector(self, address):
        """
        Handles unsupported sector reads.
        """

        if self.verbose > 3:
            print("<-- !!! unhandled sector {}, returning all zeroes".format(address))

        return bytes(bytearray(self.get_sector_size()))


    def get_sector_count(self):
        """
        Returns the total number of sectors present on the disk.
        """
        return int(self.size / self.get_sector_size()) - 1


    def get_partition_sectors(self):
        """
        Get the amount of sectors available for use by our main FAT partition.
        """

        # Return everything but the MBR and reserved space.
        return (self.get_sector_count() - 4096)


    def _find_sector_handler(self, address):
        """
        Locates the function that should handle generation of the given sector.
        """

        # Check each of our sector handlers to see if it is appropriate to handle
        # the given sector...
        for handler in self.sector_handlers:
            sector_or_lambda = handler['sector_or_lambda']

            if(callable(sector_or_lambda)):
                matches = sector_or_lambda(address)
            else:
                matches = (sector_or_lambda == address)

            if matches:
                return handler

        return None


    def get_sector_data(self, address):
        """
        Fetches the data at the given sector of our emulated disk.
        """

        handler = self._find_sector_handler(address)

        # If we have a handler for this sector, handle it.
        if handler:
            name     = handler['name']
            function = handler['handler']

            if self.verbose > 0:
                print("<-- handling read of {} sector ({})".format(name, address))

            # Call the main handler.
            response = function(address)

            # If our response is smaller than our sector size, pad it out with zeroes.
            if len(response) < self.get_sector_size():
                needed_bytes = self.get_sector_size() - len(response)
                response += needed_bytes * b'\x00'

            if self.verbose > 4:
                print("    response: {} ({})".format(len(response), response))

            return response

        # Otherwise, run the unknown command handler.
        else:
            return self.handle_unhandled_sector(address)

