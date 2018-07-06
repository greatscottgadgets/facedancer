import sys
from serial import Serial, PARITY_NONE

class RawDiskImage():
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