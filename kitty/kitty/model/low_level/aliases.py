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
Functions that provide simpler field creation API and name aliasing for convenience

:Integer Aliases:

    Since integers the are binary encoded are used in many places, there are many aliases for them.
    Some are similar to common type conventions, others are simply meant to make the template code smaller.
    Below is a (hopefully) full list of aliases.
    However, the safest place to check, as always, is the source.

    +-------+--------+--------------------------+---------------------------+
    | Bytes | Signed | Endianess                | Aliases                   |
    +=======+========+==========================+===========================+
    | 1     | No     |                          | U8, UInt8, BE8, LE8, Byte |
    +-------+--------+--------------------------+---------------------------+
    | 2     | No     | big, but can be changed  | U16, UInt16, Word         |
    +-------+        +--------------------------+---------------------------+
    | 2     |        | big                      | BE16, WordBE              |
    +-------+        +--------------------------+---------------------------+
    | 2     |        | little                   | LE16, WordLE              |
    +-------+--------+--------------------------+---------------------------+
    | 2     | Yes    | big, but can be changed  | S16, SInt16               |
    +-------+--------+--------------------------+---------------------------+
    | 4     | No     | big, but can be changed  | U32, UInt32, Dword        |
    +-------+        +--------------------------+---------------------------+
    | 4     |        | big                      | BE32, DwordBE             |
    +-------+        +--------------------------+---------------------------+
    | 4     |        | little                   | LE32, DwordLE             |
    +-------+--------+--------------------------+---------------------------+
    | 4     | Yes    | big, but can be changed  | S32, SInt32               |
    +-------+--------+--------------------------+---------------------------+
    | 8     | No     | big, but can be changed  | U64, UInt64, Qword        |
    +-------+        +--------------------------+---------------------------+
    | 8     |        | big                      | BE64, QwordBE             |
    +-------+        +--------------------------+---------------------------+
    | 8     |        | little                   | LE64, QwordLE             |
    +-------+--------+--------------------------+---------------------------+
    | 8     | Yes    | big, but can be changed  | S64, SInt64               |
    +-------+--------+--------------------------+---------------------------+

:Hash Aliases:

    There are multiple functions that return frequently used Hash instances:

    - *Md5*
    - *Sha1*
    - *Sha224*
    - *Sha256*
    - *Sha384*
    - *Sha512*.

    Their prototype is the same as *Hash*, excluding the *algorithm* argument.

:Compare Aliases:

    The *Compare* aliases create a Compare object with a specific comp_type.
    See table below:

    +-----------+-----------------------+
    | comp_type | Aliases               |
    +===========+=======================+
    | '=='      | Equal                 |
    +-----------+-----------------------+
    | '!='      | NotEqual              |
    +-----------+-----------------------+
    | '>'       | Greater               |
    +-----------+-----------------------+
    | '>='      | GreaterEqual, AtLeast |
    +-----------+-----------------------+
    | '<'       | Lesser                |
    +-----------+-----------------------+
    | '<='      | LesserEqual, AtMost   |
    +-----------+-----------------------+
    | '&'       | BitMaskSet            |
    +-----------+-----------------------+
    | '&=0'     | BitMaskNotSet         |
    +-----------+-----------------------+
