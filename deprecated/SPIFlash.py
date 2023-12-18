"""
SPIFlash.py

Contains code needed to emulate SPI flash memory.

Copyright (c) 2018, wchill
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the organization nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""


class SPIFlash(object):

    def __init__(self, size=0x80000, filename=None, data=None):
        if filename is not None:
            with open(filename, 'rb') as f:
                self._mem = list(f.read())
        elif data is not None:
            self._mem = list(data)
        else:
            self._mem = [0xff] * size

    def __repr__(self):
        return 'SPIFlash(data={})'.format(bytes(self._mem))

    def __str__(self):
        return 'SPI flash memory ({} bytes)'.format(len(self._mem))

    def __len__(self):
        return len(self._mem)

    def __setitem__(self, key, value):
        if not isinstance(key, int):
            raise KeyError('Key must be an integer')
        if isinstance(value, int):
            self.write(key, [value])
        elif isinstance(value, bytes):
            self.write(key, list(value))
        elif isinstance(value, list):
            self.write(key, value)
        else:
            raise ValueError('Value must be an int, bytes or list')

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.read(key, 1)
        elif isinstance(key, slice):
            return self._mem[key]
        raise KeyError('Key must be an int or slice')

    def __iter__(self):
        return iter(self._mem)

    def load(self, filename):
        with open(filename, 'rb') as f:
            self.write(0, list(f.read()))

    def save(self, filename):
        with open(filename, 'wb') as f:
            f.write(self.read(0, len(self._mem)))

    def read(self, address, length):
        if address < 0 or address >= len(self._mem):
            raise ValueError(
                'Invalid address {:04x} - valid range is 0 to {:04x}'
                .format(address, len(self._mem) - 1))
        end_addr = address + length
        if end_addr <= 0 or end_addr > len(self._mem):
            raise ValueError(
                'Invalid end address {:04x} - valid range is 1 to {:04x}'
                .format(end_addr, len(self._mem)))
        return bytes(self._mem[address:end_addr])

    def write(self, address, data):
        if address < 0 or address >= len(self._mem):
            raise ValueError(
                'Invalid address {:04x} - valid range is 0 to {:04x}'
                .format(address, len(self._mem) - 1))
        end_addr = address + len(data)
        if end_addr <= 0 or end_addr > len(self._mem):
            raise ValueError(
                'Invalid end address {:04x} - valid range is 1 to {:04x}'
                .format(end_addr, len(self._mem)))
        self._mem = self._mem[:address] + data + self._mem[end_addr:]

    def erase(self, address):
        if address & 4095:
            raise ValueError(
                'Invalid erase address {:04x} - value must be 4kb aligned'
                .format(address))
        for i in range(address, address+4096):
            self._mem[i] = 0xff
