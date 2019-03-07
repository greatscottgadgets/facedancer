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
Container mutators treat fields of the container as atomic blocks,
and perform mutations over the collection of the field.

Examples of such mutations are:
    remove fields from the rendered payload
    repeat fields in the rendered payload
    change the order of fields etc.
'''
import itertools
from kitty.model.low_level.field import BaseField
from kitty.model.low_level.container import Container, OneOf
from kitty.model.low_level.encoder import ENC_BITS_DEFAULT
from kitty.core import KittyException


def _intersperse(seq, value):
    res = [value] * (2 * len(seq) - 1)
    res[0::2] = seq
    return res


class FieldRangeMutator(Container):
    '''
    Base class for mutating a field range,
    it should not be instantiated.
    Mutators are intended to be used internally in the framework,
    not in the template declaration directly,
    and as such, they provide empty response when not mutated.
    '''

    def __init__(self, field_count, fields=[], delim=None, encoder=ENC_BITS_DEFAULT, fuzzable=True, name=None):
        '''
        :param field_count: how many fields to omit in each mutation
        :type fields: field or iterable of fields
        :param fields: enclosed field(s) (default: [])
        :type delim: field
        :param delim: delimiter between elements in the list (default: None)
        :type encoder: BitsEncoder
        :param encoder: encoder for the container (default: ENC_BITS_DEFAULT)
        :param fuzzable: is container fuzzable (default: True)
        :param name: (unique) name of the container (default: None)
        '''
        if field_count < 1:
            raise KittyException('field_count (%s) < 1' % (field_count))
        super(FieldRangeMutator, self).__init__(fields=fields, encoder=encoder, fuzzable=fuzzable, name=name)
        self._field_count = field_count
        self._orig_fields = []
        self._delim = delim

    def _init(self):
        self._orig_fields = self._fields
        self._fields = []
        super(FieldRangeMutator, self)._init()

    def _num_stages(self):
        return len(self._orig_fields) - self._field_count + 1

    def _calculate_mutations(self, num):
        self._num_mutations = self._num_stages()

    def _current_field(self):
        return None

    def render(self, ctx=None):
        self._initialize()
        super(FieldRangeMutator, self).render(ctx)
        return self._current_rendered

    def reset(self):
        super(FieldRangeMutator, self).reset()
        self._fields = []

    def is_default(self):
        return not self._mutating()

    def _mutate(self):
        i = self._first_mutated_field_index()
        pre = self._orig_fields[:i]
        post = self._orig_fields[i + self._field_count:]
        current = self._orig_fields[i:i + self._field_count]
        current = self._mutate_fields_in_range(current)
        fields_to_render = pre + current + post
        self._fields = fields_to_render
        if self._delim:
            self._fields = _intersperse(self._fields, self._delim)

    def _mutate_fields_in_range(self, fields):
        return fields

    def _first_mutated_field_index(self):
        return self._current_index


class OmitMutator(FieldRangeMutator):
    '''
    Omit X fields from the final payload

    :example:

            ::

                OmitMutator(field_count=1, fields=[
                    Static('A'),
                    Static('B'),
                    Static('C'),
                    Static('D'),
                ])

            will result in: BCD, ACD, ABD, ABC

    '''

    def _mutate_fields_in_range(self, fields):
        return []


class DuplicateMutator(FieldRangeMutator):
    '''
    Duplicate X fields Y times in the final payload
    '''

    def __init__(self, field_count, dup_num, fields=[], delim=None, encoder=ENC_BITS_DEFAULT, fuzzable=True, name=None):
        '''
        :param field_count: how many (sequential) fields to duplicate
        :param dup_num: how many times to duplicate each of the field
        :type fields: field or iterable of fields
        :param fields: enclosed field(s) (default: [])
        :type delim: field
        :param delim: delimiter between elements in the list (default: None)
        :type encoder: BitsEncoder
        :param encoder: encoder for the container (default: ENC_BITS_DEFAULT)
        :param fuzzable: is container fuzzable (default: True)
        :param name: (unique) name of the container (default: None)

        :example:

            ::

                DuplicateMutator(field_count=2, dup_num=2, fields=[
                    Static('A'),
                    Static('B'),
                    Static('C'),
                    Static('D'),
                ])

            will result in: AABBCD, ABBCCD, ABCCDD
        '''
        super(DuplicateMutator, self).__init__(field_count=field_count, fields=fields, delim=delim, encoder=encoder, fuzzable=fuzzable, name=name)
        self._dup_num = dup_num

    def _mutate_fields_in_range(self, fields):
        res = []
        for f in fields:
            res.extend(itertools.repeat(f, self._dup_num))
        return res


class RotateMutator(FieldRangeMutator):
    '''
    Perform rotation of X fields in the final payload
    '''

    def __init__(self, field_count, fields=[], delim=None, encoder=ENC_BITS_DEFAULT, fuzzable=True, name=None):
        '''
        :param field_count: how many fields to omit in each mutation
        :type fields: field or iterable of fields
        :param fields: enclosed field(s) (default: [])
        :type delim: field
        :param delim: delimiter between elements in the list (default: None)
        :type encoder: BitsEncoder
        :param encoder: encoder for the container (default: ENC_BITS_DEFAULT)
        :param fuzzable: is container fuzzable (default: True)
        :param name: (unique) name of the container (default: None)

        :example:

            ::

                RotateMutator(field_count=3, fields=[
                    Static('A'),
                    Static('B'),
                    Static('C'),
                    Static('D'),
                ])

            will result in: BCAD, CABD, ACDB, ADBC
        '''
        if field_count < 2:
            raise KittyException('field_count (%s) < 2' % (field_count))
        super(RotateMutator, self).__init__(field_count=field_count, fields=fields, delim=delim, encoder=encoder, fuzzable=fuzzable, name=name)

    def _calculate_mutations(self, num):
        self._num_mutations = self._num_stages() * (self._field_count - 1)

    def _mutate_fields_in_range(self, fields):
        rot_count = (self._current_index % (self._field_count - 1)) + 1
        return fields[rot_count:] + fields[:rot_count]

    def _first_mutated_field_index(self):
        return self._current_index // (self._field_count - 1)


class List(OneOf):
    '''
    Describe a list of elements in the template.
    In addition to the standard mutations of its element,
    a List also performs mutation of full elements,
    by reordering, duplicating and omitting them.
    '''

    def __init__(self, fields, delim=None, encoder=ENC_BITS_DEFAULT, fuzzable=True, name=None):
        '''
        :type fields: field or iterable of fields
        :param fields: enclosed field(s)
        :type delim: field
        :param delim: delimiter between elements in the list (default: None)
        :type encoder: BitsEncoder
        :param encoder: encoder for the container (default: ENC_BITS_DEFAULT)
        :param fuzzable: is container fuzzable (default: True)
        :param name: (unique) name of the container (default: None)

        .. note::

            Due to the nature of class, fields should not be added using .push(),
            only by passing them as the fields parameter.

        :example:

            ::

                List([
                    BE32(name='id1', value=1),
                    BE32(name='id2', value=2),
                    BE32(name='id3', value=10),
                    BE32(name='id4', value=50),
                ])
        '''
        if not fields:
            raise KittyException('List constructor does not expect an empty list or None as fields')
        if isinstance(fields, BaseField):
            fields = [fields]
        self._final_fields = []
        base_fields = fields
        if delim:
            base_fields = _intersperse(base_fields, Container(fields=delim, fuzzable=False))
        self._final_fields.append(
            Container(name='internal_mutations', fields=base_fields)
        )
        self._final_fields.extend(self._get_dups(fields, delim))
        self._final_fields.extend(self._get_omits(fields, delim))
        self._final_fields.extend(self._get_rotations(fields, delim))
        super(List, self).__init__(fields=self._final_fields, encoder=encoder, fuzzable=fuzzable, name=name)

    def _get_dups(self, fields, delim):
        num_fields = len(fields)
        res = []
        for field_count in set(x for x in [1, 2, num_fields // 2, num_fields] if x > 0):
            for i in [2, 5, 10, 100, 1000]:
                res.append(
                    DuplicateMutator(
                        field_count=field_count,
                        dup_num=i,
                        fields=fields,
                        delim=delim,
                        name='duplicate_%s_%s' % (field_count, i)
                    )
                )
        return res

    def _get_omits(self, fields, delim):
        num_fields = len(fields)
        res = []
        for field_count in set([1, 2, num_fields // 2, num_fields]):
            if field_count > 0:
                res.append(
                    OmitMutator(
                        field_count=field_count,
                        fields=fields,
                        delim=delim,
                        name='omit_%s' % field_count
                    )
                )
        return res

    def _get_rotations(self, fields, delim):
        num_fields = len(fields)
        res = []
        counts = set([2, 5, 10, num_fields // 3, num_fields // 2, num_fields])
        counts = [c for c in counts if c >= 2]
        counts = [c for c in counts if c <= num_fields]
        for field_count in counts:
            if field_count > 0:
                res.append(
                    RotateMutator(
                        field_count=field_count,
                        fields=fields,
                        delim=delim,
                        name='rotation_%s' % field_count
                    )
                )
        return res
