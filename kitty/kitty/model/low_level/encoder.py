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
Encoders are used for encoding fields and containers.
The encoders are passed as an argument to the fields/container, during the field rendering,
the encoder's `encode` method is called.

There are four families of encoders:

:Bits Encoders: Used to encode fields/containers that their value is of type *Bits* (Container, ForEach etc.)

:String Encoders: Used to encode fields that their value is of type *str* (String, Delimiter, RandomBytes etc.)

:BitField Encoders:
    Used to encode fields that inherit from BitField or contain BitField (UInt8, Size, Checksum etc.)
    Those encoders are also refferred to as Int Encoders.

:FloatingPoint Encoders:
    Used to encode fields that inherit from FloatingPoint field (Float, Double)
    Those encoders are also refferred to as Float Encoders
'''
import sys
import six
from struct import pack
from binascii import hexlify
from base64 import b64encode
from bitstring import Bits, BitArray
from kitty.core import kassert, KittyException


def strToBytes(value):
    '''
    :type value: ``str``
    :param value: value to encode
    '''
    kassert.is_of_types(value, (bytes, bytearray, six.string_types))
    if isinstance(value, six.string_types):
        return bytes(bytearray([ord(x) for x in value]))
    elif isinstance(value, bytearray):
        return bytes(value)
    return value


def strToUtf8(value):
    '''
    :type value: ``str``
    :param value: value to encode
    '''
    kassert.is_of_types(value, str)
    if sys.version_info < (3,):
        return ''.join([unichr(ord(x)) for x in value])
    return value

# ################### String Encoders ####################


class StrEncoder(object):
    '''
    Base encoder class for str values
    The String encoders *encode* function receives a *str* object as an argument and returns an encoded *Bits* object.

    +----------------------+------------------------------------+---------------------------+
    | Singleton Name       | Encoding                           | Class                     |
    +======================+====================================+===========================+
    | ENC_STR_UTF8         | Encode the str in UTF-8            | StrEncodeEncoder          |
    +----------------------+------------------------------------+                           |
    | ENC_STR_HEX          | Encode the str in hex              |                           |
    +----------------------+------------------------------------+                           |
    | ENC_STR_BASE64       | Encode the str in base64           |                           |
    +----------------------+------------------------------------+---------------------------+
    | ENC_STR_DEFAULT      | Do nothing, just convert the str   | StrEncoder                |
    |                      | to Bits object                     |                           |
    +----------------------+------------------------------------+---------------------------+
    '''

    def encode(self, value):
        '''
        :type value: ``str``
        :param value: value to encode
        '''
        return Bits(bytes=strToBytes(value))


class StrFuncEncoder(StrEncoder):
    '''
    Encode string/byte_string using a given function
    '''

    def __init__(self, func):
        '''
        :param func: encoder function(str)->str
        '''
        super(StrFuncEncoder, self).__init__()
        self._func = func

    def encode(self, value):
        encoded = self._func(strToBytes(value))
        return Bits(bytes=encoded)


_py2_str_encoder_funcs_cache = {}


def py2_str_encoder_func(encoding):
    if encoding not in _py2_str_encoder_funcs_cache:
        _py2_str_encoder_funcs_cache[encoding] = lambda x: x.encode(encoding)
    return _py2_str_encoder_funcs_cache[encoding]


class StrEncodeEncoder(StrFuncEncoder):
    '''
    Encode the string using str.encode function
    '''

    def __init__(self, encoding):
        '''
        :type encoding: ``str``
        :param encoding: encoding to be used, should be a valid argument for str.encode
        '''
        if encoding == 'hex':
            func = hexlify
        elif encoding == 'base64':
            func = b64encode
        elif encoding == 'utf-8':
            func = strToUtf8
        elif encoding == 'bytes':
            func = strToBytes
        elif isinstance(encoding, str):
            if sys.version_info < (3, 0):
                func = py2_str_encoder_func(encoding)
            else:
                raise KittyException('Kitty does not support encoding "%s" on python3' % encoding)
        else:
            func = encoding
        super(StrEncodeEncoder, self).__init__(func)


class StrNullTerminatedEncoder(StrEncoder):
    '''
    Encode the string as c-string, with null at the end
    '''

    def encode(self, value):
        '''
        :param value: value to encode
        '''
        encoded = strToBytes(value) + b'\x00'
        return Bits(bytes=encoded)


ENC_STR_BASE64 = StrEncodeEncoder('base64')
ENC_STR_UTF8 = StrEncodeEncoder('utf-8')
ENC_STR_HEX = StrEncodeEncoder('hex')
ENC_STR_NULL_TERM = StrNullTerminatedEncoder()
ENC_STR_DEFAULT = StrEncoder()


# ################### BitField (int) Encoders ####################

class BitFieldEncoder(object):
    '''
    Base encoder class for BitField values

    +-------------------+---------------------------------------+-----------------------+
    | Singleton Name    | Encoding                              | Class                 |
    +===================+=======================================+=======================+
    | ENC_INT_BIN       | Encode as binary bits                 | BitFieldBinEncoder    |
    +-------------------+---------------------------------------+                       +
    | ENC_INT_LE        | Encode as a little endian binary bits |                       |
    +-------------------+---------------------------------------+                       |
    | ENC_INT_BE        | Encode as a big endian binary bits    |                       |
    +-------------------+---------------------------------------+-----------------------+
    | ENC_INT_DEC       | Encode as a decimal value             | BitFieldAsciiEncoder  |
    +-------------------+---------------------------------------+                       |
    | ENC_INT_HEX       | Encode as a hex value                 |                       |
    +-------------------+---------------------------------------+                       |
    | ENC_INT_HEX_UPPER | Encode as an upper case hex value     |                       |
    +-------------------+---------------------------------------+-----------------------+
    | ENC_INT_DEFAULT   | Same as ENC_INT_BIN                   | BitFieldBinEncoder    |
    +-------------------+---------------------------------------+-----------------------+
    '''

    def encode(self, value, length, signed):
        '''
        :type value: ``int``
        :param value: value to encode
        :type length: ``int``
        :param length: length of value in bits
        :type signed: ``boolean``
        :param signed: is value signed
        '''
        raise NotImplementedError('should be implemented in sub classes')


class BitFieldBinEncoder(BitFieldEncoder):
    '''
    Encode int as binary
    '''

    def __init__(self, mode):
        '''
        :type mode: str
        :param mode: mode of binary encoding. 'le' for little endian, 'be' for big endian, '' for non-byte aligned
        '''
        kassert.is_in(mode, ['', 'be', 'le'])
        super(BitFieldBinEncoder, self).__init__()
        self._mode = mode

    def encode(self, value, length, signed):
        '''
        :param value: value to encode
        :param length: length of value in bits
        :param signed: is value signed
        '''
        if (length % 8 != 0) and self._mode:
            raise Exception('cannot use endianess for non bytes aligned int')
        pre = '' if signed else 'u'
        fmt = '%sint%s:%d=%d' % (pre, self._mode, length, value)
        return Bits(fmt)


class BitFieldAsciiEncoder(BitFieldEncoder):
    '''
    Encode int as ascii
    '''

    formats = ['%d', '%x', '%X', '%#x', '%#X']

    def __init__(self, fmt):
        '''
        :param fmt: format for encoding (from BitFieldAsciiEncoder.formats)
        '''
        kassert.is_in(fmt, BitFieldAsciiEncoder.formats)
        self._fmt = fmt

    def encode(self, value, length, signed):
        return Bits(bytes=strToBytes(self._fmt % value))


class BitFieldMultiByteEncoder(BitFieldEncoder):
    '''
    Encode int as multi-byte (used in WBXML format)
    '''

    def __init__(self, mode='be'):
        '''
        :type mode: str
        :param mode: mode of binary encoding. 'le' for little endian, 'be' for big endian, '' for non-byte aligned
        '''
        kassert.is_in(mode, ['be', 'le'])
        super(BitFieldMultiByteEncoder, self).__init__()
        self._mode = mode

    def encode(self, value, length, signed):
        '''
        :param value: value to encode
        :param length: length of value in bits
        :param signed: is value signed
        '''
        if signed:
            raise KittyException('Signed MultiBytes not supported yet, sorry')

        # split to septets
        if value:
            bytes_arr = []
            while value:
                bytes_arr.append((value & 0x7f) | 0x80)
                value >>= 7
        else:
            bytes_arr = [0]

        # reverse if big endian endian
        if self._mode == 'be':
            bytes_arr.reverse()

        # remove msb from last byte
        bytes_arr[-1] = bytes_arr[-1] & 0x7f

        multi_bytes = ''.join(chr(x) for x in bytes_arr)
        return Bits(bytes=strToBytes(multi_bytes))


ENC_INT_BIN = BitFieldBinEncoder('')
ENC_INT_LE = BitFieldBinEncoder('le')
ENC_INT_BE = BitFieldBinEncoder('be')

ENC_INT_DEC = BitFieldAsciiEncoder('%d')
ENC_INT_HEX = BitFieldAsciiEncoder('%x')
ENC_INT_HEX_UPPER = BitFieldAsciiEncoder('%X')
ENC_INT_DEFAULT = ENC_INT_BIN

ENC_INT_MULTIBYTE_BE = BitFieldMultiByteEncoder('be')

# ################### Bits Encoders ####################


class BitsEncoder(object):
    '''
    Base encoder class for Bits values

    The Bits encoders *encode* function receives a *Bits* object as an argument and returns an encoded *Bits* object.

    +-----------------------+----------------------------------------+------------------------+
    | Singleton Name        | Encoding                               | Class                  |
    +=======================+========================================+========================+
    | ENC_BITS_NONE         | None, returns the same value received  | BitsEncoder            |
    +-----------------------+----------------------------------------+------------------------+
    | ENC_BITS_BYTE_ALIGNED | Appends bits to the received object to | ByteAlignedBitsEncoder |
    |                       | make it byte aligned                   |                        |
    +-----------------------+----------------------------------------+------------------------+
    | ENC_BITS_REVERSE      | Reverse the order of bits              | ReverseBitsEncoder     |
    +-----------------------+----------------------------------------+------------------------+
    | ENC_BITS_BASE64       | Encode a Byte aligned bits in base64   | StrEncoderWrapper      |
    +-----------------------+----------------------------------------+                        |
    | ENC_BITS_UTF8         | Encode a Byte aligned bits in UTF-8    |                        |
    +-----------------------+----------------------------------------+                        |
    | ENC_BITS_HEX          | Encode a Byte aligned bits in hex      |                        |
    +-----------------------+----------------------------------------+------------------------+
    | ENC_BITS_DEFAULT      | Same as ENC_BITS_NONE                  |                        |
    +-----------------------+----------------------------------------+------------------------+
    '''

    def encode(self, value):
        '''
        :type value: Bits
        :param value: value to encode
        '''
        kassert.is_of_types(value, Bits)
        return value


class ByteAlignedBitsEncoder(BitsEncoder):
    '''
    Stuff bits for byte alignment
    '''

    def encode(self, value):
        '''
        :param value: value to encode
        '''
        kassert.is_of_types(value, Bits)
        remainder = len(value) % 8
        if remainder:
            value += Bits(bin='0' * (8 - remainder))
        return value


class ReverseBitsEncoder(BitsEncoder):
    '''
    Reverse the order of bits
    '''

    def encode(self, value):
        '''
        :param value: value to encode
        '''
        kassert.is_of_types(value, Bits)
        result = BitArray(value)
        result.reverse()
        return result


class StrEncoderWrapper(ByteAlignedBitsEncoder):
    '''
    Encode the data using str.encode function
    '''

    def __init__(self, encoder):
        '''
        :type encoding: StrEncoder
        :param encoding: encoder to wrap
        '''
        super(StrEncoderWrapper, self).__init__()
        self._encoder = encoder

    def encode(self, value):
        '''
        :param value: value to encode
        '''
        kassert.is_of_types(value, Bits)
        if len(value) % 8 != 0:
            raise KittyException('this encoder cannot encode bits that are not byte aligned')
        return self._encoder.encode(value.bytes)


class BitsFuncEncoder(BitsEncoder):
    '''
    Encode bits using a given function
    '''

    def __init__(self, func):
        '''
        :param func: encoder function(Bits)->Bits
        '''
        super(BitsFuncEncoder, self).__init__()
        self._func = func

    def encode(self, value):
        kassert.is_of_types(value, Bits)
        encoded = self._func(value)
        return encoded


ENC_BITS_NONE = BitsEncoder()
ENC_BITS_BYTE_ALIGNED = ByteAlignedBitsEncoder()
ENC_BITS_REVERSE = ReverseBitsEncoder()

ENC_BITS_BASE64 = StrEncoderWrapper(StrEncodeEncoder('base64'))
ENC_BITS_UTF8 = StrEncoderWrapper(StrEncodeEncoder('utf-8'))
ENC_BITS_HEX = StrEncoderWrapper(StrEncodeEncoder('hex'))

ENC_BITS_DEFAULT = ENC_BITS_NONE


# ################### BitField (int) Encoders ####################

class FloatEncoder(object):
    '''
    Base encoder class for FloatingPoint values

    +-------------------+---------------------------------------+-----------------------------------------------------------+
    | Singleton Name    | Encoding                              | Class                                                     |
    +===================+=======================================+===========================================================+
    | ENC_FLT_LE        | Encode as a little endian 32 bit      | :class:`~kitty.model.low_level.encoder.FloatBinEncoder`   |
    +-------------------+---------------------------------------+                                                           |
    | ENC_FLT_BE        | Encode as a big endian 32 bit         |                                                           |
    +-------------------+---------------------------------------+                                                           |
    | ENC_DBL_LE        | Encode as a little endian 64 bit      |                                                           |
    +-------------------+---------------------------------------+                                                           |
    | ENC_DBL_BE        | Encode as a big endian 64 bit         |                                                           |
    +-------------------+---------------------------------------+-----------------------------------------------------------+
    | ENC_FLT_FP        | Fixed point                           | :class:`~kitty.model.low_level.encoder.FloatAsciiEncoder` |
    +-------------------+---------------------------------------+                                                           |
    | ENC_FLT_EXP       | Exponent notation                     |                                                           |
    +-------------------+---------------------------------------+                                                           |
    | ENC_FLT_EXP_UPPER | Exponent notation, with upper case E  |                                                           |
    +-------------------+---------------------------------------+                                                           |
    | ENC_FLT_GEN       | General format                        |                                                           |
    +-------------------+---------------------------------------+                                                           |
    | ENC_FLT_GEN_UPPER | General format, with upper case       |                                                           |
    +-------------------+---------------------------------------+-----------------------------------------------------------+
    | ENC_FLT_DEFAULT   | Same as ENC_FLT_BE                    | :class:`~kitty.model.low_level.encoder.FloatBinEncoder`   |
    +-------------------+---------------------------------------+-----------------------------------------------------------+
    '''

    def encode(self, value):
        '''
        :type value: ``float``
        :param value: value to encode
        :rtype: ``Bits``
        :return: encoded value in bits
        '''
        raise NotImplementedError('should be implemented in sub classes')


class FloatBinEncoder(FloatEncoder):
    '''
    Encode a floating point number in binary format as described by IEEE 754 (binary32 and binary64)
    '''

    def __init__(self, fmt):
        '''
        :type fmt: str
        :param fmt: format of binary encoding (see floating point encoding in struct docs.)
        '''
        super(FloatBinEncoder, self).__init__()
        self.fmt = fmt

    def encode(self, value):
        '''
        :param value: value to encode
        '''
        packed = pack(self.fmt, value)
        return Bits(bytes=packed)


class FloatAsciiEncoder(FloatEncoder):
    '''
    Encode a floating point number in ascii as described by IEEE 754 (decimal*)
    '''

    def __init__(self, fmt):
        '''
        :type fmt: str
        :param fmt: format of ascii encoding (see floating point encoding in string docs.)
        '''
        super(FloatAsciiEncoder, self).__init__()
        self.fmt = fmt

    def encode(self, value):
        '''
        :param value: value to encode
        '''
        return Bits(bytes=strToBytes(self.fmt % value))


ENC_FLT_LE = FloatBinEncoder('<f')
ENC_FLT_BE = FloatBinEncoder('>f')
ENC_DBL_LE = FloatBinEncoder('<d')
ENC_DBL_BE = FloatBinEncoder('>d')
ENC_FLT_FP = FloatAsciiEncoder('%f')
ENC_FLT_EXP = FloatAsciiEncoder('%e')
ENC_FLT_EXP_UPPER = FloatAsciiEncoder('%E')
ENC_FLT_GEN = FloatAsciiEncoder('%g')
ENC_FLT_GEN_UPPER = FloatAsciiEncoder('%G')
ENC_FLT_DEFAULT = ENC_FLT_BE
