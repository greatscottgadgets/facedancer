import os
from mmap import mmap

class RawDiskImage():
    """
        Raw disk image backed by a file.
    """

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

        self.verbose("<-- reading sector %d" % (address))

        block_start = address * self.block_size
        block_end   = (address + 1) * self.block_size   # slices are NON-inclusive
        data = self.image[block_start:block_end]

        if not any(data):
                self.debug("<-- reading sector %d [all zeroes]" % (address))
        else:
                self.debug("<-- reading sector {} [{}]".format(address, data))

        return data

    def put_data(self, address, data):
        blocks = int(len(data) / self.block_size)
        self.verbose("--> writing %d blocks at lba %d" % (blocks, address))

        super().put_data(address, data)


    def put_sector_data(self, address, data):

        self.debug("--> writing sector {}".format(address))

        if len(data) > self.block_size:
            self.warning("WARNING: got %d bytes of sector data; expected a max of %d" % (len(data), self.block_size))

        block_start = address * self.block_size
        block_end   = (address + 1) * self.block_size   # slices are NON-inclusive

        if not any(data):
            self.debug("--> writing sector %d [all zeroes]" % (address))
        else:
            self.debug("--> writing sector {} [{}]".format(address, data))

        self.image[block_start:block_end] = data[:self.block_size]
        self.image.flush() 