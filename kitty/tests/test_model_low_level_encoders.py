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
Tests for low level encoders:
'''
from struct import pack
from binascii import hexlify
from bitstring import Bits
from kitty.model.low_level.encoder import BitFieldMultiByteEncoder
from kitty.model.low_level.encoder import StrFuncEncoder, StrEncodeEncoder
from kitty.model.low_level.encoder import StrNullTerminatedEncoder
from kitty.model.low_level.encoder import BitsEncoder, ByteAlignedBitsEncoder, ReverseBitsEncoder
from kitty.model.low_level.encoder import StrEncoderWrapper, BitsFuncEncoder
from kitty.model.low_level.encoder import BitFieldBinEncoder
from kitty.model.low_level.encoder import strToBytes
from kitty.model.low_level import BitField
from kitty.core import KittyException
from common import BaseTestCase


class BitFieldBinEncoderTests(BaseTestCase):

    def setUp(self, cls=BitFieldBinEncoder):
        super(BitFieldBinEncoderTests, self).setUp(cls)
        self.fmt = '>I'
        self.signed = False
        self.length = 32
        self.mode = 'be'

    def _encode_func(self, value):
        return Bits(bytes=pack(self.fmt, value))

    def get_default_encoder(self):
        return BitFieldBinEncoder(self.mode)

    def testCorrectEncoding(self):
        uut = self.get_default_encoder()
        value = 0x12345678
        self.assertEqual(uut.encode(value, self.length, self.signed), self._encode_func(value))

    def testSignedValue(self):
        uut = self.get_default_encoder()
        value = -1234
        self.signed = True
        self.fmt = '>i'
        self.assertEqual(uut.encode(value, self.length, self.signed), self._encode_func(value))

    def testLittleEndian(self):
        self.mode = 'le'
        self.fmt = '<I'
        uut = self.get_default_encoder()
        value = 0x12345678
        self.assertEqual(uut.encode(value, self.length, self.signed), self._encode_func(value))

    def testExceptionIfLengthIsNotAligned(self):
        uut = self.get_default_encoder()
        with self.assertRaises(Exception):
            uut.encode(1, 9, True)


class BitFieldMultiByteEncoderTest(BaseTestCase):

    def setUp(self, cls=None):
        super(BitFieldMultiByteEncoderTest, self).setUp(cls)

    def _multibyte_len(self, num):
        num_bits = len(bin(num)) - 2
        num_bytes = num_bits // 7
        if num_bits % 7 != 0:
            num_bytes += 1
        return num_bytes * 8

    def _test(self, bitfield):
        expected_len = self._multibyte_len(bitfield._default_value)
        # bitfield.mutate()
        rendered = bitfield.render()
        self.assertEqual(expected_len, len(rendered))

    def testUnsignedLength8(self):
        bitfield = BitField(
            0xaa,
            length=8,
            signed=False,
            max_value=255,
            encoder=BitFieldMultiByteEncoder()
        )
        self._test(bitfield)

    def testUnsignedLength16(self):
        bitfield = BitField(
            1234,
            length=16,
            signed=False,
            encoder=BitFieldMultiByteEncoder()
        )
        self._test(bitfield)

    def testUnsignedLength32(self):
        bitfield = BitField(
            1234,
            length=32,
            signed=False,
            encoder=BitFieldMultiByteEncoder()
        )
        self._test(bitfield)

    def testUnsignedLength64(self):
        bitfield = BitField(
            78945,
            length=64,
            signed=False,
            encoder=BitFieldMultiByteEncoder()
        )
        self._test(bitfield)

    def testUnsignedLength11(self):
        bitfield = BitField(
            14,
            length=11,
            signed=False,
            encoder=BitFieldMultiByteEncoder()
        )
        self._test(bitfield)

    def testZero(self):
        uut = BitFieldMultiByteEncoder()
        self.assertEqual(uut.encode(0, 10, False), Bits(bytes=b'\x00'))

    def testBitFieldMultiByteEncoderSignedUnsupported(self):
        with self.assertRaises(KittyException):
            BitField(
                -12,
                length=8,
                signed=True,
                max_value=127,
                encoder=BitFieldMultiByteEncoder()
            )


class StrFuncEncoderTest(BaseTestCase):

    def setUp(self, cls=StrFuncEncoder):
        super(StrFuncEncoderTest, self).setUp(cls)

    def _encode_func(self, s):
        return hexlify(strToBytes(s))

    def get_default_encoder(self):
        return self.cls(self._encode_func)

    def testReturnValueIsBits(self):
        uut = self.get_default_encoder()
        encoded = uut.encode('abc')
        self.assertIsInstance(encoded, Bits)

    def testExceptionIfInputIsInt(self):
        uut = self.get_default_encoder()
        with self.assertRaises(KittyException):
            uut.encode(1)

    def testExceptionIfInputIsList(self):
        uut = self.get_default_encoder()
        with self.assertRaises(KittyException):
            uut.encode([])

    def testExceptionIfInputIsStringList(self):
        uut = self.get_default_encoder()
        with self.assertRaises(KittyException):
            uut.encode(['a', 'b', 'c'])

    def testCorrectValueEncoded(self):
        value = 'abcd'
        expected_encoded = self._encode_func(value)
        uut = self.get_default_encoder()
        encoded = uut.encode(value).tobytes()
        self.assertEqual(encoded, expected_encoded)

    def testEmptyValueEncoded(self):
        value = ''
        expected_encoded = self._encode_func(value)
        uut = self.get_default_encoder()
        encoded = uut.encode(value).tobytes()
        self.assertEqual(encoded, expected_encoded)


class StrEncodeEncoderTest(StrFuncEncoderTest):

    def setUp(self, cls=StrEncodeEncoder):
        super(StrEncodeEncoderTest, self).setUp(cls)
        self.encoding = 'hex'

    def _encode_func(self, s):
        return hexlify(strToBytes(s))

    def get_default_encoder(self):
        return self.cls(self.encoding)


class StrNullTerminatedEncoderTest(StrFuncEncoderTest):

    def setUp(self, cls=StrNullTerminatedEncoder):
        super(StrNullTerminatedEncoderTest, self).setUp(cls)

    def _encode_func(self, s):
        return strToBytes(s) + b'\x00'

    def get_default_encoder(self):
        return self.cls()


class BitsEncoderTest(BaseTestCase):

    def setUp(self, cls=BitsEncoder):
        super(BitsEncoderTest, self).setUp(cls)

    def _encode_func(self, bits):
        return bits

    def get_default_encoder(self):
        return self.cls()

    def testCorrectEncoding(self):
        value = Bits(bin='01010011')
        uut = self.get_default_encoder()
        self.assertEqual(uut.encode(value), self._encode_func(value))

    def testEmptyBits(self):
        value = Bits()
        uut = self.get_default_encoder()
        self.assertEqual(uut.encode(value), Bits())

    def testRaisesExceptionWhenValueIsNotBits(self):
        uut = self.get_default_encoder()
        with self.assertRaises(KittyException):
            uut.encode(1)
        with self.assertRaises(KittyException):
            uut.encode('hello')


class ReverseBitsEncoderTest(BitsEncoderTest):

    def setUp(self):
        super(ReverseBitsEncoderTest, self).setUp(ReverseBitsEncoder)

    def _encode_func(self, bits):
        return bits[::-1]


class ByteAlignedBitsEncoderTest(BitsEncoderTest):

    def setUp(self):
        super(ByteAlignedBitsEncoderTest, self).setUp(ByteAlignedBitsEncoder)

    def _encode_func(self, bits):
        remainder = len(bits) % 8
        pad_len = (8 - remainder) % 8
        return bits + Bits(pad_len)

    def testPaddingNoPad(self):
        value = Bits(bytes=b'\x01')
        uut = self.get_default_encoder()
        self.assertEqual(uut.encode(value), value)

    def testPadding1(self):
        value = Bits(bin='1111111')
        expected = Bits(bin='11111110')
        uut = self.get_default_encoder()
        self.assertEqual(uut.encode(value), expected)

    def testPadding4(self):
        value = Bits(bin='1111')
        expected = Bits(bin='11110000')
        uut = self.get_default_encoder()
        self.assertEqual(uut.encode(value), expected)

    def testPadding7(self):
        value = Bits(bin='1')
        expected = Bits(bin='10000000')
        uut = self.get_default_encoder()
        self.assertEqual(uut.encode(value), expected)

    def testPaddingMoreThanOneByte(self):
        value = Bits(bin='1100110011')
        expected = Bits(bin='1100110011000000')
        uut = self.get_default_encoder()
        self.assertEqual(uut.encode(value), expected)


class StrEncoderWrapperTest(BitsEncoderTest):

    def setUp(self):
        super(StrEncoderWrapperTest, self).setUp(StrEncoderWrapper)
        self._str_encoder = StrEncodeEncoder('base64')

    def _encode_func(self, bits):
        return self._str_encoder.encode(bits.tobytes())

    def get_default_encoder(self):
        return self.cls(self._str_encoder)

    def testExceptionWhenBitsNotByteAligned(self):
        value = Bits(bin='1111111')
        uut = self.get_default_encoder()
        with self.assertRaises(KittyException):
            uut.encode(value)


class BitsFuncEncoderTest(BitsEncoderTest):

    def setUp(self):
        super(BitsFuncEncoderTest, self).setUp(BitsFuncEncoder)

    def _encode_func(self, bits):
        return bits[::-1]

    def get_default_encoder(self):
        return self.cls(self._encode_func)
