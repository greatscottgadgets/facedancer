from mmap import mmap

import os


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
        Handles an access to the device's file allocation table.
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



class RawDiskImage(DiskImage):
    """
        Raw disk image backed by a file.
    """

    def __init__(self, filename, block_size, verbose=0):
        self.filename = filename
        self.block_size = block_size
        self.verbose = verbose

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

        if self.verbose == 2:
            print("<-- reading sector {}".format(address))

        block_start = address * self.block_size
        block_end   = (address + 1) * self.block_size   # slices are NON-inclusive
        data = self.image[block_start:block_end]

        if self.verbose > 3:

            if not any(data):
                print("<-- reading sector {} [all zeroes]".format(address))
            else:
                print("<-- reading sector {} [{}]".format(address, data))

        return data

    def put_data(self, address, data):
        if self.verbose > 1:
            blocks = int(len(data) / self.block_size)
            print("--> writing {} blocks at lba {}".format(blocks, address))

        super().put_data(address, data)


    def put_sector_data(self, address, data):

        if self.verbose == 2:
            print("--> writing sector {}".format(address))

        if len(data) > self.block_size:
            print("WARNING: got {} bytes of sector data; expected a max of {}".format(len(data), self.block_size))

        block_start = address * self.block_size
        block_end   = (address + 1) * self.block_size   # slices are NON-inclusive

        if self.verbose > 3:
            if not any(data):
                print("--> writing sector {} [all zeroes]".format(address))
            else:
                print("--> writing sector {} [{}]".format(address, data))

        self.image[block_start:block_end] = data[:self.block_size]
        self.image.flush()
