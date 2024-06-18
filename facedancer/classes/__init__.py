#
# This file is part of Facedancer.
#
""" Support code for USB classes. """

from enum import IntEnum


class USBDeviceClass(IntEnum):
    """ Class representing known USB class numbers. """
    COMPOSITE            = 0x00
    AUDIO                = 0x01
    COMMUNICATIONS       = 0x02
    HID                  = 0x03
    PHYSICAL             = 0x05
    IMAGE                = 0x06
    PRINTER              = 0x07
    MASS_STORAGE         = 0x08
    HUB                  = 0x09
    CDC_DATA             = 0x0A
    SMART_CARD           = 0x0B
    CONTENT_SECURITY     = 0x0D
    VIDEO                = 0x0E
    PERSONAL_HEALTHCARE  = 0x0F
    AUDIO_VIDEO          = 0x10
    BILLBOARD            = 0x11
    TYPE_C_BRIDGE        = 0x12
    DIAGNOSTIC           = 0xDC
    WIRELESS_CONTROLLER  = 0xE0
    MISCELLANEOUS        = 0xEF
    APPLICATION_SPECIFIC = 0xFE
    VENDOR_SPECIFIC      = 0xFF
