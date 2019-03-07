# Copyright (C) 2016 Cisco Systems, Inc. and/or its affiliates. All rights reserved.
#
# This file is part of Kitty.
#
# Kitty is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Kitty is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Kitty.  If not, see <http://www.gnu.org/licenses/>.

'''
Fields to perform mutation fuzzing

In some cases, you might not know the details and structure of the fuzzed protocol
(or might just be too lazy) but you do have some examples of valid messages.
In these cases, it makes sense to perform mutation fuzzing.
The strategy of mutation fuzzing is to take some valid messages and mutate them in various ways.
Kitty supports the following strategies described below.
The last one, `MutableField`, combines all strategies, with reasonable parameters, together.

Currently all strategies are inspired by this article:
http://lcamtuf.blogspot.com/2014/08/binary-fuzzing-strategies-what-works.html
'''
import sys
from bitstring import Bits, BitArray
from kitty.model.low_level.field import BaseField
from kitty.model.low_level.container import OneOf
from kitty.model.low_level.encoder import ENC_BITS_DEFAULT, ENC_BITS_BYTE_ALIGNED, BitsEncoder
from kitty.model.low_level.encoder import ENC_STR_DEFAULT, StrEncoder
from kitty.model.low_level.encoder import strToBytes
from kitty.core import kassert, KittyException, khash


class BitFlip(BaseField):
    '''
    Perform bit-flip mutations of N sequential bits on the value

    :example:

        ::

            BitFlip('\\x01', 3)
            Results in: '\\xe1', '\\x71', '\\x39', '\\x1d', '\\x0f', '\\x06'
    '''
    _encoder_type_ = BitsEncoder

    def __init__(self, value, num_bits=1, fuzzable=True, name=None):
        '''
        :param value: value to mutate (str or bytes)
        :param num_bits: number of consequtive bits to flip (invert)
        :param fuzzable: is field fuzzable (default: True)
        :param name: name of the object (default: None)

        :raises: ``KittyException`` if num_bits is bigger than the value length in bits
        :raises: ``KittyException`` if num_bits is not positive
        '''
        kassert.is_of_types(value, (bytes, bytearray, str))
        value = strToBytes(value)
        if len(value) * 8 < num_bits:
            raise KittyException('len of value in bits(%d) < num_bits(%d)' % (len(value) * 8, num_bits))
        if num_bits <= 0:
            raise KittyException('num_bits(%d) <= 0' % (num_bits))
        super(BitFlip, self).__init__(value=Bits(bytes=value), encoder=ENC_BITS_DEFAULT, fuzzable=fuzzable, name=name)
        self._data_len = len(value) * 8
        self._num_bits = num_bits
        self._num_mutations = self._data_len - (num_bits - 1)

    def _start_end(self):
        start_idx = self._current_index
        end_idx = start_idx + self._num_bits
        return start_idx, end_idx

    def _mutate(self):
        new_val = BitArray(self._default_value).copy()
        start, end = self._start_end()
        new_val.invert(range(start, end))
        self.set_current_value(Bits(new_val))

    def get_info(self):
        info = super(BitFlip, self).get_info()
        info['strategy'] = 'bit flip'
        info['bits to flip'] = self._num_bits
        start, end = self._start_end()
        info['start bit'] = start
        info['end bit'] = end
        return info

    def hash(self):
        hashed = super(BitFlip, self).hash()
        return khash(hashed, self._num_bits)


class ByteFlip(BaseField):
    '''
    Flip number of sequential bytes in the message, each mutation moving one byte forward.

    :example:

        ::

            ByteFlip('\\x00\\x00\\x00\\x00', 2)
            # results in:
            '\\xff\\xff\\x00\\x00'
            '\\x00\\xff\\xff\\x00'
            '\\x00\\x00\\xff\\xff'
    '''
    _encoder_type_ = StrEncoder

    def __init__(self, value, num_bytes=1, fuzzable=True, name=None):
        '''
        :type value: str or bytes
        :param value: value to mutate
        :param num_bytes: number of consequtive bytes to flip (invert)
        :param fuzzable: is field fuzzable (default: True)
        :param name: name of the object (default: None)

        :raises: ``KittyException`` if num_bytes is bigger than the value length
        :raises: ``KittyException`` if num_bytes is not positive
        '''
        kassert.is_of_types(value, (bytes, bytearray, str))
        value = strToBytes(value)
        if len(value) < num_bytes:
            raise KittyException('len(value) <= num_bytes', (len(value), num_bytes))
        if num_bytes <= 0:
            raise KittyException('num_bytes(%d) <= 0' % (num_bytes))
        super(ByteFlip, self).__init__(value=value, encoder=ENC_STR_DEFAULT, fuzzable=fuzzable, name=name)
        self._data_len = len(value)
        self._num_bytes = num_bytes
        self._num_mutations = self._data_len - (num_bytes - 1)

    def _start_end(self):
        start_idx = self._current_index
        end_idx = start_idx + self._num_bytes
        return start_idx, end_idx

    def _mutate(self):
        start, end = self._start_end()
        pre = self._default_value[:start]
        current = self._default_value[start:end]
        if sys.version_info >= (3,):
            mutated = ''.join(chr(c ^ 0xff) for c in current)
        else:
            mutated = ''.join(chr(ord(c) ^ 0xff) for c in current)
        post = self._default_value[end:]
        self.set_current_value(pre + strToBytes(mutated) + post)

    def get_info(self):
        info = super(ByteFlip, self).get_info()
        info['strategy'] = 'byte flip'
        info['bytes to flip'] = self._num_bytes
        start, end = self._start_end()
        info['start byte'] = start
        info['end bit'] = end
        return info

    def hash(self):
        hashed = super(ByteFlip, self).hash()
        return khash(hashed, self._num_bytes)


