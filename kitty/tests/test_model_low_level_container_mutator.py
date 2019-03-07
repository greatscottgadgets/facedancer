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
Tests for Mutators and Mutator-based containers
'''
from bitstring import Bits
from common import metaTest, BaseTestCase
from kitty.model.low_level import String, Static
from kitty.model.low_level import Container
from kitty.model.low_level import List, OmitMutator, DuplicateMutator, RotateMutator
from kitty.core import KittyException

empty_bits = Bits()


class MutatorTests(BaseTestCase):

    __meta__ = True

    def setUp(self, cls=None):
        super(MutatorTests, self).setUp(cls)
        self.uut_name = 'uut'

    def get_uut(self, field_count, fields, delim=None, fuzzable=True):
        return self.cls(field_count=field_count, fields=fields, delim=delim, fuzzable=fuzzable, name=self.uut_name)

    @metaTest
    def testEmptyWhileNotMutating(self):
        fields = [Static('A'), Static('B'), Static('C')]
        uut = self.get_uut(2, fields)
        rendered = uut.render()
        self.assertEqual(rendered, empty_bits)
        while uut.mutate():
            pass
        uut.reset()
        rendered = uut.render()
        self.assertEqual(rendered, empty_bits)

    @metaTest
    def testEmptyWhenNotFuzzable(self):
        fields = [Static('A'), Static('B'), Static('C')]
        uut = self.get_uut(2, fields, fuzzable=False)
        rendered = uut.render()
        self.assertEqual(rendered, empty_bits)
        self.assertEqual(uut.num_mutations(), 0)
        self.assertFalse(uut.mutate())
        rendered = uut.render()
        self.assertEqual(rendered, empty_bits)

    @metaTest
    def testSameMutationsAfterReset(self):
        fields = [Static('A'), Static('B'), Static('C')]
        uut = self.get_uut(2, fields)
        mutations1 = self.get_all_mutations(uut)
        mutations2 = self.get_all_mutations(uut)
        self.assertEqual(mutations1, mutations2)

    @metaTest
    def testExceptionRaisedIfFieldCountIs0(self):
        with self.assertRaises(KittyException):
            self.get_uut(field_count=0, fields=[])

    @metaTest
    def testExceptionRaisedIfFieldCountIsNegative(self):
        with self.assertRaises(KittyException):
            self.get_uut(field_count=-1, fields=[])

    def _staticTest(self, values, field_count, expected, **kwargs):
        fields = [Static(c) for c in values]
        uut = self.get_uut(field_count, fields, **kwargs)
        self.assertEqual(uut.num_mutations(), len(expected))
        mutations = [x.tobytes().decode() for x in self.get_all_mutations(uut)]
        self.assertEqual(mutations, expected)

    def _stringTest(self, values, field_count, expected, **kwargs):
        fields = [String(c) for c in values]
        uut = self.get_uut(field_count, fields, **kwargs)
        self.assertEqual(uut.num_mutations(), len(expected))
        mutations = [x.tobytes().decode() for x in self.get_all_mutations(uut)]
        self.assertEqual(mutations, expected)


class DuplicateMutatorTests(MutatorTests):

    __meta__ = False

    def setUp(self, cls=DuplicateMutator):
        super(DuplicateMutatorTests, self).setUp(cls)

    def get_uut(self, field_count, fields, dup_num=1, fuzzable=True):
        return self.cls(field_count=field_count, dup_num=dup_num, fields=fields, fuzzable=fuzzable, name=self.uut_name)

    def testMutationsFieldCount1DupNum2(self):
        letters = 'ABCDEF'
        field_count = 1
        dup_num = 2
        expected = ['AABCDEF', 'ABBCDEF', 'ABCCDEF', 'ABCDDEF', 'ABCDEEF', 'ABCDEFF']
        self._staticTest(letters, field_count, expected, dup_num=dup_num)
        self._stringTest(letters, field_count, expected, dup_num=dup_num)

    def testMutationsFieldCount1DupNum4(self):
        letters = 'ABCDEF'
        field_count = 1
        dup_num = 4
        expected = ['AAAABCDEF', 'ABBBBCDEF', 'ABCCCCDEF', 'ABCDDDDEF', 'ABCDEEEEF', 'ABCDEFFFF']
        self._staticTest(letters, field_count, expected, dup_num=dup_num)
        self._stringTest(letters, field_count, expected, dup_num=dup_num)

    def testMutationsFieldCount1DupNum10(self):
        letters = 'ABCDEF'
        field_count = 1
        dup_num = 10
        expected = [
            'AAAAAAAAAABCDEF',
            'ABBBBBBBBBBCDEF',
            'ABCCCCCCCCCCDEF',
            'ABCDDDDDDDDDDEF',
            'ABCDEEEEEEEEEEF',
            'ABCDEFFFFFFFFFF',
        ]
        self._staticTest(letters, field_count, expected, dup_num=dup_num)
        self._stringTest(letters, field_count, expected, dup_num=dup_num)

    def testMutationsFieldCount3DupNum2(self):
        letters = 'ABCDEF'
        field_count = 3
        dup_num = 2
        expected = ['AABBCCDEF', 'ABBCCDDEF', 'ABCCDDEEF', 'ABCDDEEFF']
        self._staticTest(letters, field_count, expected, dup_num=dup_num)
        self._stringTest(letters, field_count, expected, dup_num=dup_num)

    def testMutationsFieldCount3DupNum10(self):
        letters = 'ABCDEF'
        field_count = 3
        dup_num = 10
        expected = [
            'AAAAAAAAAABBBBBBBBBBCCCCCCCCCCDEF',
            'ABBBBBBBBBBCCCCCCCCCCDDDDDDDDDDEF',
            'ABCCCCCCCCCCDDDDDDDDDDEEEEEEEEEEF',
            'ABCDDDDDDDDDDEEEEEEEEEEFFFFFFFFFF'
        ]
        self._staticTest(letters, field_count, expected, dup_num=dup_num)
        self._stringTest(letters, field_count, expected, dup_num=dup_num)


class RotateMutatorTests(MutatorTests):

    __meta__ = False

    def setUp(self, cls=RotateMutator):
        super(RotateMutatorTests, self).setUp(cls)

    @metaTest
    def testExceptionRaisedIfFieldCountIs1(self):
        with self.assertRaises(KittyException):
            self.get_uut(field_count=1, fields=[Static('A')])

    def testMutationsFieldCount2(self):
        letters = 'ABCDEF'
        field_count = 2
        expected = ['BACDEF', 'ACBDEF', 'ABDCEF', 'ABCEDF', 'ABCDFE']
        self._staticTest(letters, field_count, expected)
        self._stringTest(letters, field_count, expected)

    def testMutationsFieldCount3(self):
        letters = 'ABCDEF'
        field_count = 3
        expected = ['BCADEF', 'CABDEF', 'ACDBEF', 'ADBCEF', 'ABDECF', 'ABECDF', 'ABCEFD', 'ABCFDE']
        self._staticTest(letters, field_count, expected)
        self._stringTest(letters, field_count, expected)

    def testMutationsFieldCount6(self):
        letters = 'ABCDEF'
        field_count = 6
        expected = ['BCDEFA', 'CDEFAB', 'DEFABC', 'EFABCD', 'FABCDE']
        self._staticTest(letters, field_count, expected)
        self._stringTest(letters, field_count, expected)


class OmitMutatorTests(MutatorTests):

    __meta__ = False

    def setUp(self, cls=OmitMutator):
        super(OmitMutatorTests, self).setUp(cls)

    def testMutationsFieldCount1(self):
        letters = 'ABCDEF'
        field_count = 1
        expected = ['BCDEF', 'ACDEF', 'ABDEF', 'ABCEF', 'ABCDF', 'ABCDE']
        self._staticTest(letters, field_count, expected)
        self._stringTest(letters, field_count, expected)

    def testMutationsFieldCount2(self):
        letters = 'ABCDEF'
        field_count = 2
        expected = ['CDEF', 'ADEF', 'ABEF', 'ABCF', 'ABCD']
        self._staticTest(letters, field_count, expected)
        self._stringTest(letters, field_count, expected)

    def testMutationsFieldCount4(self):
        letters = 'ABCDEF'
        field_count = 4
        expected = ['EF', 'AF', 'AB']
        self._staticTest(letters, field_count, expected)
        self._stringTest(letters, field_count, expected)


class ListTests(BaseTestCase):

    __meta__ = False

    def setUp(self, cls=List):
        super(ListTests, self).setUp(cls)
        self.uut_name = 'uut'

    def get_uut(self, fields=None, delim=None, fuzzable=True):
        if fields is None:
            fields = self.get_default_fields()
        return self.cls(name=self.uut_name, fields=fields, delim=delim, fuzzable=fuzzable)

    def get_default_fields(self):
        return [
            Static(name='string A', value='A'),
            String(name='string B', value='B'),
            String(name='string C', value='C'),
        ]

    def testNoExceptionsInMutateRenderLoop(self):
        uut = self.get_uut()
        uut.render()
        while uut.mutate():
            uut.render()

    def testContainsAllDefaultMutations(self):
        fields = [String('a'), Container([Static('A'), String('B')])]
        default_container = Container(fields=fields)
        default_mutations = self.get_all_mutations(default_container)
        uut = self.get_uut(fields)
        uut_mutations = self.get_all_mutations(uut)
        for mutation in default_mutations:
            self.assertIn(mutation, uut_mutations)

    def testDefaultValueWhenNotFuzzable(self):
        fields = [String('a'), Container([Static('A'), String('B')])]
        default_container = Container(fields=fields, fuzzable=False)
        default_rendered = default_container.render()
        uut = self.get_uut(fields, fuzzable=False)
        uut_rendered = uut.render()
        self.assertEqual(default_rendered, uut_rendered)

    def testDefaultValueWhenFuzzableBeforeMutation(self):
        fields = [String('a'), Container([Static('A'), String('B')])]
        default_container = Container(fields=fields, fuzzable=False)
        default_rendered = default_container.render()
        uut = self.get_uut(fields, fuzzable=True)
        uut_rendered = uut.render()
        self.assertEqual(default_rendered, uut_rendered)

    def testDefaultValueWhenFuzzableAfterReset(self):
        fields = [String('a'), Container([Static('A'), String('B')])]
        default_container = Container(fields=fields, fuzzable=False)
        default_rendered = default_container.render()
        uut = self.get_uut(fields, fuzzable=True)
        while uut.mutate():
            pass
        uut.reset()
        uut_rendered = uut.render()
        self.assertEqual(default_rendered, uut_rendered)

    def testDelimiterExist(self):
        num_elems = 3
        fields = [Static('A') for i in range(num_elems)]
        uut = self.get_uut(fields=fields, delim=String('/'))
        mutations = [m.tobytes().decode() for m in self.get_all_mutations(uut)]
        for m in mutations:
            if m != '':
                self.assertEqual(m.count('/'), (len(m) - 1) // 2)

    def testExceptionOnEmptyListFields(self):
        with self.assertRaises(KittyException):
            self.cls(name=self.uut_name, fields=[])

    def testExceptionOnNoneFields(self):
        with self.assertRaises(KittyException):
            self.cls(name=self.uut_name, fields=None)
