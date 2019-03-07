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
Tests for conditions (used by If/IfNot containers)
'''
from common import metaTest, BaseTestCase
from kitty.core import KittyException
from kitty.model import Container, If, Meta
from kitty.model import String, U8, Static
from kitty.model import Condition
from kitty.model import Equal, NotEqual, Greater, GreaterEqual, AtLeast
from kitty.model import Lesser, LesserEqual, AtMost, BitMaskSet, BitMaskNotSet


class ConditionTests(BaseTestCase):

    __meta__ = True
    __cls__ = None

    def setUp(self, cls=None):
        super(ConditionTests, self).setUp(cls)

    @metaTest
    def testApplies(self):
        expected_value = 'Expected'
        value_field = self._get_applies_field()
        condition = self._get_condition(value_field)
        c = Container(
            name='container',
            fields=[
                Meta(value_field),
                If(condition=condition, fields=[
                    Static(expected_value)
                ])
            ])
        rendered = c.render().tobytes()
        self.assertEqual(rendered, expected_value.encode())

    @metaTest
    def testNotApplies(self):
        expected_value = ''
        value_field = self._get_not_applies_field()
        condition = self._get_condition(value_field)
        c = Container(
            name='container',
            fields=[
                Meta(value_field),
                If(condition=condition, fields=[
                    Static('Should not appear')
                ])
            ])
        rendered = c.render().tobytes()
        self.assertEqual(rendered, expected_value.encode())


class CompareTests(ConditionTests):

    __meta__ = True
    __cls__ = Condition
    __comp_type__ = None
    __applied_value__ = None
    __not_applied_value__ = None
    __comp_value__ = None

    def _get_applies_field(self):
        return U8(name='comp_field', value=self.__applied_value__)

    def _get_not_applies_field(self):
        return U8(name='comp_field', value=self.__not_applied_value__)

    def _get_condition(self, field):
        return self.cls(field=field, comp_value=self.__comp_value__)


class EqualTests(CompareTests):
    __meta__ = False
    __applied_value__ = 5
    __not_applied_value__ = 6
    __comp_value__ = 5

    def setUp(self):
        super(ConditionTests, self).setUp(Equal)

    def testStringApplies(self):
        expected_value = 'Expected'
        value_field = String(name='comp_field', value='applies')
        condition = self.cls(field=value_field, comp_value='applies')
        c = Container(
            name='container',
            fields=[
                Meta(value_field),
                If(condition=condition, fields=[
                    Static('Expected')
                ])
            ])
        rendered = c.render().tobytes()
        self.assertEqual(rendered, expected_value.encode())

    def testStringNotApplies(self):
        expected_value = ''
        value_field = String(name='comp_field', value='napplies')
        condition = self.cls(field=value_field, comp_value='applies')
        c = Container(
            name='container',
            fields=[
                Meta(value_field),
                If(condition=condition, fields=[
                    Static('Should not appear')
                ])
            ])
        rendered = c.render().tobytes()
        self.assertEqual(rendered, expected_value.encode())


class NotEqualTests(CompareTests):
    __meta__ = False
    __applied_value__ = 5
    __not_applied_value__ = 4
    __comp_value__ = 4

    def setUp(self):
        super(ConditionTests, self).setUp(NotEqual)

    def testStringApplies(self):
        expected_value = 'Expected'
        value_field = String(name='comp_field', value='napplies')
        condition = self.cls(field=value_field, comp_value='applies')
        c = Container(
            name='container',
            fields=[
                Meta(value_field),
                If(condition=condition, fields=[
                    Static('Expected')
                ])
            ])
        rendered = c.render().tobytes()
        self.assertEqual(rendered, expected_value.encode())

    def testStringNotApplies(self):
        expected_value = ''
        value_field = String(name='comp_field', value='applies')
        condition = self.cls(field=value_field, comp_value='applies')
        c = Container(
            name='container',
            fields=[
                Meta(value_field),
                If(condition=condition, fields=[
                    Static('Should not appear')
                ])
            ])
        rendered = c.render().tobytes()
        self.assertEqual(rendered, expected_value.encode())


class CompareOnlyIntTests(CompareTests):

    __meta__ = True

    @metaTest
    def testExceptionIfStringPassed(self):
        with self.assertRaises(KittyException):
            value_field = String(name='comp_field', value='applies')
            self.cls(field=value_field, comp_value='applies')


class GreaterTests(CompareOnlyIntTests):
    __meta__ = False
    __applied_value__ = 5
    __not_applied_value__ = 3
    __comp_value__ = 3

    def setUp(self):
        super(ConditionTests, self).setUp(Greater)


class GreaterEqualTests(CompareOnlyIntTests):
    __meta__ = False
    __applied_value__ = 5
    __not_applied_value__ = 4
    __comp_value__ = 5

    def setUp(self):
        super(ConditionTests, self).setUp(GreaterEqual)


class AtLeastTests(CompareOnlyIntTests):
    __meta__ = False
    __applied_value__ = 5
    __not_applied_value__ = 4
    __comp_value__ = 5

    def setUp(self):
        super(ConditionTests, self).setUp(AtLeast)


class LesserTests(CompareOnlyIntTests):
    __meta__ = False
    __applied_value__ = 5
    __not_applied_value__ = 6
    __comp_value__ = 6

    def setUp(self):
        super(ConditionTests, self).setUp(Lesser)


class LesserEqualTests(CompareOnlyIntTests):
    __meta__ = False
    __applied_value__ = 5
    __not_applied_value__ = 6
    __comp_value__ = 5

    def setUp(self):
        super(ConditionTests, self).setUp(LesserEqual)


class AtMostTests(CompareOnlyIntTests):
    __meta__ = False
    __applied_value__ = 5
    __not_applied_value__ = 6
    __comp_value__ = 5

    def setUp(self):
        super(ConditionTests, self).setUp(AtMost)


class BitMaskSetTests(CompareOnlyIntTests):
    __meta__ = False
    __applied_value__ = 0xcc
    __not_applied_value__ = 0xf3
    __comp_value__ = 0xc

    def setUp(self):
        super(ConditionTests, self).setUp(BitMaskSet)


class BitMaskNotSetTests(CompareOnlyIntTests):
    __meta__ = False
    __applied_value__ = 0xcc
    __not_applied_value__ = 0x1
    __comp_value__ = 0x3

    def setUp(self):
        super(ConditionTests, self).setUp(BitMaskNotSet)
