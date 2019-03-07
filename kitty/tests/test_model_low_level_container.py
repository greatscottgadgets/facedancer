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
Tests for low level fields
'''
from struct import unpack
from bitstring import Bits
from common import metaTest, BaseTestCase
from kitty.model.low_level import String, Static, Group, BE32
from kitty.model.low_level.container import Container, ForEach, If, IfNot, Repeat, Template, Switch
from kitty.model.low_level.container import Meta, Pad, Trunc, PseudoTemplate, OneOf, TakeFrom
from kitty.model.low_level.condition import Condition
from kitty.model.low_level.aliases import Equal, NotEqual
from kitty.core import KittyException


class ContainerTest(BaseTestCase):

    __meta__ = True

    def setUp(self, cls=Container):
        super(ContainerTest, self).setUp(cls)
        self.uut_name = 'uut'

    def get_default_container(self, fields=[], fuzzable=True):
        return self.cls(fields=fields, fuzzable=fuzzable, name=self.uut_name)

    def _test_fields(self, init_fields=[], push_fields=[]):
        all_fields = init_fields + push_fields
        container = self.get_default_container(fields=init_fields, fuzzable=True)
        for f in push_fields:
            container.push(f)
            if isinstance(f, Container):
                # default is to pop the container immediatly in the tests...
                container.pop()
        fields_num_mutations = sum(f.num_mutations() for f in all_fields)
        container_num_mutations = container.num_mutations()
        self.assertEqual(fields_num_mutations, container_num_mutations)

        field_default_values = []
        for f in all_fields:
            field_default_values.append(f.render())
        fields_mutations = []
        for i, field in enumerate(all_fields):
            prefix = sum(field_default_values[:i])
            postfix = sum(field_default_values[i + 1:])
            if prefix == 0:
                prefix = Bits()
            if postfix == 0:
                postfix = Bits()
            while field.mutate():
                fields_mutations.append(prefix + field.render() + postfix)
            field.reset()
        container_mutations = self.get_all_mutations(container)
        self.assertListEqual(fields_mutations, container_mutations)

    @metaTest
    def testPrimitivesInit1(self):
        fields = [String('test_%d' % d) for d in range(1)]
        self._test_fields(init_fields=fields)

    @metaTest
    def testPrimitivesInit2(self):
        fields = [String('test_%d' % d) for d in range(2)]
        self._test_fields(init_fields=fields)

    @metaTest
    def testPrimitivesInit5(self):
        fields = [String('test_%d' % d) for d in range(5)]
        self._test_fields(init_fields=fields)

    @metaTest
    def testPrimitivesPush1(self):
        fields = [String('test_%d' % d) for d in range(1)]
        self._test_fields(push_fields=fields)

    @metaTest
    def testPrimitivesPush2(self):
        fields = [String('test_%d' % d) for d in range(2)]
        self._test_fields(push_fields=fields)

    @metaTest
    def testPrimitivesPush5(self):
        fields = [String('test_%d' % d) for d in range(5)]
        self._test_fields(push_fields=fields)

    @metaTest
    def testPrimitivesInit1Push1(self):
        init_fields = [
            String('test1'),
        ]
        push_fields = [
            String('test2'),
        ]
        self._test_fields(init_fields=init_fields, push_fields=push_fields)

    @metaTest
    def testPrimitivesInit2Push2(self):
        init_fields = [
            String('test11'),
            String('test12'),
        ]
        push_fields = [
            String('test21'),
            String('test22'),
        ]
        self._test_fields(init_fields=init_fields, push_fields=push_fields)

    @metaTest
    def testContainersInit1(self):
        containers = [Container(fields=[String('test_%d' % d)]) for d in range(1)]
        self._test_fields(init_fields=containers)

    @metaTest
    def testContainersInit2(self):
        containers = [Container(fields=[String('test_%d' % d)]) for d in range(2)]
        self._test_fields(init_fields=containers)

    @metaTest
    def testContainersInit5(self):
        containers = [Container(fields=[String('test_%d' % d)]) for d in range(5)]
        self._test_fields(init_fields=containers)

    @metaTest
    def testContainersPush1(self):
        containers = [Container(fields=[String('test_%d' % d)]) for d in range(1)]
        self._test_fields(push_fields=containers)

    @metaTest
    def testContainersPush2(self):
        containers = [Container(fields=[String('test_%d' % d)]) for d in range(2)]
        self._test_fields(push_fields=containers)

    @metaTest
    def testContainersPush5(self):
        containers = [Container(fields=[String('test_%d' % d)]) for d in range(5)]
        self._test_fields(push_fields=containers)

    @metaTest
    def testContainersInit1Push1(self):
        init_containers = [Container(fields=[String('test_init_%d' % d)]) for d in range(1)]
        push_containers = [Container(fields=[String('test_push_%d' % d)]) for d in range(1)]
        self._test_fields(init_fields=init_containers, push_fields=push_containers)

    @metaTest
    def testContainersInit2Push2(self):
        init_containers = [Container(fields=[String('test_init_%d' % d)]) for d in range(2)]
        push_containers = [Container(fields=[String('test_push_%d' % d)]) for d in range(2)]
        self._test_fields(init_fields=init_containers, push_fields=push_containers)

    def _test_not_fuzzable(self, fields):
        container = self.get_default_container(fields=fields, fuzzable=False)
        self.assertEqual(container.num_mutations(), 0)
        rendered = container.render()
        for _ in range(10):
            self.assertFalse(container.mutate())
            self.assertEqual(container.render(), rendered)
        container.reset()
        for _ in range(10):
            self.assertFalse(container.mutate())
            self.assertEqual(container.render(), rendered)

    @metaTest
    def testNotFuzzable1(self):
        fields = [String('test_%d' % d) for d in range(1)]
        self._test_not_fuzzable(fields)

    @metaTest
    def testNotFuzzable2(self):
        fields = [String('test_%d' % d) for d in range(2)]
        self._test_not_fuzzable(fields)

    @metaTest
    def testNotFuzzable5(self):
        fields = [String('test_%d' % d) for d in range(5)]
        self._test_not_fuzzable(fields)

    @metaTest
    def testHashTheSameForTwoSimilarObjects(self):
        container1 = self.get_default_container(fields=[String('test_string')])
        container2 = self.get_default_container(fields=[String('test_string')])
        self.assertEqual(container1.hash(), container2.hash())

    @metaTest
    def testHashTheSameAfterReset(self):
        container = self.get_default_container(fields=[String('test_string')])
        hash_after_creation = container.hash()
        container.mutate()
        hash_after_mutate = container.hash()
        self.assertEqual(hash_after_creation, hash_after_mutate)
        container.reset()
        hash_after_reset = container.hash()
        self.assertEqual(hash_after_creation, hash_after_reset)
        while container.mutate():
            hash_after_mutate_all = container.hash()
            self.assertEqual(hash_after_creation, hash_after_mutate_all)
            container.render()
            hash_after_render_all = container.hash()
            self.assertEqual(hash_after_creation, hash_after_render_all)

    @metaTest
    def testGetRenderedFieldsCorrect(self):
        fields = [
            String('test_string', name='field1'),
            If(Equal('test_group_5', 'A'), String('if', name='if_field3'), name='if2'),
            IfNot(Equal('test_group_5', 'A'), String('ifnot', name='ifnot_field5'), name='ifnot4'),
            Group(name='test_group_5', values=['A', 'B', 'C'])
        ]
        container = self.get_default_container(fields)
        expected_list = list(filter(lambda x: len(x.render()), fields))
        if len(container.render()):
            self.assertListEqual(container.get_rendered_fields(), expected_list)
        else:
            self.assertListEqual(container.get_rendered_fields(), [])
        while container.mutate():
            expected_list = list(filter(lambda x: len(x.render()), fields))
            if len(container.render()):
                self.assertEqual(container.get_rendered_fields(), expected_list)
            else:
                self.assertEqual(container.get_rendered_fields(), [])

    @metaTest
    def testCopy(self):
        fields = [
            String('test_string', name='field1'),
            If(Equal('test_group_5', 'A'), String('if', name='if_field3'), name='if2'),
            IfNot(Equal('test_group_5', 'A'), String('ifnot', name='ifnot_field5'), name='ifnot4'),
            Group(name='test_group_5', values=['A', 'B', 'C'])
        ]
        uut = self.get_default_container(fields)
        uut_copy = uut.copy()
        uut_mutations = self.get_all_mutations(uut, reset=False)
        copy_mutations = self.get_all_mutations(uut_copy, reset=False)
        self.assertEqual(uut_mutations, copy_mutations)

    @metaTest
    def testExceptionWhenRenderedContainedFieldIsNotBitsDefaultRender(self):
        class BadString(String):
            def render(self, ctx=None):
                return self._current_value

            def _initialize_default_buffer(self):
                super(BadString, self)._initialize_default_buffer()
                return self._current_value
        fields = [BadString('hello')]
        uut = self.get_default_container(fields)
        with self.assertRaises(KittyException):
            uut.render()

    @metaTest
    def testExceptionWhenRenderedContainedFieldIsNotBitsMutatedRender(self):
        class BadString(String):
            def render(self, ctx=None):
                return self._current_value
        fields = [BadString('hello')]
        uut = self.get_default_container(fields)
        with self.assertRaises(KittyException):
            uut.mutate()
            uut.render()

    @metaTest
    def testExceptionIfTwoFieldsHasTheSameName(self):
        field1 = String(name='A', value='A')
        field2 = String(name='A', value='B')
        with self.assertRaises(KittyException):
            Container(fields=[field1, field2])


class RealContainerTest(ContainerTest):

    __meta__ = False


class ConditionTest(ContainerTest):

    __meta__ = True
    condition_field_name = 'condition field'
    condition_field_value = 'condition value'
    inner_field_value = 'inner'

    def setUp(self, cls=None):
        super(ConditionTest, self).setUp(cls)

    class AlwaysTrue(Condition):
        def applies(self, container, ctx=None):
            return True

    class AlwaysFalse(Condition):
        def applies(self, container, ctx=None):
            return False

    def get_default_container(self, fields=[], fuzzable=True):
        return self.cls(condition=self.get_applies_always_condition(), fields=fields, fuzzable=fuzzable, name=self.uut_name)

    def get_applies_first_condition(self):
        return None

    def get_not_applies_first_condition(self):
        return None

    def get_applies_always_condition(self):
        return None

    def get_not_applies_always_condition(self):
        return None

    def get_condition_field(self):
        return String(name=ConditionTest.condition_field_name, value=ConditionTest.condition_field_value)

    @metaTest
    def testlways(self):
        field = self.get_condition_field()
        condition = self.get_not_applies_always_condition()
        condition_container = self.cls(condition=condition, fields=[String(ConditionTest.inner_field_value)], fuzzable=True)
        # This is done to allow field name resolution
        enclosing = Container(fields=[field, condition_container])
        rendered = condition_container.render()
        self.assertEqual(rendered, Bits())
        while condition_container.mutate():
            rendered = condition_container.render()
            self.assertEqual(rendered, Bits())
        del enclosing

    @metaTest
    def testConditionAppliesFirst(self):
        field = self.get_condition_field()
        condition = self.get_applies_first_condition()
        inner_field = String(ConditionTest.inner_field_value)
        condition_container = self.cls(condition=condition, fields=[inner_field], fuzzable=True)
        # This is done to allow field name resolution
        enclosing = Container(fields=[field, condition_container])
        self.assertEqual(condition_container.render(), inner_field.render())
        while condition_container.mutate():
            self.assertEqual(condition_container.render(), inner_field.render())

        condition_container.reset()
        field.mutate()
        self.assertEqual(condition_container.render(), Bits())
        while condition_container.mutate():
            self.assertEqual(condition_container.render(), Bits())

        del enclosing

    @metaTest
    def testConditionNotAppliesFirst(self):
        field = self.get_condition_field()
        condition = self.get_not_applies_first_condition()
        inner_field = String(ConditionTest.inner_field_value)
        condition_container = self.cls(condition=condition, fields=[inner_field], fuzzable=True)
        # This is done to allow field name resolution
        enclosing = Container(fields=[field, condition_container])
        self.assertEqual(condition_container.render(), Bits())
        while condition_container.mutate():
            self.assertEqual(condition_container.render(), Bits())

        condition_container.reset()
        field.mutate()
        self.assertEqual(condition_container.render(), inner_field.render())
        while condition_container.mutate():
            self.assertEqual(condition_container.render(), inner_field.render())

        del enclosing


class IfTest(ConditionTest):

    __meta__ = False

    def setUp(self, cls=If):
        super(IfTest, self).setUp(cls)

    def get_applies_first_condition(self):
        return Equal(ConditionTest.condition_field_name, ConditionTest.condition_field_value)

    def get_not_applies_first_condition(self):
        return NotEqual(ConditionTest.condition_field_name, ConditionTest.condition_field_value)

    def get_applies_always_condition(self):
        return ConditionTest.AlwaysTrue()

    def get_not_applies_always_condition(self):
        return ConditionTest.AlwaysFalse()


class IfNotTest(ConditionTest):

    __meta__ = False

    def setUp(self, cls=IfNot):
        super(IfNotTest, self).setUp(cls)

    def get_applies_first_condition(self):
        return NotEqual(ConditionTest.condition_field_name, ConditionTest.condition_field_value)

    def get_not_applies_first_condition(self):
        return Equal(ConditionTest.condition_field_name, ConditionTest.condition_field_value)

    def get_applies_always_condition(self):
        return ConditionTest.AlwaysFalse()

    def get_not_applies_always_condition(self):
        return ConditionTest.AlwaysTrue()


class OneOfTests(ContainerTest):
    __meta__ = False

    def setUp(self, cls=OneOf):
        super(OneOfTests, self).setUp(cls)

    def get_default_container(self, fields=[], fuzzable=True, mutated_field=None):
        if mutated_field is None:
            mutated_field = String('static field')
        return OneOf(fields=fields, fuzzable=fuzzable, name=self.uut_name)

    def _test_fields(self, init_fields=[], push_fields=[]):
        all_fields = init_fields + push_fields
        container = self.get_default_container(fields=init_fields, fuzzable=True)
        for f in push_fields:
            container.push(f)
            if isinstance(f, Container):
                # default is to pop the container immediatly in the tests...
                container.pop()
        fields_num_mutations = sum(f.num_mutations() for f in all_fields) + len(all_fields)
        container_num_mutations = container.num_mutations()
        self.assertEqual(fields_num_mutations, container_num_mutations)

    def testGetRenderedFieldsCorrect(self):
        fields = [
            String('test_string', name='field1'),
            If(Equal('test_group_5', 'A'), String('if', name='if_field3'), name='if2'),
            IfNot(Equal('test_group_5', 'A'), String('ifnot', name='ifnot_field5'), name='ifnot4'),
            Group(name='test_group_5', values=['A', 'B', 'C'])
        ]
        container = self.get_default_container(fields)
        if len(container.render()):
            self.assertEqual(len(container.get_rendered_fields()), 1)
        while container.mutate():
            if len(container.render()):
                self.assertEqual(len(container.get_rendered_fields()), 1)
            else:
                self.assertEqual(len(container.get_rendered_fields()), 0)


class ForEachTest(ContainerTest):

    __meta__ = False

    def setUp(self, cls=ForEach):
        super(ForEachTest, self).setUp(cls)

    def get_default_container(self, fields=[], fuzzable=True, mutated_field=None):
        if mutated_field is None:
            mutated_field = Static('static field')
        return ForEach(mutated_field=mutated_field, fields=fields, fuzzable=fuzzable, name=self.uut_name)

    def _test_basic(self, mutated, field):
        container = ForEach(mutated_field=mutated, fields=[field])
        expected_num_mutations = mutated.num_mutations() * field.num_mutations()
        container_num_mutations = container.num_mutations()
        self.assertEqual(container_num_mutations, expected_num_mutations)
        fields_mutations = self.get_all_mutations(field)
        container_mutations = self.get_all_mutations(container)
        self.assertListEqual(container_mutations, fields_mutations * mutated.num_mutations())

    def _test_mutating_mutated(self, mutated, field):
        foreach = ForEach(mutated_field=mutated, fields=[field])
        container = Container(fields=[mutated, foreach])
        expected_num_mutations = mutated.num_mutations() * field.num_mutations() + mutated.num_mutations()
        container_num_mutations = container.num_mutations()
        self.assertEqual(container_num_mutations, expected_num_mutations)
        mutated_mutations = self.get_all_mutations(mutated)
        fields_mutations = self.get_all_mutations(field)
        expected_mutations = []
        for mutation in mutated_mutations:
            expected_mutations.append(mutation + field.render())
        for gmutation in mutated_mutations:
            for fmutation in fields_mutations:
                expected_mutations.append(gmutation + fmutation)
        container_mutations = self.get_all_mutations(container)
        self.assertListEqual(container_mutations, expected_mutations)

    def testGroupGroup(self):
        mutated = Group(values=['1', '2', '3'])
        field = Group(values=['a', 'b', 'c'])
        self._test_basic(mutated, field)

    def testGroupGroupMutatingMutatedField(self):
        mutated = Group(values=['1', '2', '3'])
        field = Group(values=['a', 'b', 'c'])
        self._test_mutating_mutated(mutated, field)

    def testGroupString(self):
        mutated = Group(values=['1', '2', '3'])
        field = String('best', max_size=10)
        self._test_basic(mutated, field)

    def testGroupStringMutatingMutatedField(self):
        mutated = Group(values=['1', '2', '3'])
        field = String('best')
        self._test_mutating_mutated(mutated, field)

    def testStringString(self):
        mutated = String('test', max_size=10)
        field = String('best', max_size=10)
        self._test_basic(mutated, field)

    def testStringStringMutatingMutatedField(self):
        mutated = String('test', max_size=10)
        field = String('best', max_size=10)
        self._test_mutating_mutated(mutated, field)

    def testStringGroup(self):
        mutated = String('test', max_size=10)
        field = Group(values=['a', 'b', 'c'])
        self._test_basic(mutated, field)

    def testStringGroupMutatingMutatedField(self):
        mutated = String('test', max_size=10)
        field = Group(values=['a', 'b', 'c'])
        self._test_mutating_mutated(mutated, field)


class RepeatTest(ContainerTest):

    __meta__ = False

    def setUp(self, cls=Repeat):
        super(RepeatTest, self).setUp(cls)

    def get_default_container(self, fields=[], fuzzable=True):
        return Repeat(fields=fields, fuzzable=fuzzable, name=self.uut_name)

    def _test_mutations(self, repeater, fields, min_times=1, max_times=1, step=1):
        repeats = max_times - min_times // step
        expected_num_mutations = sum(f.num_mutations() for f in fields) + repeats
        repeater_num_mutations = repeater.num_mutations()
        self.assertEqual(repeater_num_mutations, expected_num_mutations)

        field_default_values = [field.render() for field in fields]
        fields_mutations = []
        for i in range(min_times, max_times, step):
            fields_mutations.append(sum(field_default_values) * i)
        for j, field in enumerate(fields):
            prefix = sum(field_default_values[:j])
            postfix = sum(field_default_values[j + 1:])
            if prefix == 0:
                prefix = Bits()
            if postfix == 0:
                postfix = Bits()
            while field.mutate():
                fields_mutations.append((prefix + field.render() + postfix) * min_times)
            field.reset()
        repeater.reset()
        repeater_mutations = self.get_all_mutations(repeater)
        self.assertListEqual(fields_mutations, repeater_mutations)

    def testRepeatSingleMaxTimes1(self):
        max_times = 1
        fields = [
            String('field1')
        ]
        repeater = Repeat(fields=fields, max_times=max_times)
        self._test_mutations(repeater, fields, max_times=max_times)

    def testRepeatSingleMaxTimes5(self):
        max_times = 5
        fields = [
            String('field1')
        ]
        repeater = Repeat(fields=fields, max_times=max_times)
        self._test_mutations(repeater, fields, max_times=max_times)


class MetaTest(BaseTestCase):

    def setUp(self):
        super(MetaTest, self).setUp(Meta)
        self.uut_name = 'uut'

    def testIsFuzzable(self):
        field = String('abc')
        uut = Meta(name=self.uut_name, fields=[field], fuzzable=True)
        num_mutations = uut.num_mutations()
        self.assertGreater(num_mutations, 0)
        self.assertGreaterEqual(num_mutations, field.num_mutations())
        actual_num_mutations = 0
        while uut.mutate():
            actual_num_mutations += 1
        self.assertEqual(actual_num_mutations, num_mutations)

    def testIsNotRenderedWhenFuzzable(self):
        field = String('abc')
        uut = Meta(name=self.uut_name, fields=[field], fuzzable=True)
        while uut.mutate():
            self.assertEqual(len(uut.render()), 0)

    def testIsNotFuzzable(self):
        field = String('abc')
        uut = Meta(name=self.uut_name, fields=[field], fuzzable=False)
        self.assertEqual(uut.num_mutations(), 0)
        self.assertFalse(uut.mutate())

    def testIsNotRenderedWhenNotFuzzable(self):
        field = String('abc')
        uut = Meta(name=self.uut_name, fields=[field], fuzzable=False)
        self.assertEqual(len(uut.render()), 0)

    def testAlwaysRenderedAsEmptyBits(self):
        field = String('abc')
        uut = Meta(name=self.uut_name, fields=[field], fuzzable=True)
        self.assertEqual(len(uut.render()), 0)
        while uut.mutate():
            self.assertEqual(len(uut.render()), 0)
        uut.reset()
        self.assertEqual(len(uut.render()), 0)
        while uut.mutate():
            self.assertEqual(len(uut.render()), 0)


class PadTest(BaseTestCase):

    __meta__ = False

    def setUp(self, cls=Pad):
        super(PadTest, self).setUp(cls)
        self.pad_length = 10 * 8
        self.uut_name = 'uut'

    def _testValuePadded(self, field, uut, pad_length, pad_data):
        fdata = field.render()
        udata = uut.render()
        actual_pad_len = max(0, pad_length - len(fdata))
        expected_padding = Bits(bytes=pad_data * (actual_pad_len // 8 + 1))[:actual_pad_len]
        self.assertEqual(fdata, udata[:len(fdata)])
        self.assertEqual(expected_padding, udata[len(fdata):])

    def testPadWhenFuzzable(self):
        field = String(name='padded', value='abc')
        uut = Pad(self.pad_length, fields=field, name=self.uut_name)
        self._testValuePadded(field, uut, self.pad_length, b'\x00')
        while uut.mutate():
            self._testValuePadded(field, uut, self.pad_length, b'\x00')

    def testPadWhenNotFuzzable(self):
        field = String(name='padded', value='abc')
        uut = Pad(self.pad_length, fields=field, name=self.uut_name, fuzzable=False)
        self._testValuePadded(field, uut, self.pad_length, b'\x00')

    def testNumMutations(self):
        field = String(name='padded', value='abc')
        uut = Pad(self.pad_length, fields=field, name=self.uut_name)
        field_num_mutations = field.num_mutations()
        uut_num_mutations = uut.num_mutations()
        self.assertEqual(uut_num_mutations, field_num_mutations)
        self.assertGreater(uut_num_mutations, 0)
        actual_num_mutations = 0
        while uut.mutate():
            actual_num_mutations += 1
        self.assertEqual(actual_num_mutations, uut_num_mutations)

    def testFixedWithPad(self):
        data = 'abcd'
        expected = Bits(bytes=b'abcd\xff\xff\xff\xff\xff\xff')
        uut = Pad(pad_length=10 * 8, fields=Static(data), pad_data=b'\xff')
        uut_num_mutations = uut.num_mutations()
        self.assertEqual(uut_num_mutations, 0)
        actual_num_mutations = 0
        while uut.mutate():
            actual_num_mutations += 1
        self.assertEqual(actual_num_mutations, uut_num_mutations)
        self.assertEqual(uut.render(), expected)

    def testFixedWithoutPad(self):
        data = 'abcdefghijklmnop'
        expected = Bits(bytes=data.encode())
        uut = Pad(pad_length=10 * 8, fields=Static(data), pad_data=b'\xff')
        uut_num_mutations = uut.num_mutations()
        self.assertEqual(uut_num_mutations, 0)
        actual_num_mutations = 0
        while uut.mutate():
            actual_num_mutations += 1
        self.assertEqual(actual_num_mutations, uut_num_mutations)
        self.assertEqual(uut.render(), expected)

    def testHashTheSameForTwoSimilarObjects(self):
        pad1 = Pad(pad_length=10 * 8, fields=String('abc'), pad_data=b'\xff')
        pad2 = Pad(pad_length=10 * 8, fields=String('abc'), pad_data=b'\xff')
        self.assertEqual(pad1.hash(), pad2.hash())

    def testHashTheSameAfterReset(self):
        container = Pad(pad_length=10 * 8, fields=String('abc'), pad_data=b'\xff')
        hash_after_creation = container.hash()
        container.mutate()
        hash_after_mutate = container.hash()
        self.assertEqual(hash_after_creation, hash_after_mutate)
        container.reset()
        hash_after_reset = container.hash()
        self.assertEqual(hash_after_creation, hash_after_reset)
        while container.mutate():
            hash_after_mutate_all = container.hash()
            self.assertEqual(hash_after_creation, hash_after_mutate_all)
            container.render()
            hash_after_render_all = container.hash()
            self.assertEqual(hash_after_creation, hash_after_render_all)

    def testDifferentHashIfPadLengthIsDifferend(self):
        pad1 = Pad(pad_length=11 * 8, fields=String('abc'), pad_data=b'\xff')
        pad2 = Pad(pad_length=10 * 8, fields=String('abc'), pad_data=b'\xff')
        self.assertNotEqual(pad1.hash(), pad2.hash())

    def testDifferentHashIfPadDataIsDifferend(self):
        pad1 = Pad(pad_length=10 * 8, fields=String('abc'), pad_data=b'\x00')
        pad2 = Pad(pad_length=10 * 8, fields=String('abc'), pad_data=b'\xff')
        self.assertNotEqual(pad1.hash(), pad2.hash())


class TruncTest(BaseTestCase):

    __meta__ = False

    def setUp(self, cls=Trunc):
        super(TruncTest, self).setUp(cls)
        self.trunc_size = 10 * 8
        self.uut_name = 'uut'

    def _testValueTrunced(self, field, uut, trunc_size):
        fdata = field.render()
        udata = uut.render()
        expected_data = fdata[:trunc_size]
        self.assertEqual(expected_data, udata)

    def testValueTruncedNotFuzzable(self):
        field = String(name='trunced', value='abc')
        uut = Trunc(max_size=self.trunc_size, fields=field, fuzzable=False)
        self._testValueTrunced(field, uut, self.trunc_size)
        self.assertEqual(uut.num_mutations(), 0)
        self.assertFalse(uut.mutate())

    def testValueTruncedFuzzable(self):
        field = String(name='trunced', value='abc')
        uut = Trunc(max_size=self.trunc_size, fields=field, fuzzable=True)
        self._testValueTrunced(field, uut, self.trunc_size)
        self.assertEqual(uut.num_mutations(), field.num_mutations())
        self.assertGreater(uut.num_mutations(), 0)
        while uut.mutate():
            self._testValueTrunced(field, uut, self.trunc_size)

    def testNumMutations(self):
        field = String(name='trunced', value='abc')
        uut = Trunc(self.trunc_size, fields=field, name=self.uut_name)
        field_num_mutations = field.num_mutations()
        uut_num_mutations = uut.num_mutations()
        self.assertEqual(uut_num_mutations, field_num_mutations)
        self.assertGreater(uut_num_mutations, 0)
        actual_num_mutations = 0
        while uut.mutate():
            actual_num_mutations += 1
        self.assertEqual(actual_num_mutations, uut_num_mutations)

    def testHashTheSameForTwoSimilarObjects(self):
        trunc1 = Trunc(10 * 8, fields=String('abc'))
        trunc2 = Trunc(10 * 8, fields=String('abc'))
        self.assertEqual(trunc1.hash(), trunc2.hash())

    def testHashTheSameAfterReset(self):
        container = Trunc(10 * 8, fields=String('abc'))
        hash_after_creation = container.hash()
        container.mutate()
        hash_after_mutate = container.hash()
        self.assertEqual(hash_after_creation, hash_after_mutate)
        container.reset()
        hash_after_reset = container.hash()
        self.assertEqual(hash_after_creation, hash_after_reset)
        while container.mutate():
            hash_after_mutate_all = container.hash()
            self.assertEqual(hash_after_creation, hash_after_mutate_all)
            container.render()
            hash_after_render_all = container.hash()
            self.assertEqual(hash_after_creation, hash_after_render_all)

    def testDifferentHashIfPadLengthIsDifferend(self):
        trunc1 = Trunc(11 * 8, fields=String('abc'))
        trunc2 = Trunc(10 * 8, fields=String('abc'))
        self.assertNotEqual(trunc1.hash(), trunc2.hash())


class SwitchTest(BaseTestCase):

    __meta__ = False

    def setUp(self, cls=Switch):
        super(SwitchTest, self).setUp(cls)
        self.uut_name = 'uut'
        self.key_field_name = 'key_field'
        self.key_field_default_value = 0

    def get_uut(self, field_dict=[], default_key=0, fuzzable=True):
        return self.cls(field_dict, self.key_field_name, default_key, name=self.uut_name, fuzzable=fuzzable)

    def get_default_key_field(self, fuzzable=True):
        key_field = BE32(name=self.key_field_name, value=self.key_field_default_value, fuzzable=fuzzable)
        return key_field

    def testNumMutationsMatchesMutateCount(self):
        field_dict = {
            1: String('1'),
            2: String('2'),
            3: String('3'),
        }
        uut = self.get_uut(field_dict, 2)
        key_field = self.get_default_key_field()
        container = Container([uut, key_field])
        num_mutations = uut.num_mutations()
        actual_num_mutations = len(self.get_all_mutations(uut))
        self.assertEqual(num_mutations, actual_num_mutations)
        del container

    def testNumMutationsIsAtLeastSumOfFieldsNumMutations(self):
        field_dict = {
            1: String('1'),
            2: String('2'),
            3: String('3'),
        }
        uut = self.get_uut(field_dict, 2)
        key_field = self.get_default_key_field()
        container = Container([uut, key_field])
        num_mutations = uut.num_mutations()
        actual_num_mutations = sum(v.num_mutations() for k, v in field_dict.items())
        self.assertGreaterEqual(num_mutations, actual_num_mutations)
        del container

    def testZeroMutationsIfNotFuzzable(self):
        field_dict = {
            1: String('1'),
            2: String('2'),
            3: String('3'),
        }
        uut = self.get_uut(field_dict, 2, fuzzable=False)
        key_field = self.get_default_key_field()
        container = Container([uut, key_field])
        num_mutations = uut.num_mutations()
        actual_num_mutations = len(self.get_all_mutations(uut))
        self.assertEqual(num_mutations, actual_num_mutations)
        self.assertEqual(num_mutations, 0)
        del container

    def testSwitchFieldSetByKeyFieldWhenNotMutating(self):
        field_dict = {
            1: String('1'),
            2: String('2'),
            3: String('3'),
        }
        default_key = 2
        uut = self.get_uut(field_dict, default_key)
        key_field = self.get_default_key_field()
        container = Container([uut, key_field])
        while key_field.mutate():
            key = key_field._current_value
            uut_rendered = uut.render()
            uut_key = key if key in field_dict else default_key
            field_rendred = field_dict[uut_key].render()
            self.assertEqual(uut_rendered, field_rendred)
        del container

    def testKeyFieldValueSetBySwitchWhenMutating(self):
        field_dict = {
            1: String('1'),
            2: String('2'),
            3: String('3'),
        }
        uut = self.get_uut(field_dict, 2)
        key_field = self.get_default_key_field()
        container = Container([uut, key_field])
        while uut.mutate():
            key_rendered = key_field.render().tobytes()
            key_value = key_field._current_value
            self.assertEqual(key_value, unpack('>I', key_rendered)[0])
            self.assertEqual(key_value, uut._keys[uut._field_idx])
        del container

    def testContainerRenderingKeyBeforeSwitch(self):
        field_dict = {
            1: Static('\x00\x00\x00\x01'),
            2: Static('\x00\x00\x00\x02'),
            3: Static('\x00\x00\x00\x03'),
        }
        default_key = 2
        uut = self.get_uut(field_dict, default_key)
        key_field = self.get_default_key_field(fuzzable=False)
        container = Container([key_field, uut])
        mutations = self.get_all_mutations(container)
        for mutation in mutations:
            mutation = mutation.tobytes()
            self.assertEqual(len(mutation), 8)
            key = unpack('>I', mutation[:4])[0]
            case = unpack('>I', mutation[4:])[0]
            if key in field_dict:
                self.assertEqual(key, case)
            else:
                self.assertEqual(case, 2)

    def testContainerRenderingKeyAfterSwitch(self):
        field_dict = {
            1: Static('\x00\x00\x00\x01'),
            2: Static('\x00\x00\x00\x02'),
            3: Static('\x00\x00\x00\x03'),
        }
        default_key = 2
        uut = self.get_uut(field_dict, default_key)
        key_field = self.get_default_key_field(fuzzable=False)
        container = Container([uut, key_field])
        mutations = self.get_all_mutations(container)
        for mutation in mutations:
            mutation = mutation.tobytes()
            self.assertEqual(len(mutation), 8)
            key = unpack('>I', mutation[:4])[0]
            case = unpack('>I', mutation[4:])[0]
            if key in field_dict:
                self.assertEqual(key, case)
            else:
                self.assertEqual(case, 2)

    def testSwitchWithStringKey(self):
        field_dict = {
            '1': String('1'),
            '2': String('2'),
            '3': String('3'),
        }
        default_key = '3'
        uut = self.get_uut(field_dict, default_key)
        key_field = String(name=self.key_field_name, value='someval')
        container = Container([uut, key_field])
        while key_field.mutate():
            key = key_field._current_value
            uut_rendered = uut.render()
            uut_key = key if key in field_dict else default_key
            field_rendred = field_dict[uut_key].render()
            self.assertEqual(uut_rendered, field_rendred)
        del container

    def testSwitchWithStaticKeyField(self):
        field_dict = {
            '1': String('1'),
            '2': String('2'),
            '3': String('3'),
        }
        default_key = '3'
        uut = self.get_uut(field_dict, default_key)
        key_field = Static(name=self.key_field_name, value='someval')
        container = Container([uut, key_field])
        while key_field.mutate():
            key = key_field._current_value
            uut_rendered = uut.render()
            uut_key = key if key in field_dict else default_key
            field_rendred = field_dict[uut_key].render()
            self.assertEqual(uut_rendered, field_rendred)
        del container

    def testExceptionIfDefaultKeyNotInDict(self):
        with self.assertRaises(KittyException):
            field_dict = {
                1: String('1'),
                2: String('2'),
                3: String('3'),
            }
            self.get_uut(field_dict, 0)


class TakeFromTest(BaseTestCase):

    __meta__ = False

    def setUp(self):
        super(TakeFromTest, self).setUp(TakeFrom)

    def get_uut(self, fields=None, fuzzable=True):
        return TakeFrom(fields=fields, fuzzable=fuzzable)

    def default_fields(self):
        return [
            String('String1'),
            String('String2'),
            Static('Static1'),
        ]

    def testCopy(self):
        tf1 = self.get_uut(self.default_fields())
        tf2 = tf1.copy()
        tf1_mutations = self.get_all_mutations(tf1, False)
        tf2_mutations = self.get_all_mutations(tf2, False)
        self.assertListEqual(tf1_mutations, tf2_mutations)

    def testNumMutationCorrect(self):
        tf = self.get_uut(self.default_fields())
        self.assertEqual(tf.num_mutations(), len(self.get_all_mutations(tf)))

    def testSameAfterReset(self):
        tf = self.get_uut(self.default_fields())
        before_reset = self.get_all_mutations(tf)
        tf.reset()
        after_reset = self.get_all_mutations(tf)
        self.assertEqual(before_reset, after_reset)


class TemplateTest(ContainerTest):

    __meta__ = False

    def setUp(self, cls=Template):
        super(TemplateTest, self).setUp(cls)
        self.uut_name = 'uut'

    def testCopy(self):
        uut = self.get_default_container()
        with self.assertRaises(KittyException):
            uut.copy()


class PseudoTemplateTest(BaseTestCase):

    __meta__ = False

    def setUp(self):
        super(PseudoTemplateTest, self).setUp(PseudoTemplate)

    def testRendersToEmptyBits(self):
        uut = PseudoTemplate('uut')
        self.assertEqual(uut.render(), Bits())

    def testNotFuzzable(self):
        uut = PseudoTemplate('uut')
        self.assertEqual(uut.num_mutations(), 0)
        self.assertFalse(uut.mutate())

    def testDifferentHashToAllPseudoTemplates(self):
        templates = []
        templates.extend([PseudoTemplate('a') for i in range(1000)])
        templates.extend([PseudoTemplate('b') for i in range(1000)])
        self.assertEqual(len(templates), len(set(templates)))