'''
from kitty.model.low_level.field import BitField
from kitty.model.low_level.calculated import Size, Hash
from kitty.model.low_level.encoder import ENC_INT_DEFAULT, ENC_INT_BE, ENC_INT_LE, ENC_STR_DEFAULT
from kitty.model.low_level.condition import Compare


# ################### Field Aliases ####################

def UInt8(value, min_value=None, max_value=None, encoder=ENC_INT_DEFAULT, fuzzable=True, name=None, full_range=False):
    '''Unsigned 8-bit field'''
    return BitField(value, 8, signed=False, min_value=min_value, max_value=max_value, encoder=encoder, fuzzable=fuzzable, name=name, full_range=full_range)


def UInt16(value, min_value=None, max_value=None, encoder=ENC_INT_DEFAULT, fuzzable=True, name=None, full_range=False):
    '''Unsigned 16-bit field'''
    return BitField(value, 16, signed=False, min_value=min_value, max_value=max_value, encoder=encoder, fuzzable=fuzzable, name=name, full_range=full_range)


def UInt32(value, min_value=None, max_value=None, encoder=ENC_INT_DEFAULT, fuzzable=True, name=None, full_range=False):
    '''Unsigned 32-bit field'''
    return BitField(value, 32, signed=False, min_value=min_value, max_value=max_value, encoder=encoder, fuzzable=fuzzable, name=name, full_range=full_range)


def UInt64(value, min_value=None, max_value=None, encoder=ENC_INT_DEFAULT, fuzzable=True, name=None, full_range=False):
    '''Unsigned 64-bit field'''
    return BitField(value, 64, signed=False, min_value=min_value, max_value=max_value, encoder=encoder, fuzzable=fuzzable, name=name, full_range=full_range)


def SInt8(value, min_value=None, max_value=None, encoder=ENC_INT_DEFAULT, fuzzable=True, name=None, full_range=False):
    '''Signed 8-bit field'''
    return BitField(value, 8, signed=True, min_value=min_value, max_value=max_value, encoder=encoder, fuzzable=fuzzable, name=name, full_range=full_range)


def SInt16(value, min_value=None, max_value=None, encoder=ENC_INT_DEFAULT, fuzzable=True, name=None, full_range=False):
    '''Signed 16-bit field'''
    return BitField(value, 16, signed=True, min_value=min_value, max_value=max_value, encoder=encoder, fuzzable=fuzzable, name=name, full_range=full_range)


def SInt32(value, min_value=None, max_value=None, encoder=ENC_INT_DEFAULT, fuzzable=True, name=None, full_range=False):
    '''Signed 32-bit field'''
    return BitField(value, 32, signed=True, min_value=min_value, max_value=max_value, encoder=encoder, fuzzable=fuzzable, name=name, full_range=full_range)


def SInt64(value, min_value=None, max_value=None, encoder=ENC_INT_DEFAULT, fuzzable=True, name=None, full_range=False):
    '''Signed 64-bit field'''
    return BitField(value, 64, signed=True, min_value=min_value, max_value=max_value, encoder=encoder, fuzzable=fuzzable, name=name, full_range=full_range)


def BE8(value, min_value=None, max_value=None, fuzzable=True, name=None, full_range=False):
    '''8-bit field, Big endian encoded'''
    return UInt8(value, min_value=min_value, max_value=max_value, encoder=ENC_INT_BE, fuzzable=fuzzable, name=name, full_range=full_range)


def BE16(value, min_value=None, max_value=None, fuzzable=True, name=None, full_range=False):
    '''16-bit field, Big endian encoded'''
    return UInt16(value, min_value=min_value, max_value=max_value, encoder=ENC_INT_BE, fuzzable=fuzzable, name=name, full_range=full_range)


def BE32(value, min_value=None, max_value=None, fuzzable=True, name=None, full_range=False):
    '''32-bit field, Big endian encoded'''
    return UInt32(value, min_value=min_value, max_value=max_value, encoder=ENC_INT_BE, fuzzable=fuzzable, name=name, full_range=full_range)


def BE64(value, min_value=None, max_value=None, fuzzable=True, name=None, full_range=False):
    '''64-bit field, Big endian encoded'''
    return UInt64(value, min_value=min_value, max_value=max_value, encoder=ENC_INT_BE, fuzzable=fuzzable, name=name, full_range=full_range)


def LE8(value, min_value=None, max_value=None, fuzzable=True, name=None, full_range=False):
    '''8-bit field, Little endian encoded'''
    return UInt8(value, min_value=min_value, max_value=max_value, encoder=ENC_INT_LE, fuzzable=fuzzable, name=name, full_range=full_range)


def LE16(value, min_value=None, max_value=None, fuzzable=True, name=None, full_range=False):
    '''16-bit field, Little endian encoded'''
    return UInt16(value, min_value=min_value, max_value=max_value, encoder=ENC_INT_LE, fuzzable=fuzzable, name=name, full_range=full_range)


def LE32(value, min_value=None, max_value=None, fuzzable=True, name=None, full_range=False):
    '''32-bit field, Little endian encoded'''
    return UInt32(value, min_value=min_value, max_value=max_value, encoder=ENC_INT_LE, fuzzable=fuzzable, name=name, full_range=full_range)


def LE64(value, min_value=None, max_value=None, fuzzable=True, name=None, full_range=False):
    '''64-bit field, Little endian encoded'''
    return UInt64(value, min_value=min_value, max_value=max_value, encoder=ENC_INT_LE, fuzzable=fuzzable, name=name, full_range=full_range)


U8 = UInt8
S8 = SInt8
Byte = UInt8
U16 = UInt16
S16 = SInt16
Word = UInt16
WordBE = BE16
WordLE = LE16
U32 = UInt32
S32 = SInt32
Dword = UInt32
DwordBE = BE32
DwordLE = LE32
U64 = UInt64
S64 = SInt64
Qword = UInt64
QwordBE = BE64
QwordLE = LE64


# ################### Calculated Field Aliases ####################

def SizeInBytes(sized_field, length, encoder=ENC_INT_DEFAULT, fuzzable=False, name=None):
    '''
    :rtype: :class:`~kitty.model.low_level.calculated.Size`
    :return: Size field, which holds the size in bytes of the sized field
    '''
    return Size(sized_field=sized_field, length=length, calc_func=lambda x: len(x) // 8, encoder=encoder, fuzzable=fuzzable, name=name)


def Md5(depends_on, encoder=ENC_STR_DEFAULT, fuzzable=False, name=None):
    '''
    :rtype: :class:`~kitty.model.low_level.calculated.Hash`
    :return: MD5 hash field
    '''
    return Hash(depends_on=depends_on, algorithm='md5', encoder=encoder, fuzzable=fuzzable, name=name)


def Sha1(depends_on, encoder=ENC_STR_DEFAULT, fuzzable=False, name=None):
    '''
    :rtype: :class:`~kitty.model.low_level.calculated.Hash`
    :return: SHA1 hash field
    '''
    return Hash(depends_on=depends_on, algorithm='sha1', encoder=encoder, fuzzable=fuzzable, name=name)


def Sha224(depends_on, encoder=ENC_STR_DEFAULT, fuzzable=False, name=None):
    '''
    :rtype: :class:`~kitty.model.low_level.calculated.Hash`
    :return: SHA224 hash field
    '''
    return Hash(depends_on=depends_on, algorithm='sha224', encoder=encoder, fuzzable=fuzzable, name=name)


def Sha256(depends_on, encoder=ENC_STR_DEFAULT, fuzzable=False, name=None):
    '''
    :rtype: :class:`~kitty.model.low_level.calculated.Hash`
    :return: SHA256 hash field
    '''
    return Hash(depends_on=depends_on, algorithm='sha256', encoder=encoder, fuzzable=fuzzable, name=name)


def Sha384(depends_on, encoder=ENC_STR_DEFAULT, fuzzable=False, name=None):
    '''
    :rtype: :class:`~kitty.model.low_level.calculated.Hash`
    :return: SHA384 hash field
    '''
    return Hash(depends_on=depends_on, algorithm='sha384', encoder=encoder, fuzzable=fuzzable, name=name)


def Sha512(depends_on, encoder=ENC_STR_DEFAULT, fuzzable=False, name=None):
    '''
    :rtype: :class:`~kitty.model.low_level.calculated.Hash`
    :return: SHA512 hash field
    '''
    return Hash(depends_on=depends_on, algorithm='sha512', encoder=encoder, fuzzable=fuzzable, name=name)


# ################### Condition Aliases ####################

def Equal(field, comp_value):
    '''
    Condition applies if the value of the field is equal to the comp_value

    :rtype: :class:`~kitty.model.low_level.condition.Compare`
    '''
    return Compare(field, '==', comp_value)


def NotEqual(field, comp_value):
    '''
    Condition applies if the value of the field is not equal to the comp_value

    :rtype: :class:`~kitty.model.low_level.condition.Compare`
    '''
    return Compare(field, '!=', comp_value)


def Greater(field, comp_value):
    '''
    Condition applies if the value of the field is greater than the comp_value

    :rtype: :class:`~kitty.model.low_level.condition.Compare`
    '''
    return Compare(field, '>', comp_value)


def GreaterEqual(field, comp_value):
    '''
    Condition applies if the value of the field is greater than or equals to the comp_value

    :rtype: :class:`~kitty.model.low_level.condition.Compare`
    '''
    return Compare(field, '>=', comp_value)


def Lesser(field, comp_value):
    '''
    Condition applies if the value of the field is lesser than the comp_value

    :rtype: :class:`~kitty.model.low_level.condition.Compare`
    '''
    return Compare(field, '<', comp_value)


def LesserEqual(field, comp_value):
    '''
    Condition applies if the value of the field is lesser than or equals to the comp_value

    :rtype: :class:`~kitty.model.low_level.condition.Compare`
    '''
    return Compare(field, '<=', comp_value)


def BitMaskSet(field, comp_value):
    '''
    Condition applies if the given bitmask is set in the value of the field

    :rtype: :class:`~kitty.model.low_level.condition.Compare`
    '''
    return Compare(field, '&', comp_value)


def BitMaskNotSet(field, comp_value):
    '''
    Condition applies if the given bitmask is equal to 0 in the value of the field

    :rtype: :class:`~kitty.model.low_level.condition.Compare`
    '''
    return Compare(field, '&=0', comp_value)


AtLeast = GreaterEqual
AtMost = LesserEqual