class BlockOperation(BaseField):
    '''
    Base class for performing block-level mutations
    '''

    _encoder_type_ = StrEncoder

    def __init__(self, value, block_size, fuzzable=True, name=None):
        '''
        :type value: str
        :param value: value to mutate
        :param block_size: number of consequtive bytes to operate on
        :param fuzzable: is field fuzzable (default: True)
        :param name: name of the object (default: None)

        :raises: ``KittyException`` if block_size is bigger than the value length in bytes
        :raises: ``KittyException`` if block_size is not positive
        '''
        if block_size > len(value):
            raise KittyException('block_size (%d) > length of value (%d)' % (block_size, len(value)))
        if block_size <= 0:
            raise KittyException('block_size (%d) <= 0' % (block_size))
        super(BlockOperation, self).__init__(value=value, encoder=ENC_STR_DEFAULT, fuzzable=fuzzable, name=name)
        self._block_size = block_size
        self._num_mutations = len(value) - (self._block_size - 1)

    def _split(self):
        pre = self._default_value[:self._current_index]
        current = self._default_value[self._current_index:self._current_index + self._block_size]
        post = self._default_value[self._current_index + self._block_size:]
        return pre, current, post

    def hash(self):
        hashed = super(BlockOperation, self).hash()
        return khash(hashed, self._block_size)


class BlockRemove(BlockOperation):
    '''
    Remove a block of bytes from the default value, each mutation moving one byte forward.
    '''

    def __init__(self, value, block_size, fuzzable=True, name=None):
        '''
        :type value: str
        :param value: value to mutate
        :param block_size: number of consequtive bytes to remove
        :param fuzzable: is field fuzzable (default: True)
        :param name: name of the object (default: None)

        :raises: ``KittyException`` if block_size is bigger than the value length in bytes
        :raises: ``KittyException`` if block_size is not positive
        '''
        super(BlockRemove, self).__init__(value, block_size, fuzzable, name)

    def _mutate(self):
        pre, _, post = self._split()
        self.set_current_value(pre + post)


class BlockDuplicate(BlockOperation):
    '''
    Duplicate a block of bytes from the default value, each mutation moving one byte forward.
    '''

    def __init__(self, value, block_size, num_dups=2, fuzzable=True, name=None):
        '''
        :type value: str
        :param value: value to mutate
        :param block_size: number of consequtive bytes to duplicate
        :param num_dups: number of times to duplicate the block (default: 1)
        :param fuzzable: is field fuzzable (default: True)
        :param name: name of the object (default: None)

        :raises: ``KittyException`` if block_size is bigger than the value length in bytes
        :raises: ``KittyException`` if block_size is not positive
        '''
        if num_dups <= 0:
            raise KittyException('num_dups(%d) <= 0' % (num_dups))
        super(BlockDuplicate, self).__init__(value, block_size, fuzzable, name)
        self._num_dups = num_dups

    def _mutate(self):
        pre, current, post = self._split()
        self.set_current_value(pre + (current * self._num_dups) + post)

    def hash(self):
        hashed = super(BlockDuplicate, self).hash()
        return khash(hashed, self._num_dups)


class BlockSet(BlockOperation):
    '''
    Set a block of bytes from the default value to a specific value, each mutation moving one byte forward.
    '''

    def __init__(self, value, block_size, set_chr, fuzzable=True, name=None):
        '''
        :type value: str
        :param value: value to mutate
        :param block_size: number of consequtive bytes to duplicate
        :param set_chr: char to set in the blocks
        :param fuzzable: is field fuzzable (default: True)
        :param name: name of the object (default: None)

        :raises: ``KittyException`` if block_size is bigger than the value length in bytes
        :raises: ``KittyException`` if block_size is not positive
        '''
        super(BlockSet, self).__init__(value, block_size, fuzzable, name)
        self._set_chr = set_chr

    def _mutate(self):
        pre, _, post = self._split()
        self.set_current_value(pre + (self._set_chr * self._block_size) + post)


