#
# This file is part of Facedancer.
#
""" Functionality for working with objects with associated USB descriptors. """

from .magic import AutoInstantiable, DescribableMeta, adjust_defaults

from dataclasses import field
from enum import IntEnum
from typing import Dict
from warnings import warn

import itertools
import textwrap

class USBDescribable(metaclass=DescribableMeta):
    """
    Abstract base class for objects that can be created from USB descriptors.
    """

    # Override me!
    DESCRIPTOR_TYPE_NUMBER = None

    @classmethod
    def handles_binary_descriptor(cls, data):
        """
        Returns true iff this class handles the given descriptor. By default,
        this is based on the class's DESCRIPTOR_TYPE_NUMBER declaration.
        """
        return data[1] == cls.DESCRIPTOR_TYPE_NUMBER



    @classmethod
    def from_binary_descriptor(cls, data, strings={}):
        """
        Attempts to create a USBDescriptor subclass from the given raw
        descriptor data.
        """

        for subclass in cls.__subclasses__():
            # If this subclass handles our binary descriptor, use it to parse the given descriptor.
            if subclass.handles_binary_descriptor(data):
                return subclass.from_binary_descriptor(data, strings=strings)

        return USBDescriptor.from_binary_descriptor(data, strings=strings)


class USBDescriptor(USBDescribable, AutoInstantiable):
    """ Class for arbitrary USB descriptors; minimal concrete implementation of USBDescribable. """

    """ The raw bytes of the descriptor. """
    raw : bytes

    """ The bDescriptorType of the descriptor. """
    type_number : int = None

    """ Number to request this descriptor with a GET_DESCRIPTOR request. """
    number : int = None

    """ Parent object which this descriptor is associated with. """
    parent : USBDescribable = None

    """ Whether this descriptor should be included in a GET_CONFIGURATION response. """
    include_in_config : bool = False

    def __post_init__(self):
        # If type number was not set, get it from the raw bytes.
        if self.type_number is None and self.raw is not None:
            self.type_number = self.raw[1]

    def __call__(self, index=0):
        """ Converts the descriptor object into raw bytes. """
        return self.raw

    def get_identifier(self):
        return (self.type_number, self.number)

    @classmethod
    def from_binary_descriptor(cls, data, strings={}):
        return USBDescriptor(raw=data, type_number=data[1], number=None)

    def generate_code(self, name=None, indent=0):
        type_num = f"0x{self.type_number:02X}"
        if name is None:
            if self.include_in_config:
                name = f"Descriptor_{type_num}"
            else:
                name = f"Descriptor_{type_num}_{self.number}"

        # use a shim until we get itertools.batched in Python 3.12
        def batched(iterable, n=1):
            l = len(iterable)
            for ndx in range(0, l, n):
                yield iterable[ndx:min(ndx + n, l)]

        num_bytes = len(self.raw)
        if num_bytes == 0:
            raw = ""
        elif num_bytes < 7:
            raw = str.join(", ", (f'0x{b:02X}' for b in self.raw))
        else:
            if 8 < num_bytes < 20:
                chunk_size = (num_bytes + 1) // 2
            else:
                chunk_size = 10
            raw = "\n        " + str.join(",\n        ", (
                str.join(", ", (f'0x{b:02X}' for b in chunk))
                    for chunk in batched(self.raw, chunk_size)))

        code = "\n"
        if self.include_in_config:
            code += f"@include_in_config\n"
        if self.number is not None:
            code += f"@requestable(type_number={type_num}, number={self.number})\n"

        code += f"class {name}(USBDescriptor):\n"
        code += f"    raw = bytes([{raw}])\n"

        return textwrap.indent(code, ' ' * indent)


class USBClassDescriptor(USBDescriptor):
    """ Class for arbitrary USB Class descriptors. """

    include_in_config : bool = True

    def __init_subclass__(cls, **kwargs):
        warn(
            "The USBClassDescriptor class is deprecated. "
            "Use USBDescriptor with include_in_config=True instead.",
            UserWarning, 3)
        super().__init_subclass__(**kwargs)


