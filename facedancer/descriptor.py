#
# This file is part of Facedancer.
#
""" Functionality for working with objects with associated USB descriptors. """

from dataclasses import dataclass

from .magic import AutoInstantiable

from enum import IntEnum
from warnings import warn

import itertools
import textwrap

class USBDescribable(object):
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


@dataclass
class USBDescriptor(USBDescribable, AutoInstantiable):
    """ Class for arbitrary USB descriptors; minimal concrete implementation of USBDescribable. """

    """
    Index number of this descriptor.

    When include_in_config is True, this determines the order in which
    attached descriptors will appear after their parent in the response
    to a GET_CONFIGURATION request.

    When include_in_config is False, this is the index number with which
    this descriptor can be requested with a GET_DESCRIPTOR request.
    """
    number      : int

    """ The raw bytes of the descriptor. """
    raw         : bytes

    """ The bDescriptorType of the descriptor. """
    type_number : int            = None

    """ Parent object which this descriptor is associated with. """
    parent      : USBDescribable = None

    """ Whether this descriptor should be included in a GET_CONFIGURATION response. """
    include_in_config : bool     = False

    def __call__(self, index=0):
        """ Converts the descriptor object into raw bytes. """
        return self.raw

    def get_identifier(self):
        return (self.type_number, self.number)

    @classmethod
    def from_binary_descriptor(cls, data, strings={}):
        return USBDescriptor(raw=data, type_number=data[1], number=None)

    def generate_code(self, name=None, indent=0):
        if name is None:
            if self.include_in_config:
                name = f"Descriptor_0x{self.type_number:02X}"
            else:
                name = f"Descriptor_0x{self.type_number:02X}_{self.number}"

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
                    for chunk in itertools.batched(self.raw, chunk_size)))

        code = f"""
class {name}(USBDescriptor):
    type_number       : int  = 0x{self.type_number:02X}
    include_in_config : bool = {self.include_in_config}
    number            : int  = {self.number}

    raw : bytes = bytes([{raw}])
"""

        return textwrap.indent(code, ' ' * indent)


@dataclass
class USBClassDescriptor(USBDescriptor):
    """ Class for arbitrary USB Class descriptors. """

    include_in_config : bool = True

    def __init_subclass__(cls, **kwargs):
        warn(
            "The USBClassDescriptor class is deprecated. "
            "Use USBDescriptor with include_in_config=True instead.",
            UserWarning, 3)
        super().__init_subclass__(**kwargs)


@dataclass
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
        if isinstance(string, int):
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
