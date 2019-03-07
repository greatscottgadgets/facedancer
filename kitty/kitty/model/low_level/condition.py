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
conditon object has one mandatory function - applies, which receives a Container as the single argument.

Conditions are used by the *If* and *IfNot* fields to decide wether to render their content or not.
In many cases the decision is made based on a value of a specific field, but you can create whatever condition you want.
In future versions, they will probably be used to make other decisions, not only basic rendering decisions.
'''
import copy
import six
from kitty.core import KittyException, khash
from kitty.model.low_level.encoder import strToBytes


class Condition(object):

    def applies(self, container, ctx):
        '''
        All subclasses must implement the `applies(self, container)` method

        :type container: Container
        :param container: the caller
        :param ctx: rendering context in which applies was called
        :return: True if condition applies, False otherwise
        '''
        raise NotImplementedError('applies')

    def hash(self):
        '''
        :rtype: int
        :return: hash of the condition
        '''
        return khash(type(self).__name__)

    def copy(self):
        '''
        :return: a copy of the condition
        '''
        return copy.copy(self)

    def invalidate(self, container):
        '''
        :param container: the container that tries to invalidate the condition
        '''
        pass


class FieldCondition(Condition):
    '''
    Base class for field-based conditions (if field meets condition return true)
    '''

    def __init__(self, field):
        '''
        :type field: :class:`~kitty.model.low_level.field.BaseField` or ``str``
        :param field: (name of, or) field that should meet the condition
        '''
        super(FieldCondition, self).__init__()
        if isinstance(field, str):
            self._field_name = field
            self._field = None
        else:
            self._field_name = None
            self._field = field

    def invalidate(self, container):
        '''
        :param container: the container that tries to invalidate the condition
        '''
        self._get_ready(container)
        field_name = self._field.get_name()
        if field_name is None:
            raise KittyException('Cannot invalidate field without name')
        self._field_name = field_name
        self._field = None

    def _get_ready(self, container):
        if not self._field:
            if self._field_name:
                field = container.resolve_field(self._field_name)
                if not field:
                    raise KittyException('failed to resolve field name %s' % self._field_name)
                self._field = field
        if not self._field:
            raise KittyException('No field provided to base the condition on')

    def applies(self, container, ctx):
        '''
        Subclasses should not override `applies`, but instead they should override `_applies`, which has the same syntax as `applies`.
        In the `_applies` method the condition is guaranteed to have a reference to the desired field, as `self._field`.

        :type container: :class:`~kitty.model.low_level.container.Container`
        :param container: the caller
        :param ctx: rendering context in which applies was called
        :return: True if condition applies, False otherwise
        '''
        self._get_ready(container)
        return self._applies(container, ctx)

    def _applies(self, container, ctx):
        raise NotImplementedError('_applies')

    def hash(self):
        hashed = super(FieldCondition, self).hash()
        return khash(hashed, self._field_name)


class ListCondition(FieldCondition):
    '''
    Base class for comparison between field and list. can't be instantiated
    '''

    def __init__(self, field, value_list):
        '''
        :param field: (name of) field that should meet the condition
        :param value_list: list of values that should be compared to the field
        '''
        super(ListCondition, self).__init__(field=field)
        self._value_list = value_list

    def hash(self):
        hashed = super(ListCondition, self).hash()
        return khash(hashed, len(self._value_list), frozenset(self._value_list))


class InList(ListCondition):
    '''
    Condition applies if the value of the field appears in the value list

    :example:

        Render the content of the `If` container only if the current
        rendered value of the 'numbers' field is '1', '5' or '7'.

        ::

            Template([
                Group(['1', '2', '3'], name='numbers'),
                If(InList('numbers', ['1', '5', '7']), [
                    String('123')
                ])
            ])
    '''

    def _applies(self, container, ctx):
        value = self._field._current_value
        return value in self._value_list


class FieldMutating(FieldCondition):
    '''
    Condition applies if the field is currently mutating

    :example:

        Render the content of the `If` container only if 'kittyfield'
        is currently mutating.

        ::

            Template([
                String('kitty', name='kittyfield'),
                String('fritty', name='frittyfield'),
                If(FieldMutating('kittyfield'), [
                    String('kitty is now mutating')
                ])
            ])
    '''

    def _applies(self, container):
        return self._field._mutating


class Compare(FieldCondition):
    '''
    Condition applies if the comparison between the value of the field and the comp_value evaluates to True

    .. note:: There are some functions for creating specific `Compare` conditions that you can see below.
    '''

    _comparison_types = {
        '>': lambda x, y: x > y,
        '<': lambda x, y: x < y,
        '>=': lambda x, y: x >= y,
        '<=': lambda x, y: x <= y,
        '==': lambda x, y: x == y,
        '!=': lambda x, y: x != y,
        '&': lambda x, y: (x & y) == y,
        '&=0': lambda x, y: (x & y) == 0,
    }

    def __init__(self, field, comp_type, comp_value):
        '''
        :param field: (name of) field that should meet the condition
        :param comp_type: how to compare the values. One of ('>', '<', '>=', '<=', '==', '!=')
        :param comp_value: value to compare the field to

        :example:

            Render the content of the `If` container only if the value
            in the field called "name" is not 'kitty'

            ::

                Template([
                    String('kitty', name='name'),
                    If(Compare('name', '!=', 'kitty'), [
                        String('current name is not kitty')
                    ])
                ])
        '''
        super(Compare, self).__init__(field=field)
        self._comp_type = comp_type
        if comp_type in Compare._comparison_types:
            if comp_type not in ['==', '!='] and isinstance(comp_value, str):
                raise KittyException('can\'t use comparison type "%s" with comparison value of type str' % comp_type)
            self._comp_fn = Compare._comparison_types[comp_type]
        else:
            raise KittyException('unknown comparison type (%s)' % (comp_type))
        if isinstance(comp_value, six.string_types):
            comp_value = strToBytes(comp_value)
        self._comp_value = comp_value

    def _applies(self, container, ctx):
        value = self._field._current_value
        return self._comp_fn(value, self._comp_value)

    def hash(self):
        '''
        :rtype: int
        :return: hash of the condition
        '''
        hashed = super(Compare, self).hash()
        return khash(hashed, self._comp_value, self._comp_type)
