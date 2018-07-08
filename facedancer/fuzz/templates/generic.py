'''
Generic data model components for all USB related fuzzing
'''
from kitty.model import Dynamic, String, BaseField
from kitty.model import OneOf, Pad, Template, Container
from kitty.model import SizeInBytes, UInt8
from kitty.model import ENC_STR_DEFAULT


def _join_name(prefix, postfix):
    if prefix is None:
        return None
    return '%s_%s' % (prefix, postfix)


class DynamicExtended(OneOf):
    '''
    Container that provides mutations based on the dynamic value,
    or based on the other given field.
    '''

    def __init__(self, key, value, additional_field, fuzzable=True, name=None):
        '''
        :param key: key for data in the session information
        :param value: the default value of the Dynamic field
        :param additional_field: the additional field to base the mutations on
        :param fuzzable: is this field fuzzable (default: False)
        :param name: name of the container (default: None)
        '''
        if name is None:
            name = key
        fields = [
            Dynamic(key=key, default_value=value, length=len(value), fuzzable=True, name=_join_name(name, 'dynamic')),
            additional_field
        ]
        super(DynamicExtended, self).__init__(fields=fields, fuzzable=fuzzable, name=name)


class DynamicString(DynamicExtended):
    '''
    Container that provides mutations based on the dynamic value,
    or based on string mutations.
    '''

    def __init__(self, key, value, keep_size=False, encoder=ENC_STR_DEFAULT, fuzzable=True, name=None):
        '''
        :param key: key for data in the session information
        :param value: the default value of the Dynamic field
        :param keep_size: should limit the size of the string based on the original string (default: False)
        :param encoder: string encoder (default: ``ENC_STR_DEFAULT``)
        :param fuzzable: is this field fuzzable (default: True)
        :param name: name of the container (default: None)
        '''
        str_len = len(value) if keep_size else None
        additional_field = String(value=value, max_size=str_len, encoder=encoder, name=_join_name(name, 'string'))
        if keep_size:
            additional_field = Pad(str_len * 8, fields=additional_field, name=_join_name(name, 'string_wrap'))
        super(DynamicString, self).__init__(
            key=key,
            value=value,
            additional_field=additional_field,
            fuzzable=fuzzable,
            name=name
        )


class DynamicInt(DynamicExtended):
    '''
    Container that provides mutations based on the dynamic value,
    or based on BitField mutations.
    '''

    def __init__(self, key, bitfield, fuzzable=True, name=None):
        '''
        :param key: key for data in the session information
        :param bitfield: a bitfield to base the value on
        :param fuzzable: (default: True)
        :param name: (default: None)
        '''
        super(DynamicInt, self).__init__(
            key=key,
            value=bitfield.render().bytes,
            additional_field=bitfield,
            fuzzable=fuzzable,
            name=name
        )


class Descriptor(Template):
    '''
    USB descriptor template.
    '''

    def __init__(self, name, descriptor_type, fields, fuzz_type=True):
        if isinstance(fields, BaseField):
            fields = [fields]
        fields.insert(0, SizeInBytes(name='bLength', sized_field=self, length=8, fuzzable=True))
        fields.insert(1, UInt8(name='bDescriptorType', value=descriptor_type, fuzzable=fuzz_type))
        super(Descriptor, self).__init__(name=name, fields=fields)


class SubDescriptor(Container):
    def __init__(self, name, descriptor_type, fields, fuzz_type=True):
        if isinstance(fields, BaseField):
            fields = [fields]
        fields.insert(0, SizeInBytes(name='bLength', sized_field=self, length=8, fuzzable=True))
        fields.insert(1, UInt8(name='bDescriptorType', value=descriptor_type, fuzzable=fuzz_type))
        super(SubDescriptor, self).__init__(name=name, fields=fields)


class SizedPt(Container):
    '''
    Sized part of a descriptor.
    It receives all fields excepts of the size field and adds it.
    '''
    def __init__(self, name, fields):
        '''
        :param name: name of the Container
        :param fields: list of fields in the container
        '''
        if isinstance(fields, BaseField):
            fields = [fields]
        fields.insert(0, SizeInBytes(name='%s size' % name, sized_field=self, length=8, fuzzable=True))
        super(SizedPt, self).__init__(name=name, fields=fields)
