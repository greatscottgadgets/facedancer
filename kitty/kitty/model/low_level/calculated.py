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
Fields that are dependant on other fields - Size, Checksum etc.
'''
import zlib
import hashlib
from bitstring import Bits
from kitty.model.low_level.field import BaseField
from kitty.model.low_level.field import BitField
from kitty.model.low_level.encoder import BitsEncoder
from kitty.model.low_level.encoder import StrEncoder
from kitty.model.low_level.encoder import ENC_BITS_DEFAULT
from kitty.model.low_level.encoder import ENC_STR_DEFAULT
from kitty.model.low_level.encoder import ENC_INT_DEFAULT
from kitty.model.low_level.ll_utils import RenderContext
from kitty.core import KittyException, khash, kassert


empty_bits = Bits()


def num_bits_to_bytes(x):
    return x // 8


class Calculated(BaseField):
    '''
    A base type for fields that are calculated based on other fields
    '''
    _encoder_type_ = BitsEncoder
    _default_value_ = empty_bits
    VALUE_BASED = 'value'
    LENGTH_BASED = 'length'
    FIELD_PROP_BASED = 'field property'

    def __init__(self, depends_on, encoder=ENC_BITS_DEFAULT, fuzzable=True, name=None):
        '''
        :param depends_on: (name of) field we depend on
        :type encoder: :class:`~kitty.model.low_level.encoder.BitsEncoder`
        :param encoder: encoder for the field
        :param fuzzable: is container fuzzable
        :param name: (unique) name of the container
        '''
        self._rendered_field = None
        self.dependency_type = Calculated.VALUE_BASED
        super(Calculated, self).__init__(value=self.__class__._default_value_, encoder=encoder, fuzzable=fuzzable, name=name)
        if isinstance(depends_on, str):
            self._field_name = depends_on
            self._field = None
        elif isinstance(depends_on, BaseField):
            self._field_name = None
            self._field = depends_on
        else:
            raise KittyException('depends_on parameter (%s) is neither a string nor a valid field' % depends_on)

    def is_default(self):
        '''
        Checks if the field is in its default form

        :return: True if field is in default form
        '''
        return False

    def _initialize(self):
        '''
        We override _initialize, as we want to resolve the field each time
        '''
        if self._field_name:
            self._field = self.resolve_field(self._field_name)
        if not self._field:
            raise KittyException('Could not resolve field name %s' % self._field_name)

    def render(self, ctx=None):
        '''
        Render the current value into a :class:`bitstring.Bits` object

        :rtype: :class:`bitstring.Bits`
        :return: the rendered field
        '''
        self._initialize()
        if ctx is None:
            ctx = RenderContext()
        #
        # if we are called from within render, return a dummy object...
        #
        if self in ctx:
            self._current_rendered = self._in_render_value()
        else:
            ctx.push(self)
            if self.dependency_type == Calculated.VALUE_BASED:
                self._rendered_field = self._field.render(ctx)
            self._render()
            ctx.pop()
        return self._current_rendered

    def _render(self):
        raise NotImplementedError('_render should be implemented in subclass')

    def _in_render_value(self):
        '''
        This method is called when rendered was called recursively.
        This means that we are enclosed by the field we depend on.
        So consider carefully what value are you going to return....

        :rtype: Bits
        :return: a dummy rendered value
        '''
        raise NotImplementedError('_in_render_value should be implemented in subclass (%s)' % type(self).__name__)

    def hash(self):
        '''
        :rtype: int
        :return: hash of the field
        '''
        hashed = super(Calculated, self).hash()
        return khash(hashed, self._field_name)


class CalculatedBits(Calculated):
    '''
    field that depends on the rendered value of a field, and rendered into Bits() object
    '''

    def __init__(self, depends_on, func, encoder=ENC_BITS_DEFAULT, fuzzable=True, name=None):
        '''
        :param depends_on: (name of) field we depend on
        :type encoder: :class:`~kitty.model.low_level.encoder.BitsEncoder`
        :param func: function for processing of the dependant data. func(Bits)->Bits
        :param encoder: encoder for the field
        :param fuzzable: is container fuzzable
        :param name: (unique) name of the container
        '''
        try:
            res = func(empty_bits)
            kassert.is_of_types(res, Bits)
            self._func = func
        except:
            raise KittyException('func should be func(Bits)->Bits')
        super(CalculatedBits, self).__init__(depends_on=depends_on, encoder=encoder, fuzzable=fuzzable, name=name)

    def _render(self):
        res = self._func(self._rendered_field)
        self.set_current_value(res)


class Clone(CalculatedBits):
    '''
    rendered the same as the field it depends on
    '''

    def __init__(self, depends_on, encoder=ENC_BITS_DEFAULT, fuzzable=False, name=None):
        '''
        :param depends_on: (name of) field we depend on
        :type encoder: :class:`~kitty.model.low_level.encoder.BitsEncoder`
        :param encoder: encoder for the field (default: ENC_BITS_DEFAULT)
        :param fuzzable: is container fuzzable
        :param name: (unique) name of the container

        :example:

            ::

                Container(name='empty HTML body', fields=[
                    Static('<'),
                    String(name='opening tag', value='body'),
                    Static('>'),
                    Static('</'),
                    Clone(name='closing tag', depends_on='opening tag'),
                    Static('>'),
                ])
        '''
        super(Clone, self).__init__(depends_on=depends_on, func=lambda x: x, encoder=encoder, fuzzable=fuzzable, name=name)

    def _in_render_value(self):
        return empty_bits


class CalculatedStr(Calculated):
    '''
    field that depends on the rendered value of a byte-aligned field and rendered to a byte aligned Bits() object
    '''
    _encoder_type_ = StrEncoder
    _default_value_ = ''

    def __init__(self, depends_on, func, encoder=ENC_STR_DEFAULT, fuzzable=False, name=None):
        '''
        :param depends_on: (name of) field we depend on
        :param func: function for processing of the dependant data. func(str)->str
        :type encoder: :class:`~kitty.model.low_level.encoder.StrEncoder`
        :param encoder: encoder for the field (default: ENC_STR_DEFAULT)
        :param fuzzable: is container fuzzable
        :param name: (unique) name of the container
        '''
        try:
            res = func(b'')
            kassert.is_of_types(res, bytes)
            self._func = func
        except:
            raise KittyException('func should be func(str)->str')
        super(CalculatedStr, self).__init__(depends_on=depends_on, encoder=encoder, fuzzable=fuzzable, name=name)

    def _render(self):
        if len(self._rendered_field) % 8 != 0:
            raise KittyException('Hashed data should be byte aligned')
        digest = self._func(self._rendered_field.bytes)
        self.set_current_value(digest)


class Hash(CalculatedStr):
    '''
    Hash of a field.

    .. note::

        To make it more convenient, there are multiple aliases for various hashes.
        Take a look at :mod:`~kitty.model.low_level.aliases`.
    '''
    _algos = {
        'md5': (hashlib.md5, 128),
        'sha1': (hashlib.sha1, 160),
        'sha224': (hashlib.sha224, 224),
        'sha256': (hashlib.sha256, 256),
        'sha384': (hashlib.sha384, 384),
        'sha512': (hashlib.sha512, 512),
    }

    def __init__(self, depends_on, algorithm, encoder=ENC_STR_DEFAULT, fuzzable=False, name=None):
        '''
        :param depends_on: (name of) field to be hashed
        :param algorithm: hash algorithm name (from Hash._algos) or a function to calculate the value of the field. func(str) -> str
        :type encoder: :class:`~kitty.model.low_level.encoder.StrEncoder`
        :param encoder: encoder for the field (default: ENC_STR_DEFAULT)
        :param fuzzable: is field fuzzable (default: False)
        :param name: (unique) name of the field (default: None)

        :example:

            ::

                Container(name='SHA1 hashed string', fields=[
                    Meta(String(name='secret', value='s3cr3t')),
                    Hash(name='secret_hash', algorithm='sha1', depends_on='secret')
                ])
        '''
        if algorithm in Hash._algos:
            algo = Hash._algos[algorithm][0]

            def algo_func(x):
                return algo(x).digest()

            func = algo_func
            self._hash_length = Hash._algos[algorithm][1]
        else:
            try:
                res = algorithm(b'')
                kassert.is_of_types(res, str)
                func = algorithm
                self._hash_length = len(res) * 8
            except:
                raise KittyException('algorithm should be a func(str)->str or one of the strings %s' % (Hash._algos.keys(),))
        super(Hash, self).__init__(depends_on=depends_on, func=func, encoder=encoder, fuzzable=fuzzable, name=name)

    def _in_render_value(self):
        return Bits(self._hash_length)


class CalculatedInt(Calculated):
    '''
    field that depends on the rendered value of another field and is rendered to (int, length, signed) tuple
    '''

    def __init__(self, depends_on, bit_field, calc_func, encoder=ENC_BITS_DEFAULT, fuzzable=False, name=None):
        '''
        :param depends_on: (name of) field we depend on
        :param bit_field: a BitField to be used for holding the value
        :type calc_func: func(bits) -> int
        :param calc_func: function to calculate the value of the field
        :type encoder: :class:`~kitty.model.low_level.encoder.BitsEncoder`
        :param encoder: encoder for the field (default: ENC_BITS_DEFAULT)
        :param fuzzable: is container fuzzable
        :param name: (unique) name of the container
        '''
        super(CalculatedInt, self).__init__(depends_on=depends_on, encoder=encoder, fuzzable=fuzzable, name=name)
        self._bit_field = bit_field
        self._calc_func = calc_func
        self._first_render = False
        self._num_mutations = self._bit_field.num_mutations()

    def scan_for_field(self, field_name):
        '''
        If the field name is the internal field - return it
        '''
        if self._bit_field.get_name() == field_name:
            return self._bit_field
        return None

    def reset(self):
        super(CalculatedInt, self).reset()
        self._first_render = False

    def _calculate_value(self):
        return self._calc_func(self._rendered_field)

    def _render(self):
        calculated_value = self._calculate_value()
        # This code meant for handling overflow...
        calculated_value = min(calculated_value, self._bit_field._max_value)
        calculated_value = max(calculated_value, self._bit_field._min_value)
        if self._mutating():
            if self._first_render:
                # mutate applies a mutation function on the default value
                self._bit_field._default_value = calculated_value
                self._bit_field.mutate()
                self._first_render = False
        else:
            self._bit_field.set_current_value(calculated_value)
        self.set_current_value(self._bit_field.render())

    def _mutate(self):
        self._first_render = True

    def _in_render_value(self):
        '''
        :return: a zeroed version of the field, good for some checksums and inclusive lengths
        '''
        return Bits(len(self._bit_field.render()))


class FieldIntProperty(CalculatedInt):
    '''
    Calculate an int value based on some field property.
    The main difference from :class:`~kitty.model.low_level.calculated.CalculatedInt`
    is that it provides the field itself to the calculation function,
    not its rendered value.
    '''

    def __init__(self, depends_on, length, correction=None, encoder=ENC_INT_DEFAULT, fuzzable=False, name=None):
        '''
        :param depends_on: (name of) field we depend on
        :param length: length of the FieldIntProperty field (in bits)
        :type corrention: int or func(int) -> int
        :param correction: correction function, or value for the index
        :type encoder: :class:`~kitty.model.low_level.encoder.BitFieldEncoder`
        :param encoder: encoder for the field (default: ENC_INT_DEFAULT)
        :param fuzzable: is container fuzzable
        :param name: (unique) name of the container (default: None)
        '''
        if correction:
            if not callable(correction):
                if not isinstance(correction, int):
                    raise KittyException('correction must be int, function or None!')
        self._correction = correction
        bit_field = BitField(value=0, length=length, encoder=encoder)
        super(FieldIntProperty, self).__init__(depends_on=depends_on, bit_field=bit_field, calc_func=None, fuzzable=fuzzable, name=name)
        self.dependency_type = Calculated.FIELD_PROP_BASED

    def _calculate_value(self):
        calculated = self._calculate(self._field)
        if callable(self._correction):
            calculated = self._correction(calculated)
        elif isinstance(self._correction, int):
            calculated += self._correction
        return calculated


class ElementCount(FieldIntProperty):
    '''
    Number of elements inside another field.
    The value depends on the number of fields in the field it depends on.

    :example:

        ::

            Container(name='list with count', fields=[
                ElementCount(  # will be rendered to '3'
                    name='element count',
                    depends_on='list of items',
                    length=32,
                    encoder=ENC_INT_DEC
                ),
                Container(name='list of items', fields=[
                    Static('element 1'),
                    Static('element 2'),
                    Static('element 3'),
                ])
            ])
    '''

    def _calculate(self, field):
        return len(field.get_rendered_fields(RenderContext(self)))


class IndexOf(FieldIntProperty):
    '''
    Index of a field in its container.

    Edge case behavior:

        - If field has no encloser - return 0
        - If field is not rendered - return len(rendered element list) as index/

    :example:

        ::

            Container(name='indexed list', fields=[
                IndexOf(  # will be rendered to '2'
                    name='index of second',
                    depends_on='second',
                    length=32,
                    encoder=ENC_INT_DEC
                ),
                Container(name='list of items', fields=[
                    Static(name='first', value='A'),
                    Static(name='second', value='B'),
                    Static(name='third', value='C'),
                ])
            ])
    '''

    def _calculate(self, field):
        '''
        We want to avoid trouble, so if the field is not enclosed by any other field,
        we just return 0.
        '''
        encloser = field.enclosing
        if encloser:
            rendered = encloser.get_rendered_fields(RenderContext(self))
            if field not in rendered:
                value = len(rendered)
            else:
                value = rendered.index(field)
        else:
            value = 0
        return value


class Checksum(CalculatedInt):
    '''
    Checksum of another container.
    '''
    _algos = {
        'adler32': zlib.adler32,
        'crc32': zlib.crc32,
    }

    def __init__(self, depends_on, length, algorithm='crc32', encoder=ENC_INT_DEFAULT, fuzzable=False, name=None):
        '''
        :param depends_on: (name of) field to be checksummed
        :param length: length of the checksum field (in bits)
        :param algorithm: checksum algorithm name (from Checksum._algos) or a function to calculate the value of the field. func(Bits) -> int
        :type encoder: :class:`~kitty.model.low_level.encoder.BitFieldEncoder`
        :param encoder: encoder for the field (default: ENC_INT_DEFAULT)
        :param fuzzable: is field fuzzable (default: False)
        :param name: (unique) name of the field (default: None)

        :example:

            ::

                Container(name='checksummed chunk', fields=[
                    RandomBytes(name='chunk', value='1234', min_length=0, max_length=75),
                    Checksum(name='CRC', depends_on='chunk', length=32)
                ])
        '''
        if algorithm in Checksum._algos:
            func = Checksum._algos[algorithm]
        else:
            try:
                res = algorithm(empty_bits)
                kassert.is_of_types(res, int)
                func = algorithm
            except:
                raise KittyException('algorithm should be a func(str)->int or one of the strings %s' % (Checksum._algos.keys(),))

        def calc_func(x):
            return func(x.bytes) & 0xffffffff

        bit_field = BitField(value=0, length=length, encoder=encoder)
        super(Checksum, self).__init__(depends_on=depends_on, bit_field=bit_field, calc_func=calc_func, fuzzable=fuzzable, name=name)


class Size(CalculatedInt):
    '''
    Size of another container. Calculated in each render call

    .. note::

        In most cases you can use the function :func:`~kitty.model.low_level.aliases.SizeInBytes`
        instead, which receives the same arguments except of `calc_func`
    '''

    def __init__(self, sized_field, length, calc_func=lambda x: len(x) // 8, encoder=ENC_INT_DEFAULT, fuzzable=False, name=None):
        '''
        :param sized_field: (name of) field to be sized
        :param length: length of the size field (in bits)
        :param calc_func: function to calculate the value of the field. func(bits) -> int (default: length in bytes)
        :type encoder: :class:`~kitty.model.low_level.encoder.BitFieldEncoder`
        :param encoder: encoder for the field (default: ENC_INT_DEFAULT)
        :param fuzzable: is field fuzzable (default: False)
        :param name: (unique) name of the field (default: None)

        :examples:

            Calculate the size of a field/container in bits

            ::

                Container(name='sized chunk', fields=[
                    RandomBytes(name='chunk', value='1234', min_length=0, max_length=75),
                    Size(
                        name='size in bits',
                        sized_field='chunk',
                        length=32,
                        calc_func=lambda x: len(x)
                    )
                ])

            Calculate the size of a field/container in bytes, and add 5 to the result

            ::

                Container(name='sized chunk', fields=[
                    RandomBytes(name='chunk', value='1234', min_length=0, max_length=75),
                    Size(
                        name='size in bytes plus 5',
                        sized_field='chunk',
                        length=32,
                        calc_func=lambda x: len(x) // 8 + 5
                    )
                ])
        '''
        bit_field = BitField(value=0, length=length, encoder=encoder)
        super(Size, self).__init__(depends_on=sized_field, bit_field=bit_field, calc_func=calc_func, fuzzable=fuzzable, name=name)
        self.dependency_type = Calculated.LENGTH_BASED
        self._need_second_pass = True

    def _calculate_value(self):
        return self._calc_func(self._field._current_rendered)


class Offset(FieldIntProperty):
    '''
    A relative offset of a field from another field
    '''

    def __init__(self, base_field, target_field, length, correction=None, encoder=ENC_INT_DEFAULT, fuzzable=True, name=None):
        '''
        :param base_field: (name of) field to calculate offset from
        :param target_field: (name of) field to calculate offset to
        :param length: length of the Offset field (in bits)
        :type corrention: int or func(int) -> int
        :param correction: correction function, or value for the index, (default: divide by 8 (bytes))
        :type encoder: :class:`~kitty.model.low_level.encoder.BitFieldEncoder`
        :param encoder: encoder for the field (default: ENC_INT_DEFAULT)
        :param fuzzable: is container fuzzable
        :param name: (unique) name of the container (default: None)

        :examples:

            Calculate the offset of field C from field B, in bits

            ::

                Container(fields=[
                    String(name='A', value='base string'),
                    String(name='B', value='bar'),
                    String(name='C', value='target string'),
                    Offset(
                        base_field='B',
                        target_field='C',
                        length=32,
                        correction=lambda x: x,
                    )
                ])

            Calculate the absolute offset of field C from the beginning of the payload
            (also, see :class:`~kitty.model.low_level.calculated.AbsoluteOffset`)

            ::

                Container(fields=[
                    String(name='A', value='base string'),
                    String(name='B', value='bar'),
                    String(name='C', value='target string'),
                    Offset(
                        base_field=None,
                        target_field='C',
                        length=32,
                    )
                ])
        '''
        if correction is None:
            correction = num_bits_to_bytes
        super(Offset, self).__init__(depends_on=target_field, length=length, correction=correction, encoder=encoder, fuzzable=fuzzable, name=name)
        if isinstance(base_field, str):
            self.base_field_name = base_field
            self.base_field = None
        elif isinstance(base_field, BaseField):
            self.base_field_name = None
            self.base_field = base_field
        else:
            self.base_field_name = None
            self.base_field = None
        self._need_second_pass = True

    def _calculate(self, field):
        '''
        If the offset is unknown, return 0
        '''
        base_offset = 0
        if self.base_field is not None:
            base_offset = self.base_field.offset
        target_offset = self._field.offset
        if (target_offset is None) or (base_offset is None):
            return 0
        return target_offset - base_offset

    def _initialize(self):
        super(Offset, self)._initialize()
        # now resolve the actual fields ...
        if self.base_field_name:
            self.base_field = self.resolve_field(self.base_field_name)


class AbsoluteOffset(Offset):
    '''
    An absolute offset of a field from the beginning of the payload
    '''

    def __init__(self, target_field, length, correction=None, encoder=ENC_INT_DEFAULT, fuzzable=True, name=None):
        '''
        :param target_field: (name of) field to calculate offset to
        :param length: length of the AbsoluteOffset field (in bits)
        :type corrention: int or func(int) -> int
        :param correction: correction function, or value for the index, (default: divide by 8 (bytes))
        :type encoder: :class:`~kitty.model.low_level.encoder.BitFieldEncoder`
        :param encoder: encoder for the field (default: ENC_INT_DEFAULT)
        :param fuzzable: is container fuzzable
        :param name: (unique) name of the container (default: None)

        :example:

            ::

                Container(fields=[
                    String(name='A', value='base string'),
                    String(name='B', value='bar'),
                    String(name='C', value='target string'),
                    AbsoluteOffset(
                        target_field='C',
                        length=32,
                    )
                ])
        '''
        super(AbsoluteOffset, self).__init__(
            base_field=None, target_field=target_field, length=length,
            correction=correction, encoder=encoder, fuzzable=fuzzable, name=name
        )
