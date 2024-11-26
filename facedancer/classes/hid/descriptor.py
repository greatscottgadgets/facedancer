#
# This file is part of Facedancer.
#
""" Code for implementing HID classes. """

# Support annotations on Python < 3.9
from __future__  import annotations

from enum        import IntEnum
from dataclasses import dataclass
from typing      import Tuple, Iterable

from ...descriptor import USBDescriptor, USBDescriptorTypeNumber


#
# Global items.
#

def _hid_item_generator(constant) -> Tuple[int]:
    """ Generates a HID descriptor global item entry. """

    # Generate a function that creates a item with
    # the relevant type...
    def hid_item(*octets):
        return (constant | len(octets), *octets)

    # ... and return it.
    return hid_item


def _io_item_generator(type_constant) -> Tuple[int]:

    # Generate a function that creates a item with
    # the relevant type...
    def hid_io_item(
            constant=False,
            variable=False,
            relative=False,
            wrap=False,
            nonlinear=False,
            preferred_state=True,
            nullable=False,
            buffered_bytes=False
        ):

        # If we have a buffered bytes byte, include it.
        item_length = 2 if buffered_bytes else 1

        # Build the relevant item.
        # See HID1.1 [6.2.2.4]
        item  = (1 << 0) if constant  else 0
        item |= (1 << 1) if variable  else 0
        item |= (1 << 2) if relative  else 0
        item |= (1 << 3) if wrap      else 0
        item |= (1 << 4) if nonlinear else 0
        item |= 0 if preferred_state  else (1 << 5)
        item |= (1 << 6) if nullable else 0

        # Build the item, and return it.
        extra = (1,) if buffered_bytes else ()
        return (type_constant | item_length, item, *extra)

    # ... and return our function.
    return hid_io_item


#
# Main items.
#

INPUT              =  _io_item_generator(0b1000_00_00)
OUTPUT             =  _io_item_generator(0b1001_00_00)
FEATURE            =  _io_item_generator(0b1011_00_00)
COLLECTION         = _hid_item_generator(0b1010_00_00)
END_COLLECTION     = lambda : (0b1100_00_00,)


# Note: the odd separation of the last two bits here is due to
# the formatting of the USB specification (and due to the fact)
# that those bits are overridden, and thus always should be zero.
USAGE_PAGE         = _hid_item_generator(0b0000_01_00)
LOGICAL_MINIMUM    = _hid_item_generator(0b0001_01_00)
LOGICAL_MAXIMUM    = _hid_item_generator(0b0010_01_00)
PHYSICAL_MINIMUM   = _hid_item_generator(0b0011_01_00)
PHYSICAL_MAXIMUM   = _hid_item_generator(0b0100_01_00)
UNIT_EXPONENT      = _hid_item_generator(0b0101_01_00)
UNIT               = _hid_item_generator(0b0110_01_00)
REPORT_SIZE        = _hid_item_generator(0b0111_01_00)
REPORT_ID          = _hid_item_generator(0b1000_01_00)
REPORT_COUNT       = _hid_item_generator(0b1001_01_00)
PUSH               = _hid_item_generator(0b1010_01_00)
POP                = _hid_item_generator(0b1011_01_00)

#
# Local items.
#
USAGE              = _hid_item_generator(0b0000_10_00)
USAGE_MINIMUM      = _hid_item_generator(0b0001_10_00)
USAGE_MAXIMUM      = _hid_item_generator(0b0010_10_00)
DESGINATOR_INDEX   = _hid_item_generator(0b0011_10_00)
DESGINATOR_MINIMUM = _hid_item_generator(0b0100_10_00)
DESGINATOR_MAXIMUM = _hid_item_generator(0b0101_10_00)
STRING_INDEX       = _hid_item_generator(0b0111_10_00)
STRING_MINIMUM     = _hid_item_generator(0b1000_10_00)
STRING_MAXIMUM     = _hid_item_generator(0b1001_10_00)
DELIMITER          = _hid_item_generator(0b1010_10_00)


class HIDCollection(IntEnum):
    """ HID collections; from HID1.1 [6.2.2.4]. """
    PHYSICAL       = 0x00
    APPLICATION    = 0x01
    LOGICAL        = 0x02
    REPORT         = 0x03
    NAMED_ARRAY    = 0x04
    USAGE_SWITCH   = 0x05
    USAGE_MODIFIER = 0x06
    VENDOR         = 0xFF


@dataclass
class HIDReportDescriptor(USBDescriptor):
    """ Descriptor class representing a HID report descriptor. """

    # Parameter where the user defines the descriptor's fields.
    fields: Iterable[bytes] = ()

    # Mark this as a HID report descriptor.
    type_number : int = USBDescriptorTypeNumber.REPORT
    raw         : None | bytes = None

    def __call__(self, index=0):
        """ Converts the descriptor object into raw bytes. """

        if self.raw is not None:
            return self.raw

        raw = bytearray()

        # Squish together all of our fields to make a descriptor.
        for field in self.fields:
            raw.extend(field)

        return bytes(raw)