class BitFlips(OneOf):
    '''
    Perform bit-flip mutations of (N..) sequential bits on the value
    '''

    def __init__(self, value, bits_range=range(1, 5), fuzzable=True, name=None):
        '''
        :type value: str or bytes
        :param value: value to mutate
        :param bits_range: range of number of consequtive bits to flip (default: range(1, 5))
        :param fuzzable: is field fuzzable (default: True)
        :param name: name of the object (default: None)

        :example:

            ::

                BitFlips('\\x00', (3, 5))
                Results in: '\\xe0', '\\x70', '\\x38', '\\x1c', '\\x0e', '\\x07' - 3 bits flipped each time
                            '\\xf8', '\\x7c', '\\x3e', '\\x1f' - 5 bits flipped each time
        '''
        field_name = name + '_%d' if name else 'bitflip_%d'

        fields = [BitFlip(value, i, fuzzable, field_name % i) for i in bits_range]
        super(BitFlips, self).__init__(fields=fields, fuzzable=fuzzable, name=name)


class ByteFlips(OneOf):
    '''
    Perform byte-flip mutations of (N..) sequential bytes on the value
    '''

    def __init__(self, value, bytes_range=(1, 2, 4), fuzzable=True, name=None):
        '''
        :type value: str
        :param value: value to mutate
        :param bytes_range: range of number of consequtive bytes to flip (default: (1, 2, 4))
        :param fuzzable: is field fuzzable (default: True)
        :param name: name of the object (default: None)

        :example:

            ::

                ByteFlips('\\x00\\x00\\x00\\x00', (2,3))
                Results in:
                '\\xff\\xff\\x00\\x00', '\\x00\\xff\\xff\\x00', '\\x00\\x00\\xff\\xff'  # 2 bytes flipped each time
                '\\xff\\xff\\xff\\x00', '\\x00\\xff\\xff\\xff'  # 3 bytes flipped each time
        '''
        field_name = (name + '_%d') if name else 'byteflip_%d'

        fields = [ByteFlip(value, i, fuzzable, field_name % i) for i in bytes_range]
        super(ByteFlips, self).__init__(fields=fields, fuzzable=fuzzable, name=name)


class BlockDuplicates(OneOf):
    '''
    Perform block duplication with multiple number of duplications
    '''

    def __init__(self, value, block_size, num_dups_range=(2, 5, 10, 50, 200), fuzzable=True, name=None):
        field_name = (name + '_%d') if name else 'block_duplicates_%d'
        fields = [BlockDuplicate(value, block_size, i, fuzzable, field_name % i) for i in num_dups_range]
        super(BlockDuplicates, self).__init__(fields=fields, fuzzable=fuzzable, name=name)


class MutableField(OneOf):
    '''
    Container to perform mutation fuzzing on a value
    ByteFlips, BitFlips and block operations
    '''

    def __init__(self, value, encoder=ENC_BITS_BYTE_ALIGNED, fuzzable=True, name=None):
        '''
        :type value: str
        :param value: value to mutate
        :type encoder: BitsEncoder
        :param encoder: encoder for the container (default: ENC_BITS_BYTE_ALIGNED)
        :param fuzzable: is fuzzable (default: True)
        :param name: (unique) name of the template (default: None)
        '''
        fields = []
        max_len_bytes = len(value)
        fields.append(ByteFlips(value, bytes_range=[x for x in [1, 2, 4] if x <= max_len_bytes], fuzzable=fuzzable, name='byteflips'))
        fields.append(BitFlips(value, fuzzable=fuzzable, name='bitflips'))
        if max_len_bytes > 4:
            size = 4
            fields.append(BlockRemove(value, block_size=size, fuzzable=fuzzable, name='remove_%d' % size))
            fields.append(BlockDuplicate(value, block_size=size, fuzzable=fuzzable, name='duplicate_%d' % size))
            fields.append(BlockSet(value, block_size=size, set_chr='\x00', fuzzable=fuzzable, name='set_%d' % size))
        if max_len_bytes > 8:
            size = 8
            fields.append(BlockRemove(value, block_size=size, fuzzable=fuzzable, name='remove_%d' % size))
            fields.append(BlockDuplicates(value, block_size=size, fuzzable=fuzzable, name='duplicate_%d' % size))
            fields.append(BlockSet(value, block_size=size, set_chr='\x00', fuzzable=fuzzable, name='set_%d' % size))
        if max_len_bytes > 16:
            size = 16
            fields.append(BlockRemove(value, block_size=size, fuzzable=fuzzable, name='remove_%d' % size))
            fields.append(BlockDuplicates(value, block_size=size, fuzzable=fuzzable, name='duplicate_%d' % size))
            fields.append(BlockSet(value, block_size=size, set_chr='\x00', fuzzable=fuzzable, name='set_%d' % size))
        super(MutableField, self).__init__(fields=fields, encoder=encoder, fuzzable=fuzzable, name=name)
