# -*- coding: utf-8 -*-
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
Tests for low level fields:
'''
import struct
import os
from common import metaTest, BaseTestCase
from bitstring import Bits
from kitty.model import String, Delimiter, RandomBits, RandomBytes, Dynamic, Static, Group, Float
from kitty.model import BitField, UInt8, UInt16, UInt32, UInt64, SInt8, SInt16, SInt32, SInt64
from kitty.core import KittyException


class ValueTestCase(BaseTestCase):

    __meta__ = True
    default_value = None
    default_value_rendered = None

    def setUp(self, cls=None):
        super(ValueTestCase, self).setUp(cls)
        self.default_value = self.__class__.default_value
        self.default_value_rendered = self.__class__.default_value_rendered
        self.rendered_type = self.get_rendered_type()
        self.uut_name = 'uut'

    def get_rendered_type(self):
        return Bits

    def get_default_field(self, fuzzable=True):
        return self.cls(value=self.default_value, fuzzable=fuzzable, name=self.uut_name)

    def bits_to_value(self, bits):
        '''
        default behavior: take the bytes
        '''
        return bits.bytes.decode()

    def _get_all_mutations(self, field, reset=True):
        res = []
        while field.mutate():
            res.append(field.render())
        if reset:
            field.reset()
        return res

    def _base_check(self, field):
        num_mutations = field.num_mutations()
        mutations = self._get_all_mutations(field)
        self.assertEqual(num_mutations, len(mutations))
        self.assertEqual(len(mutations), len(set(mutations)))
        mutations = self._get_all_mutations(field)
        self.assertEqual(num_mutations, len(mutations))
        self.assertEqual(len(mutations), len(set(mutations)))

    @metaTest
    def testDummyToDo(self):
        self.assertEqual(len(self.todo), 0)

    @metaTest
    def testDefaultValue(self):
        field = self.get_default_field()
        res = field.render()
        self.assertEqual(self.default_value_rendered, res)
        field.mutate()
        field.reset()
        res = field.render()
        self.assertEqual(self.default_value_rendered, res)

    @metaTest
    def testMutateAllDifferent(self):
        field = self.get_default_field()
        mutations = self._get_all_mutations(field)
        self.assertEqual(len(set(mutations)), len(mutations))

    @metaTest
    def testNotFuzzable(self):
        field = self.get_default_field(fuzzable=False)
        num_mutations = field.num_mutations()
        self.assertEqual(num_mutations, 0)
        rendered = field.render()
        as_val = self.bits_to_value(rendered)
        self.assertAlmostEqual(as_val, self.default_value, places=5)
        mutated = field.mutate()
        self.assertFalse(mutated)
        rendered = field.render()
        as_val = self.bits_to_value(rendered)
        self.assertAlmostEqual(as_val, self.default_value, places=5)
        field.reset()
        mutated = field.mutate()
        self.assertFalse(mutated)
        rendered = field.render()
        as_val = self.bits_to_value(rendered)
        self.assertAlmostEqual(as_val, self.default_value, places=5)

    @metaTest
    def testNumMutations(self):
        field = self.get_default_field()
        num_mutations = field.num_mutations()
        self._check_mutation_count(field, num_mutations)

    @metaTest
    def testSameResultWhenSameParams(self):
        field1 = self.get_default_field()
        field2 = self.get_default_field()
        res1 = self._get_all_mutations(field1)
        res2 = self._get_all_mutations(field2)
        self.assertListEqual(res1, res2)

    @metaTest
    def testSameResultAfterReset(self):
        field = self.get_default_field()
        res1 = self._get_all_mutations(field)
        res2 = self._get_all_mutations(field)
        self.assertListEqual(res1, res2)

    @metaTest
    def testSkipZero(self):
        field = self.get_default_field(fuzzable=True)
        num_mutations = field.num_mutations()
        to_skip = 0
        expected_skipped = min(to_skip, num_mutations)
        expected_mutated = num_mutations - expected_skipped
        self._check_skip(field, to_skip, expected_skipped, expected_mutated)

    @metaTest
    def testSkipOne(self):
        field = self.get_default_field(fuzzable=True)
        num_mutations = field.num_mutations()
        to_skip = 1
        expected_skipped = min(to_skip, num_mutations)
        expected_mutated = num_mutations - expected_skipped
        self._check_skip(field, to_skip, expected_skipped, expected_mutated)

    @metaTest
    def testSkipHalf(self):
        field = self.get_default_field(fuzzable=True)
        num_mutations = field.num_mutations()
        to_skip = num_mutations // 2
        expected_skipped = min(to_skip, num_mutations)
        expected_mutated = num_mutations - expected_skipped
        self._check_skip(field, to_skip, expected_skipped, expected_mutated)

    @metaTest
    def testSkipExact(self):
        field = self.get_default_field(fuzzable=True)
        num_mutations = field.num_mutations()
        to_skip = num_mutations
        expected_skipped = min(to_skip, num_mutations)
        expected_mutated = num_mutations - expected_skipped
        self._check_skip(field, to_skip, expected_skipped, expected_mutated)

    @metaTest
    def testSkipTooMuch(self):
        field = self.get_default_field(fuzzable=True)
        num_mutations = field.num_mutations()
        to_skip = num_mutations + 1
        expected_skipped = min(to_skip, num_mutations)
        expected_mutated = num_mutations - expected_skipped
        self._check_skip(field, to_skip, expected_skipped, expected_mutated)

    @metaTest
    def testReturnTypeRenderFuzzable(self):
        field = self.get_default_field(fuzzable=True)
        self.assertIsInstance(field.render(), self.rendered_type)
        field.mutate()
        self.assertIsInstance(field.render(), self.rendered_type)
        field.reset()
        self.assertIsInstance(field.render(), self.rendered_type)

    @metaTest
    def testReturnTypeGetRenderedFuzzable(self):
        field = self.get_default_field(fuzzable=True)
        self.assertIsInstance(field.render(), self.rendered_type)
        field.mutate()
        self.assertIsInstance(field.render(), self.rendered_type)
        field.reset()
        self.assertIsInstance(field.render(), self.rendered_type)

    @metaTest
    def testReturnTypeMutateFuzzable(self):
        field = self.get_default_field(fuzzable=True)
        self.assertIsInstance(field.mutate(), bool)
        field.reset()
        self.assertIsInstance(field.mutate(), bool)

    @metaTest
    def testReturnTypeRenderNotFuzzable(self):
        field = self.get_default_field(fuzzable=False)
        self.assertIsInstance(field.render(), self.rendered_type)
        field.mutate()
        self.assertIsInstance(field.render(), self.rendered_type)
        field.reset()
        self.assertIsInstance(field.render(), self.rendered_type)

    @metaTest
    def testReturnTypeGetRenderedNotFuzzable(self):
        field = self.get_default_field(fuzzable=False)
        self.assertIsInstance(field.render(), self.rendered_type)
        field.mutate()
        self.assertIsInstance(field.render(), self.rendered_type)
        field.reset()
        self.assertIsInstance(field.render(), self.rendered_type)

    @metaTest
    def testReturnTypeMutateNotFuzzable(self):
        field = self.get_default_field(fuzzable=False)
        self.assertIsInstance(field.mutate(), bool)
        field.reset()
        self.assertIsInstance(field.mutate(), bool)

    @metaTest
    def testHashTheSameForTwoSimilarObjects(self):
        field1 = self.get_default_field()
        field2 = self.get_default_field()
        self.assertEqual(field1.hash(), field2.hash())

    @metaTest
    def testHashTheSameAfterReset(self):
        field = self.get_default_field()
        hash_after_creation = field.hash()
        field.mutate()
        hash_after_mutate = field.hash()
        self.assertEqual(hash_after_creation, hash_after_mutate)
        field.reset()
        hash_after_reset = field.hash()
        self.assertEqual(hash_after_creation, hash_after_reset)
        while field.mutate():
            hash_after_mutate_all = field.hash()
            self.assertEqual(hash_after_creation, hash_after_mutate_all)
            field.render()
            hash_after_render_all = field.hash()
            self.assertEqual(hash_after_creation, hash_after_render_all)

    @metaTest
    def testGetRenderedFields(self):
        field = self.get_default_field()
        field_list = [field]
        self.assertEqual(field.get_rendered_fields(), field_list)
        while field.mutate():
            if len(field.render()):
                self.assertEqual(field.get_rendered_fields(), field_list)
            else:
                self.assertEqual(field.get_rendered_fields(), [])

    @metaTest
    def testInvalidFieldNameRaisesException(self):
        with self.assertRaises(KittyException):
            self.uut_name = 'invalid/name'
            self.get_default_field()

    def _check_skip(self, field, to_skip, expected_skipped, expected_mutated):
        # print('_check_skip(%s, %s, %s, %s)' % (field, to_skip, expected_skipped, expected_mutated))
        skipped = field.skip(to_skip)
        self.assertEqual(expected_skipped, skipped)
        mutated = 0
        while field.mutate():
            mutated += 1
        self.assertEqual(expected_mutated, mutated)
        field.reset()
        skipped = field.skip(to_skip)
        self.assertEqual(expected_skipped, skipped)
        mutated = 0
        while field.mutate():
            mutated += 1
        self.assertEqual(expected_mutated, mutated)

    def _check_mutation_count(self, field, expected_num_mutations):
        num_mutations = field.num_mutations()
        self.assertEqual(num_mutations, expected_num_mutations)
        mutation_count = 0
        while field.mutate():
            mutation_count += 1
        self.assertEqual(mutation_count, expected_num_mutations)


class StringTests(ValueTestCase):

    __meta__ = False
    default_value = 'kitty'
    default_value_rendered = Bits(bytes=default_value.encode())

    def setUp(self, cls=String):
        super(StringTests, self).setUp(cls)

    def testMaxSizeNumMutations(self):
        max_size = 35
        nm_field = self.cls(value=self.default_value)
        excepted_mutation_count = 0
        while nm_field.mutate():
            res = nm_field.render().bytes
            if len(res) <= max_size:
                excepted_mutation_count += 1
        field = self.cls(value='kitty', max_size=max_size)
        num_mutations = field.num_mutations()
        self.assertEqual(excepted_mutation_count, num_mutations)
        self._check_mutation_count(field, excepted_mutation_count)

    def testMaxSizeMutations(self):
        max_size = 35
        max_size_in_bits = max_size * 8
        nm_field = self.cls(value=self.default_value)
        all_mutations = self._get_all_mutations(nm_field)
        field = self.cls(value=self.default_value, max_size=max_size)
        mutations = self._get_all_mutations(field)
        for mutation in all_mutations:
            if len(mutation) > max_size_in_bits:
                self.assertNotIn(mutation, mutations)
            else:
                self.assertIn(mutation, mutations)

    def _testStringsFromFile(self):
        values = [
            'It was the summer of 95 (so what!)',
            'In the backyard, shaving the old plies',
            'Feeling so strong (strong!), something went wrong (wrong!)',
            'Straight into my finger, what a stinger, it was so long',
            'I still remember that day, like the day that I said that I swear',
            '"I\'ll never hurt myself again", but it seems that I\'m deemed to be wrong',
            'To be wrong, to be wrong',
            'Gotta keep holding on...they always played a slow song.',
        ]
        filename = './kitty_strings.txt'
        with open(filename, 'wb') as f:
            f.write('\n'.join(values))
        uut = String(name=self.uut_name, value='streetlight')
        all_mutations = self.get_all_mutations(uut)
        for value in values:
            self.assertIn(Bits(bytes=value), all_mutations)
        os.remove(filename)


class DelimiterTests(StringTests):

    __meta__ = False
    default_value = 'kitty'
    default_value_rendered = Bits(bytes=default_value.encode())

    def setUp(self, cls=Delimiter):
        super(DelimiterTests, self).setUp(cls)


class DynamicTests(ValueTestCase):

    __meta__ = False
    default_value = 'kitty'
    default_value_rendered = Bits(bytes=default_value.encode())

    def setUp(self, cls=Dynamic):
        super(DynamicTests, self).setUp(cls)
        self.key_exists = 'exists'
        self.value_exists = 'value'
        self.key_not_exist = 'not exist'
        self.default_session_data = {
            self.key_exists: self.value_exists
        }

    def get_default_field(self, fuzzable=True):
        return self.cls(key='my_key', default_value=self.default_value, length=len(self.default_value), fuzzable=fuzzable, name=self.uut_name)

    def testSessionDataNotFuzzable(self):
        field = self.cls(key=self.key_exists, default_value=self.default_value)
        self.assertEqual(self.default_value_rendered, field.render())
        field.set_session_data(self.default_session_data)
        self.assertEqual(Bits(bytes=self.value_exists.encode()), field.render())
        self.assertEqual(Bits(bytes=self.value_exists.encode()), field.render())

    def testSessionDataNotFuzzableAfterReset(self):
        field = self.cls(key=self.key_exists, default_value=self.default_value)
        self.assertEqual(self.default_value_rendered, field.render())
        field.set_session_data(self.default_session_data)
        self.assertEqual(Bits(bytes=self.value_exists.encode()), field.render())
        field.reset()
        self.assertEqual(self.default_value_rendered, field.render())

    def testSessionDataNotFuzzableDataChangeKeyExists(self):
        field = self.cls(key=self.key_exists, default_value=self.default_value)
        self.assertEqual(self.default_value_rendered, field.render())
        field.set_session_data(self.default_session_data)
        self.assertEqual(Bits(bytes=self.value_exists.encode()), field.render())
        new_val = 'new value'
        field.set_session_data({self.key_exists: new_val})
        self.assertEqual(Bits(bytes=new_val.encode()), field.render())

    def testSessionDataNotFuzzableDataChangeKeyNotExist(self):
        field = self.cls(key=self.key_exists, default_value=self.default_value)
        self.assertEqual(self.default_value_rendered, field.render())
        field.set_session_data(self.default_session_data)
        self.assertEqual(Bits(bytes=self.value_exists.encode()), field.render())
        new_val = 'new value'
        field.set_session_data({self.key_not_exist: new_val})
        self.assertEqual(Bits(bytes=self.value_exists.encode()), field.render())

    def testSessionDataFuzzableAfterReset(self):
        field = self.cls(key=self.key_exists, default_value=self.default_value, length=len(self.default_value), fuzzable=True)
        self.assertEqual(self.default_value_rendered, field.render())
        field.set_session_data(self.default_session_data)
        self.assertEqual(Bits(bytes=self.value_exists.encode()), field.render())
        field.reset()
        self.assertEqual(self.default_value_rendered, field.render())

    def testSessionDataFuzzableDataChangeKeyExists(self):
        field = self.cls(key=self.key_exists, default_value=self.default_value, length=len(self.default_value), fuzzable=True)
        self.assertEqual(self.default_value_rendered, field.render())
        field.set_session_data(self.default_session_data)
        self.assertEqual(Bits(bytes=self.value_exists.encode()), field.render())
        new_val = 'new value'
        field.set_session_data({self.key_exists: new_val})
        self.assertEqual(Bits(bytes=new_val.encode()), field.render())

    def testSessionDataFuzzableDataChangeKeyNotExist(self):
        field = self.cls(key=self.key_exists, default_value=self.default_value, length=len(self.default_value), fuzzable=True)
        self.assertEqual(self.default_value_rendered, field.render())
        field.set_session_data(self.default_session_data)
        self.assertEqual(Bits(bytes=self.value_exists.encode()), field.render())
        new_val = 'new value'
        field.set_session_data({self.key_not_exist: new_val})
        self.assertEqual(Bits(bytes=self.value_exists.encode()), field.render())


class RandomBitsTests(ValueTestCase):

    __meta__ = False
    default_value = 'kitty'
    default_unused_bits = 3
    default_value_rendered = Bits(bytes=default_value.encode())[:-3]

    def setUp(self, cls=RandomBits):
        super(RandomBitsTests, self).setUp(cls)

    def get_default_field(self, fuzzable=True):
        return self.cls(value=self.default_value, min_length=5, max_length=10, unused_bits=self.default_unused_bits, fuzzable=fuzzable, name=self.uut_name)

    def testNotFuzzable(self):
        field = self.get_default_field(fuzzable=False)
        num_mutations = field.num_mutations()
        self.assertEqual(num_mutations, 0)
        rendered = field.render()
        self.assertEqual(rendered, self.default_value_rendered)
        mutated = field.mutate()
        self.assertFalse(mutated)
        rendered = field.render()
        self.assertEqual(rendered, self.default_value_rendered)
        field.reset()
        mutated = field.mutate()
        self.assertFalse(mutated)
        rendered = field.render()
        self.assertEqual(rendered, self.default_value_rendered)

    def testNoStepNumMutations(self):
        param_num_mutations = 100
        field = self.cls(value=self.default_value, min_length=10, max_length=20, unused_bits=3, num_mutations=param_num_mutations)
        self._check_mutation_count(field, param_num_mutations)
        field.reset()
        self._check_mutation_count(field, param_num_mutations)

    def testNoStepSizes(self):
        min_length = 10
        max_length = 100
        field = self.cls(value=self.default_value, min_length=min_length, max_length=max_length, unused_bits=self.default_unused_bits)
        while field.mutate():
            rendered = field.render()
            self.assertGreaterEqual(len(rendered), min_length)
            self.assertLessEqual(len(rendered), max_length)

    def testNoStepMinNegative(self):
        with self.assertRaises(KittyException):
            self.cls(value=self.default_value, min_length=-1, max_length=4)

    def testNoStepMaxNegative(self):
        with self.assertRaises(KittyException):
            self.cls(value=self.default_value, min_length=-2, max_length=-1)

    def testNoStepMaxIs0(self):
        with self.assertRaises(KittyException):
            self.cls(value=self.default_value, min_length=0, max_length=0)

    def testNoStepMinBiggerThanMax(self):
        with self.assertRaises(KittyException):
            self.cls(value=self.default_value, min_length=5, max_length=4)

    def testNoStepRandomness(self):
        min_length = 10
        max_length = 100
        field = self.cls(value=self.default_value, min_length=min_length, max_length=max_length, unused_bits=self.default_unused_bits)
        mutations = self._get_all_mutations(field)
        self.assertNotEqual(len(set(mutations)), 1)

    def testSeedNotTheSame(self):
        min_length = 10
        max_length = 100
        field1 = self.cls(value=self.default_value, seed=11111, min_length=min_length, max_length=max_length, unused_bits=self.default_unused_bits)
        field2 = self.cls(value=self.default_value, seed=22222, min_length=min_length, max_length=max_length, unused_bits=self.default_unused_bits)
        res1 = self._get_all_mutations(field1)
        res2 = self._get_all_mutations(field2)
        self.assertNotEqual(res1, res2)

    def testStepNumMutations(self):
        min_length = 10
        max_length = 100
        step = 3
        excepted_num_mutations = (max_length - min_length) // step
        field = self.cls(value=self.default_value, min_length=min_length, max_length=max_length, unused_bits=7, step=step)
        self._check_mutation_count(field, excepted_num_mutations)
        field.reset()
        self._check_mutation_count(field, excepted_num_mutations)

    def testStepSizes(self):
        min_length = 10
        max_length = 100
        step = 3
        field = self.cls(value=self.default_value, min_length=min_length, max_length=max_length, unused_bits=self.default_unused_bits, step=step)
        expected_length = min_length
        while field.mutate():
            rendered = field.render()
            self.assertEqual(len(rendered), expected_length)
            expected_length += step

    def testStepMinNegative(self):
        with self.assertRaises(KittyException):
            self.cls(value=self.default_value, min_length=-1, max_length=4, step=1)

    def testStepMaxNegative(self):
        with self.assertRaises(KittyException):
            self.cls(value=self.default_value, min_length=-2, max_length=-1, step=1)

    def testStepMaxIs0(self):
        with self.assertRaises(KittyException):
            self.cls(value=self.default_value, min_length=0, max_length=0, step=1)

    def testStepMinBiggerThanMax(self):
        with self.assertRaises(KittyException):
            self.cls(value=self.default_value, min_length=5, max_length=4, step=1)

    def testStepNegative(self):
        with self.assertRaises(KittyException):
            self.cls(value=self.default_value, min_length=1, max_length=5, step=-1)

    def testStepRandomness(self):
        min_length = 10
        max_length = 100
        step = 5
        field = self.cls(value=self.default_value, min_length=min_length, max_length=max_length, unused_bits=self.default_unused_bits, step=step)
        mutations = self._get_all_mutations(field)
        self.assertNotEqual(len(set(mutations)), 1)


class RandomBytesTests(ValueTestCase):

    __meta__ = False
    default_value = 'kitty'
    default_value_rendered = Bits(bytes=default_value.encode())

    def setUp(self, cls=RandomBytes):
        super(RandomBytesTests, self).setUp(cls)

    def get_default_field(self, fuzzable=True):
        return self.cls(value=self.default_value, min_length=5, max_length=10, fuzzable=fuzzable, name=self.uut_name)

    def testNoStepNumMutations(self):
        param_num_mutations = 100
        field = RandomBytes(value=self.default_value, min_length=10, max_length=20, num_mutations=param_num_mutations)
        self._check_mutation_count(field, param_num_mutations)
        field.reset()
        self._check_mutation_count(field, param_num_mutations)

    def testNoStepSizes(self):
        min_length = 10
        max_length = 100
        field = RandomBytes(value=self.default_value, min_length=min_length, max_length=max_length)
        while field.mutate():
            rendered = field.render().bytes
            self.assertGreaterEqual(len(rendered), min_length)
            self.assertLessEqual(len(rendered), max_length)

    def testNoStepMinNegative(self):
        with self.assertRaises(KittyException):
            RandomBytes(value=self.default_value, min_length=-1, max_length=4)

    def testNoStepMaxNegative(self):
        with self.assertRaises(KittyException):
            RandomBytes(value=self.default_value, min_length=-2, max_length=-1)

    def testNoStepMaxIs0(self):
        with self.assertRaises(KittyException):
            RandomBytes(value=self.default_value, min_length=0, max_length=0)

    def testNoStepMinBiggerThanMax(self):
        with self.assertRaises(KittyException):
            RandomBytes(value=self.default_value, min_length=5, max_length=4)

    def testNoStepRandomness(self):
        min_length = 10
        max_length = 100
        field = RandomBytes(value=self.default_value, min_length=min_length, max_length=max_length)
        mutations = self._get_all_mutations(field)
        self.assertNotEqual(len(set(mutations)), 1)

    def testSeedNotTheSame(self):
        min_length = 10
        max_length = 100
        field1 = RandomBytes(value=self.default_value, seed=11111, min_length=min_length, max_length=max_length)
        field2 = RandomBytes(value=self.default_value, seed=22222, min_length=min_length, max_length=max_length)
        res1 = self._get_all_mutations(field1)
        res2 = self._get_all_mutations(field2)
        self.assertNotEqual(res1, res2)

    def testStepNumMutations(self):
        min_length = 10
        max_length = 100
        step = 3
        excepted_num_mutations = (max_length - min_length) // step
        field = RandomBytes(value=self.default_value, min_length=min_length, max_length=max_length, step=step)
        self._check_mutation_count(field, excepted_num_mutations)
        field.reset()
        self._check_mutation_count(field, excepted_num_mutations)

    def testStepSizes(self):
        min_length = 10
        max_length = 100
        step = 3
        field = RandomBytes(value=self.default_value, min_length=min_length, max_length=max_length, step=step)
        expected_length = min_length
        while field.mutate():
            rendered = field.render().bytes
            self.assertEqual(len(rendered), expected_length)
            expected_length += step

    def testStepMinNegative(self):
        with self.assertRaises(KittyException):
            RandomBytes(value=self.default_value, min_length=-1, max_length=4, step=1)

    def testStepMaxNegative(self):
        with self.assertRaises(KittyException):
            RandomBytes(value=self.default_value, min_length=-2, max_length=-1, step=1)

    def testStepMaxIs0(self):
        with self.assertRaises(KittyException):
            RandomBytes(value=self.default_value, min_length=0, max_length=0, step=1)

    def testStepMinBiggerThanMax(self):
        with self.assertRaises(KittyException):
            RandomBytes(value=self.default_value, min_length=5, max_length=4, step=1)

    def testStepNegative(self):
        with self.assertRaises(KittyException):
            RandomBytes(value=self.default_value, min_length=1, max_length=5, step=-1)

    def testStepRandomness(self):
        min_length = 10
        max_length = 100
        step = 5
        field = RandomBytes(value=self.default_value, min_length=min_length, max_length=max_length, step=step)
        mutations = self._get_all_mutations(field)
        self.assertNotEqual(len(set(mutations)), 1)


class StaticTests(ValueTestCase):

    __meta__ = False
    default_value = 'kitty'
    default_value_rendered = Bits(bytes=default_value.encode())

    def setUp(self, cls=Static):
        super(StaticTests, self).setUp(cls)

    def testNumMutations0(self):
        field = Static(value=self.default_value)
        num_mutations = field.num_mutations()
        self.assertEqual(num_mutations, 0)
        self._check_mutation_count(field, num_mutations)
        field.reset()
        self._check_mutation_count(field, num_mutations)

    def get_default_field(self, fuzzable=True):
        return Static(value=self.default_value, name=self.uut_name)


class GroupTests(ValueTestCase):

    __meta__ = False
    default_value = 'group 1'
    default_value_rendered = Bits(bytes=default_value.encode())
    default_values = [default_value, 'group 2', 'group 3', 'group 4', 'group 5']

    def setUp(self, cls=Group):
        super(GroupTests, self).setUp(cls)
        self.default_values = self.__class__.default_values

    def get_default_field(self, fuzzable=True):
        return self.cls(values=self.default_values, fuzzable=fuzzable, name=self.uut_name)

    def testMutations(self):
        field = self.get_default_field()
        mutations = self._get_all_mutations(field)
        self.assertListEqual([Bits(bytes=x.encode()) for x in self.default_values], mutations)
        mutations = self._get_all_mutations(field)
        self.assertListEqual([Bits(bytes=x.encode()) for x in self.default_values], mutations)


class FloatTests(ValueTestCase):
    __meta__ = False
    default_value = 15.3
    default_value_rendered = Bits(bytes=struct.pack('>f', default_value))

    def setUp(self):
        super(FloatTests, self).setUp(Float)

    def bits_to_value(self, bits):
        return struct.unpack('>f', bits.tobytes())[0]


class BitFieldTests(ValueTestCase):

    __meta__ = False
    default_value = 500
    default_length = 15
    default_value_rendered = Bits('uint:%d=%d' % (default_length, default_value))

    def setUp(self, cls=BitField):
        super(BitFieldTests, self).setUp(cls)
        self.default_length = self.__class__.default_length

    def get_rendered_type(self):
        return Bits

    def get_default_field(self, fuzzable=True):
        return self.cls(value=self.default_value, length=self.default_length, fuzzable=fuzzable, name=self.uut_name)

    def bits_to_value(self, bits):
        '''
        BitField returns a tuple. so just give the value...
        '''
        return bits.uint

    def testLengthNegative(self):
        with self.assertRaises(KittyException):
            BitField(value=self.default_value, length=-1)

    def testLengthZero(self):
        with self.assertRaises(KittyException):
            BitField(value=self.default_value, length=0)

    def testLengthVerySmall(self):
        for full_range in[True, False]:
            self._base_check(BitField(value=1, length=1, full_range=full_range))

    def testLengthTooSmallForValueSigned(self):
        for full_range in[True, False]:
            with self.assertRaises(KittyException):
                BitField(value=64, length=7, signed=True, full_range=full_range)

    def testLengthTooSmallForValueUnsigned(self):
        for full_range in[True, False]:
            with self.assertRaises(KittyException):
                BitField(value=64, length=6, signed=False, full_range=full_range)

    def testLengthTooSmallForMaxValue(self):
        for full_range in[True, False]:
            with self.assertRaises(KittyException):
                BitField(value=10, length=5, signed=True, max_value=17, full_range=full_range)

    def testLengthVeryLarge(self):
        for full_range in[True, False]:
            field = BitField(value=1, length=1)
            self._base_check(field)

    def testLengthNonByteAlignedUnsigned(self):
        signed = False
        for full_range in[True, False]:
            self._base_check(BitField(value=10, length=7, signed=signed, full_range=full_range))
            self._base_check(BitField(value=10, length=14, signed=signed, full_range=full_range))
        self._base_check(BitField(value=10, length=15, signed=signed))
        self._base_check(BitField(value=10, length=16, signed=signed))
        self._base_check(BitField(value=10, length=58, signed=signed))
        self._base_check(BitField(value=10, length=111, signed=signed))

    def testLengthNonByteAlignedSigned(self):
        signed = True
        for full_range in[True, False]:
            self._base_check(BitField(value=10, length=7, signed=signed, full_range=full_range))
            self._base_check(BitField(value=10, length=14, signed=signed, full_range=full_range))
        self._base_check(BitField(value=10, length=15, signed=signed))
        self._base_check(BitField(value=10, length=16, signed=signed))
        self._base_check(BitField(value=10, length=58, signed=signed))
        self._base_check(BitField(value=10, length=111, signed=signed))

    def testValueNegative(self):
        for full_range in[True, False]:
            self._base_check(BitField(value=-50, length=7, signed=True, full_range=full_range))

    def _testIntsFromFile(self):
        values = [
            '0xffffffff',
            '-345345',
            '123',
            '0',
            '333',
            '56'
        ]
        filename = './kitty_integers.txt'
        with open(filename, 'wb') as f:
            f.write('\n'.join(values))
        self._base_check(BitField(name=self.uut_name, value=1, length=12))
        os.remove(filename)


class AlignedBitTests(ValueTestCase):
    #
    # Ugly ? yes, but this way we avoid errors when they are not needed...
    #
    __meta__ = True
    default_value = 500
    default_length = 16
    default_value_rendered = Bits('uint:%d=%d' % (default_length, default_value))

    def setUp(self, cls=None):
        super(AlignedBitTests, self).setUp(cls)
        self.default_length = self.__class__.default_length

    def get_rendered_type(self):
        return Bits

    def get_default_field(self, fuzzable=True):
        return self.cls(value=self.default_value, fuzzable=fuzzable, name=self.uut_name)

    def bits_to_value(self, bits):
        return bits.uint

    @metaTest
    def testMaxValue(self):
        max_value = self.default_value + 10
        field = self.cls(value=self.default_value, max_value=max_value)
        mutations = self._get_all_mutations(field)
        for mutation in mutations:
            self.assertGreaterEqual(max_value, self.bits_to_value(mutation))

    @metaTest
    def testMinValue(self):
        min_value = self.default_value - 10
        field = self.cls(value=self.default_value, min_value=min_value)
        mutations = self._get_all_mutations(field)
        for mutation in mutations:
            self.assertLessEqual(min_value, self.bits_to_value(mutation))

    @metaTest
    def testMinMaxValue(self):
        min_value = self.default_value - 10
        max_value = self.default_value + 10
        field = self.cls(value=self.default_value, min_value=min_value, max_value=max_value)
        mutations = self._get_all_mutations(field)
        for mutation in mutations:
            self.assertLessEqual(min_value, self.bits_to_value(mutation))
            self.assertGreaterEqual(max_value, self.bits_to_value(mutation))


class SignedAlignedBitTests(AlignedBitTests):

    __meta__ = True

    def bits_to_value(self, bits):
        return bits.int


class SInt8Tests(SignedAlignedBitTests):

    __meta__ = False
    default_value = 50
    default_length = 8
    default_value_rendered = Bits('int:%d=%d' % (default_length, default_value))

    def setUp(self, cls=SInt8):
        super(SInt8Tests, self).setUp(cls)


class SInt16Tests(SignedAlignedBitTests):

    __meta__ = False
    default_value = 0x1000
    default_length = 16
    default_value_rendered = Bits('int:%d=%d' % (default_length, default_value))

    def setUp(self, cls=SInt16):
        super(SInt16Tests, self).setUp(cls)


class SInt32Tests(SignedAlignedBitTests):

    __meta__ = False
    default_value = 0x12345678
    default_length = 32
    default_value_rendered = Bits('int:%d=%d' % (default_length, default_value))

    def setUp(self, cls=SInt32):
        super(SInt32Tests, self).setUp(cls)


class SInt64Tests(SignedAlignedBitTests):

    __meta__ = False
    default_value = 0x1122334455667788
    default_length = 64
    default_value_rendered = Bits('int:%d=%d' % (default_length, default_value))

    def setUp(self, cls=SInt64):
        super(SInt64Tests, self).setUp(cls)


class UnsignedAlignedBitTests(AlignedBitTests):

    __meta__ = True

    def bits_to_value(self, bits):
        return bits.uint


class UInt8Tests(UnsignedAlignedBitTests):

    __meta__ = False
    default_value = 50
    default_length = 8
    default_value_rendered = Bits('uint:%d=%d' % (default_length, default_value))

    def setUp(self, cls=UInt8):
        super(UInt8Tests, self).setUp(cls)


class UInt16Tests(UnsignedAlignedBitTests):

    __meta__ = False
    default_value = 0x1000
    default_length = 16
    default_value_rendered = Bits('uint:%d=%d' % (default_length, default_value))

    def setUp(self, cls=UInt16):
        super(UInt16Tests, self).setUp(cls)


class UInt32Tests(UnsignedAlignedBitTests):

    __meta__ = False
    default_value = 0x12345678
    default_length = 32
    default_value_rendered = Bits('uint:%d=%d' % (default_length, default_value))

    def setUp(self, cls=UInt32):
        super(UInt32Tests, self).setUp(cls)


class UInt64Tests(UnsignedAlignedBitTests):

    __meta__ = False
    default_value = 0x1122334455667788
    default_length = 64
    default_value_rendered = Bits('uint:%d=%d' % (default_length, default_value))

    def setUp(self, cls=UInt64):
        super(UInt64Tests, self).setUp(cls)
