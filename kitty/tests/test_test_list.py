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
Tests for test lists
'''
from unittest import TestCase
from kitty.fuzzers.test_list import RangesList
from kitty.core import KittyException


class RangesListTests(TestCase):

    def setUp(self):
        pass

    def _do_tests(self, r, expected_list):
        first_list = []
        while True:
            current = r.current()
            if current is None:
                break
            first_list.append(current)
            r.next()
        self.assertListEqual(first_list, expected_list)
        self.assertListEqual(first_list, sorted(first_list))
        after_reset_list = []
        r.reset()
        while True:
            current = r.current()
            if current is None:
                break
            after_reset_list.append(current)
            r.next()
        self.assertListEqual(after_reset_list, first_list)

    def _testSimpleNoLast(self, test_str, expected_list):
        r = RangesList(test_str)
        self._do_tests(r, expected_list)

    def _testSimpleWithLast(self, test_str, expected_list, last):
        r = RangesList(test_str)
        r.set_last(last)
        self._do_tests(r, expected_list)

    def _testException(self, test_str):
        with self.assertRaises(KittyException):
            RangesList(test_str)

    def _testExceptionWithLast(self, test_str, last):
        r = RangesList(test_str)
        with self.assertRaises(KittyException):
            r.set_last(last)

    def testVanillaOneEntrySingleNoLast(self):
        self._testSimpleNoLast('1', [1])

    def testVanillaOneEntrySingleNoLastWithSpaces(self):
        self._testSimpleNoLast(' 1 ', [1])

    def testVanillaOneEntrySingleWithLast(self):
        self._testSimpleWithLast('1', [1], 10)

    def testVanillaOneEntryOpenStartNoLast(self):
        self._testSimpleNoLast('-15', list(range(0, 16)))

    def testVanillaOneEntryOpenStartWithLast(self):
        self._testSimpleWithLast('-15', list(range(0, 16)), 20)

    def testVanillaOneEntryClosedNoLast(self):
        self._testSimpleNoLast('10-15', list(range(10, 16)))

    def testVanillaOneEntryClosedWithLast(self):
        self._testSimpleWithLast('10-15', list(range(10, 16)), 20)

    def testVanillaOneEntryOpenEndWithLast(self):
        self._testSimpleWithLast('15-', list(range(15, 21)), 20)

    def testVanillaMultipleEntries(self):
        s = '-10, 11, 15, 22-28, 37, 98-'
        expected_list = [
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 15,
            22, 23, 24, 25, 26, 27, 28, 37, 98, 99, 100]
        last = 100
        self._testSimpleWithLast(s, expected_list, last)

    def testVanillaMultipleEntriesWithSpaces(self):
        self._testSimpleNoLast(' 1, 2, 3 , 4  ', [1, 2, 3, 4])

    def testVanillaMultipleEntriesSorted(self):
        self._testSimpleNoLast('4,3,2,1', [1, 2, 3, 4])

    def testExceptionOneEntryCharacter(self):
        self._testException('a')

    def testExceptionOneEntrySymbol(self):
        self._testException('~')

    def testExceptionOneEntryDash(self):
        self._testException('-')

    def testExceptionMultipleEntriesCharacter(self):
        self._testException('0,a,1')

    def testExceptionMultipleEntriesSymbol(self):
        self._testException('0,~,1')

    def testExceptionMultipleEntriesDash(self):
        self._testException('0,-,1')

    def testExceptionMultipleEntriesEmpty(self):
        self._testException('0,,1')

    def testExceptionMultipleOpenEnds(self):
        self._testException('0-, 3-')

    def testExceptionMultipleOpenStarts(self):
        self._testException('-5, -10')

    def testExceptionOverlapsSimple(self):
        self._testException('1,1')

    def testExceptionOverlapsRanges(self):
        self._testException('1-3,3-4')

    def testExceptionOverlapsOpenStart(self):
        self._testException('-3,2')

    def testExceptionOverlapsOpenEnd(self):
        self._testException('5-,7')

    def testExceptionLastWithOpenEnd(self):
        self._testExceptionWithLast('5-', 4)

    def testExceptionLastWithoutOpenEnd(self):
        self._testExceptionWithLast('1,2,3', 2)