class USBStringDescriptor(USBDescriptor):
    """ Class representing a USB string descriptor. """

    DESCRIPTOR_TYPE_NUMBER = 3

    # Property: the python version of the relevant string.
    python_string : str = None

    @classmethod
    def from_string(cls, string, *, index=None):

        # Grab the raw string
        raw_string = string.encode('utf-16')[2:]
        raw = bytes([len(raw_string) + 2, cls.DESCRIPTOR_TYPE_NUMBER, *raw_string])

        return cls(raw=raw, number=index, type_number=3, python_string=string)


class StringRef:
    """ Class representing a reference to a USB string descriptor. """

    def __init__(self, index: int = None, string : str = None):
        if index is None and str is None:
            raise TypeError("A StringRef must have an index or a string")
        self.index = index
        self.string = string


    @classmethod
    def field(cls, **kwargs):
        """ Used to create StringRef fields in dataclasses. """
        return field(default_factory=lambda: StringRef(**kwargs))


    @classmethod
    def lookup(cls, strings: Dict[int, str], index: int):
        """ Try to construct a StringRef given an index and a mapping """
        if index == 0:
            return StringRef(index=0)
        elif index in strings:
            return StringRef(index=index, string=strings[index])
        else:
            return StringRef(index=index)


    @classmethod
    def ensure(cls, value):
        """ Turn a value into a StringRef it is not one already. """
        if isinstance(value, StringRef):
            return value
        elif isinstance(value, tuple):
            index, string = value
            return StringRef(index=index, string=string)
        elif isinstance(value, int):
            return StringRef(index=value)
        elif isinstance(value, str):
            return StringRef(string=value)
        elif value is None:
            return StringRef(index=0)
        else:
            raise TypeError(f"Cannot construct StringRef from {repr(value)}")


    def generate_code(self):
        """ Generate input that will produce this StringRef when passed to ensure() """
        if self.index is not None and self.string is not None:
            return f"({self.index}, {repr(self.string)})"
        elif self.index == 0:
            return "None"
        elif self.index is not None:
            return str(self.index)
        elif self.string is not None:
            return repr(self.string)


class StringDescriptorManager:
    """ Manager class that collects active string descriptors. """

    def __init__(self):
        self.next_index = 1

        # Maps indexes => string descriptors.
        self.descriptors = {}

        # Maps python strings => indexes.
        self.indexes     = {}


    def add_string(self, string, index=None):
        """Add a Python string as a new string descriptor, and return an index.

        The specified index is used for the new string descriptor, overwriting
        any previous descriptor with the same index. If an index is not
        specified, a new, unique, incrementing index is allocated.
        """

        if isinstance(string, StringRef):
            index = string.index
            string = string.string

        if index is None:
            index = self.next_index

        if index in self.descriptors:
            old_string = self.descriptors[index].python_string
            self.indexes.pop(old_string)

        self.descriptors[index] = USBStringDescriptor.from_string(string, index=index)
        self.indexes[string]    = index

        while self.next_index in self.descriptors:
            self.next_index += 1

        return index


    def get_index(self, string):
        """ Returns the index of the given string; creating it if the string isn't already known. """

        # If we already have an index, leave it alone...
        if isinstance(string, StringRef):
            if string.index is not None:
                return string.index
            else:
                string = string.string
        elif isinstance(string, int):
            return string

        # Special case: return 0 for None, allowing null strings to be represented.
        if string is None:
            return 0

        if string in self.indexes:
            return self.indexes[string]

        return self.add_string(string)


    def __getitem__(self, index):
        """ Gets the relevant string descriptor. """

        if isinstance(index, str):
            index = self.get_index(index)

        return self.descriptors.get(index, None)


class USBDescriptorTypeNumber(IntEnum):
    DEVICE                    = 1
    CONFIGURATION             = 2
    STRING                    = 3
    INTERFACE                 = 4
    ENDPOINT                  = 5
    DEVICE_QUALIFIER          = 6
    OTHER_SPEED_CONFIGURATION = 7
    INTERFACE_POWER           = 8
    HID                       = 33
    REPORT                    = 34


def include_in_config(cls):
    """ Decorator that marks a descriptor to be included in configuration data. """
    return adjust_defaults(cls, include_in_config=True)


def requestable(type_number, number):
    """ Decorator that marks a descriptor as requestable. """
    return lambda cls: adjust_defaults(cls, type_number=type_number, number=number)
