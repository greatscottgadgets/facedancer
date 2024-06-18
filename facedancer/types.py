#
# This file is part of Facedancer.
#
""" USB types -- defines enumerations that describe standard USB types """

from enum import Enum, IntFlag, IntEnum

class USBDirection(IntEnum):
    """ Class representing USB directions. """
    OUT = 0
    IN  = 1

    def is_in(self):
        return self is self.IN

    def is_out(self):
        return self is self.OUT

    @classmethod
    def parse(cls, value):
        """ Helper that converts a numeric field into a direction. """
        return cls(value)

    @classmethod
    def from_request_type(cls, request_type_int):
        """ Helper method that extracts the direction from a request_type integer. """
        return cls(request_type_int >> 7)

    @classmethod
    def from_endpoint_address(cls, address):
        """ Helper method that extracts the direction from an endpoint address. """
        return cls(address >> 7)

    def token(self):
        """ Generates the token corresponding to the given direction. """
        return USBPacketID.IN if (self is self.IN) else USBPacketID.OUT

    def reverse(self):
        """ Returns the reverse of the given direction. """
        return self.OUT if (self is self.IN) else self.IN


    def to_endpoint_address(self, endpoint_number):
        """ Helper method that converts and endpoint_number to an address, given direction. """
        if self.is_in():
            return endpoint_number | (1 << 7)
        else:
            return endpoint_number


class USBPIDCategory(IntFlag):
    """ Category constants for each of the groups that PIDs can fall under. """

    SPECIAL   = 0b00
    TOKEN     = 0b01
    HANDSHAKE = 0b10
    DATA      = 0b11

    MASK      = 0b11



class USBPacketID(IntFlag):
    """ Enumeration specifying all of the valid USB PIDs we can handle. """

    # Token group (lsbs = 0b01).
    OUT   = 0b0001
    IN    = 0b1001
    SOF   = 0b0101
    SETUP = 0b1101

    # Data group (lsbs = 0b11).
    DATA0 = 0b0011
    DATA1 = 0b1011
    DATA2 = 0b0111
    MDATA = 0b1111

    # Handshake group (lsbs = 0b10)
    ACK   = 0b0010
    NAK   = 0b1010
    STALL = 0b1110
    NYET  = 0b0110

    # Special group.
    PRE   = 0b1100
    ERR   = 0b1100
    SPLIT = 0b1000
    PING  = 0b0100

    # Flag representing that the PID seems invalid.
    PID_INVALID   = 0b10000
    PID_CORE_MASK = 0b01111


    @classmethod
    def from_byte(cls, byte, skip_checks=False):
        """ Creates a PID object from a byte. """

        # Convert the raw PID to an integer.
        pid_as_int = int.from_bytes(byte, byteorder='little')
        return cls.from_int(pid_as_int, skip_checks=skip_checks)


    @classmethod
    def from_int(cls, value, skip_checks=True):
        """ Create a PID object from an integer. """

        PID_MASK           = 0b1111
        INVERTED_PID_SHIFT = 4

        # Pull out the PID and its inverse from the byte.
        pid          = cls(value & PID_MASK)
        inverted_pid = value >> INVERTED_PID_SHIFT

        # If we're not skipping checks,
        if not skip_checks:
            if (pid ^ inverted_pid) != PID_MASK:
                pid |= cls.PID_INVALID

        return cls(pid)


    @classmethod
    def from_name(cls, name):
        """ Create a PID object from a string representation of its name. """
        return cls[name]


    @classmethod
    def parse(cls, value):
        """ Attempt to create a PID object from a number, byte, or string. """

        if isinstance(value, bytes):
            return cls.from_byte(value)

        if isinstance(value, str):
            return cls.from_name(value)

        if isinstance(value, int):
            return cls.from_int(value)

        return cls(value)


    def category(self):
        """ Returns the USBPIDCategory that each given PID belongs to. """
        return USBPIDCategory(self & USBPIDCategory.MASK)


    def is_data(self):
        """ Returns true iff the given PID represents a DATA packet. """
        return self.category() is USBPIDCategory.DATA


    def is_token(self):
        """ Returns true iff the given PID represents a token packet. """
        return self.category() is USBPIDCategory.TOKEN


    def is_handshake(self):
        """ Returns true iff the given PID represents a handshake packet. """
        return self.category() is USBPIDCategory.HANDSHAKE


    def is_invalid(self):
        """ Returns true if this object is an attempt to encapsulate an invalid PID. """
        return (self & self.PID_INVALID)

    def direction(self):
        """ Get a USB direction from a PacketID. """

        if self is self.SOF:
            return None

        if self is self.SETUP or self is self.OUT:
            return USBDirection.OUT

        if self is self.IN:
            return USBDirection.IN

        raise ValueError("cannot determine the direction of a non-token PID")



    def summarize(self):
        """ Return a summary of the given packet. """

        # By default, get the raw name.
        core_pid  = self & self.PID_CORE_MASK
        name = core_pid.name

        if self.is_invalid():
            return "{} (check-nibble invalid)".format(name)
        else:
            return name


class USBRequestRecipient(IntEnum):
    """ Enumeration that describes each 'recipient' of a USB request field. """

    DEVICE    = 0
    INTERFACE = 1
    ENDPOINT  = 2
    OTHER     = 3

    RESERVED  = 4

    @classmethod
    def from_integer(cls, value):
        """ Special factory that correctly handles reserved values. """

        # If we have one of the reserved values; indicate so.
        if 4 <= value < 32:
            return cls.RESERVED

        # Otherwise, translate the raw value.
        return cls(value)


    @classmethod
    def from_request_type(cls, request_type_int):
        """ Helper method that extracts the type from a request_type integer. """

        MASK  = 0b11111
        return cls(request_type_int & MASK)


class USBRequestType(IntEnum):
    """ Enumeration that describes each possible Type field for a USB request. """

    STANDARD  = 0
    CLASS     = 1
    VENDOR    = 2
    RESERVED  = 3


    @classmethod
    def from_request_type(cls, request_type_int):

        """ Helper method that extracts the type from a request_type integer. """
        SHIFT = 5
        MASK  = 0b11

        return cls((request_type_int >> SHIFT) & MASK)



class USBTransferType(IntEnum):
    CONTROL     = 0
    ISOCHRONOUS = 1
    BULK        = 2
    INTERRUPT   = 3


def endpoint_number_from_address(number):
    return number & 0x7F

class LanguageIDs(IntEnum):
    AFRIKAANS                  = 0X0436
    ALBANIAN                   = 0X041C
    ARABIC_SAUDI_ARABIA        = 0X0401
    ARABIC_IRAQ                = 0X0801
    ARABIC_EGYPT               = 0X0C01
    ARABIC_LIBYA               = 0X1001
    ARABIC_ALGERIA             = 0X1401
    ARABIC_MOROCCO             = 0X1801
    ARABIC_TUNISIA             = 0X1C01
    ARABIC_OMAN                = 0X2001
    ARABIC_YEMEN               = 0X2401
    ARABIC_SYRIA               = 0X2801
    ARABIC_JORDAN              = 0X2C01
    ARABIC_LEBANON             = 0X3001
    ARABIC_KUWAIT              = 0X3401
    ARABIC_UAE                 = 0X3801
    ARABIC_BAHRAIN             = 0X3C01
    ARABIC_QATAR               = 0X4001
    ARMENIAN                   = 0X042B
    ASSAMESE                   = 0X044D
    AZERI_LATIN                = 0X042C
    AZERI_CYRILLIC             = 0X082C
    BASQUE                     = 0X042D
    BELARUSSIAN                = 0X0423
    BENGALI                    = 0X0445
    BULGARIAN                  = 0X0402
    BURMESE                    = 0X0455
    CATALAN                    = 0X0403
    CHINESE_TAIWAN             = 0X0404
    CHINESE_PRC                = 0X0804
    CHINESE_HONG_KONG          = 0X0C04
    CHINESE_SINGAPORE          = 0X1004
    CHINESE_MACAU_SAR          = 0X1404
    CROATIAN                   = 0X041A
    CZECH                      = 0X0405
    DANISH                     = 0X0406
    DUTCH_NETHERLANDS          = 0X0413
    DUTCH_BELGIUM              = 0X0813
    ENGLISH_US                 = 0X0409
    ENGLISH_UNITED_KINGDOM     = 0X0809
    ENGLISH_AUSTRALIAN         = 0X0C09
    ENGLISH_CANADIAN           = 0X1009
    ENGLISH_NEW_ZEALAND        = 0X1409
    ENGLISH_IRELAND            = 0X1809
    ENGLISH_SOUTH_AFRICA       = 0X1C09
    ENGLISH_JAMAICA            = 0X2009
    ENGLISH_CARIBBEAN          = 0X2409
    ENGLISH_BELIZE             = 0X2809
    ENGLISH_TRINIDAD           = 0X2C09
    ENGLISH_ZIMBABWE           = 0X3009
    ENGLISH_PHILIPPINES        = 0X3409
    ESTONIAN                   = 0X0425
    FAEROESE                   = 0X0438
    FARSI                      = 0X0429
    FINNISH                    = 0X040B
    FRENCH_STANDARD            = 0X040C
    FRENCH_BELGIAN             = 0X080C
    FRENCH_CANADIAN            = 0X0C0C
    FRENCH_SWITZERLAND         = 0X100C
    FRENCH_LUXEMBOURG          = 0X140C
    FRENCH_MONACO              = 0X180C
    GEORGIAN                   = 0X0437
    GERMAN_STANDARD            = 0X0407
    GERMAN_SWITZERLAND         = 0X0807
    GERMAN_AUSTRIA             = 0X0C07
    GERMAN_LUXEMBOURG          = 0X1007
    GERMAN_LIECHTENSTEIN       = 0X1407
    GREEK                      = 0X0408
    GUJARATI                   = 0X0447
    HEBREW                     = 0X040D
    HINDI                      = 0X0439
    HUNGARIAN                  = 0X040E
    ICELANDIC                  = 0X040F
    INDONESIAN                 = 0X0421
    ITALIAN_STANDARD           = 0X0410
    ITALIAN_SWITZERLAND        = 0X0810
    JAPANESE                   = 0X0411
    KANNADA                    = 0X044B
    KASHMIRI_INDIA             = 0X0860
    KAZAKH                     = 0X043F
    KONKANI                    = 0X0457
    KOREAN                     = 0X0412
    KOREAN_JOHAB               = 0X0812
    LATVIAN                    = 0X0426
    LITHUANIAN                 = 0X0427
    LITHUANIAN_CLASSIC         = 0X0827
    MACEDONIAN                 = 0X042F
    MALAY_MALAYSIAN            = 0X043E
    MALAY_BRUNEI_DARUSSALAM    = 0X083E
    MALAYALAM                  = 0X044C
    MANIPURI                   = 0X0458
    MARATHI                    = 0X044E
    NEPALI_INDIA               = 0X0861
    NORWEGIAN_BOKMAL           = 0X0414
    NORWEGIAN_NYNORSK          = 0X0814
    ORIYA                      = 0X0448
    POLISH                     = 0X0415
    PORTUGUESE_BRAZIL          = 0X0416
    PORTUGUESE_STANDARD        = 0X0816
    PUNJABI                    = 0X0446
    ROMANIAN                   = 0X0418
    RUSSIAN                    = 0X0419
    SANSKRIT                   = 0X044F
    SERBIAN_CYRILLIC           = 0X0C1A
    SERBIAN_LATIN              = 0X081A
    SINDHI                     = 0X0459
    SLOVAK                     = 0X041B
    SLOVENIAN                  = 0X0424
    SPANISH_TRADITIONAL_SORT   = 0X040A
    SPANISH_MEXICAN            = 0X080A
    SPANISH_MODERN_SORT        = 0X0C0A
    SPANISH_GUATEMALA          = 0X100A
    SPANISH_COSTA_RICA         = 0X140A
    SPANISH_PANAMA             = 0X180A
    SPANISH_DOMINICAN_REPUBLIC = 0X1C0A
    SPANISH_VENEZUELA          = 0X200A
    SPANISH_COLOMBIA           = 0X240A
    SPANISH_PERU               = 0X280A
    SPANISH_ARGENTINA          = 0X2C0A
    SPANISH_ECUADOR            = 0X300A
    SPANISH_CHILE              = 0X340A
    SPANISH_URUGUAY            = 0X380A
    SPANISH_PARAGUAY           = 0X3C0A
    SPANISH_BOLIVIA            = 0X400A
    SPANISH_EL_SALVADOR        = 0X440A
    SPANISH_HONDURAS           = 0X480A
    SPANISH_NICARAGUA          = 0X4C0A
    SPANISH_PUERTO_RICO        = 0X500A
    SUTU                       = 0X0430
    SWAHILI_KENYA              = 0X0441
    SWEDISH                    = 0X041D
    SWEDISH_FINLAND            = 0X081D
    TAMIL                      = 0X0449
    TATAR_TATARSTAN            = 0X0444
    TELUGU                     = 0X044A
    THAI                       = 0X041E
    TURKISH                    = 0X041F
    UKRAINIAN                  = 0X0422
    URDU_PAKISTAN              = 0X0420
    URDU_INDIA                 = 0X0820
    UZBEK_LATIN                = 0X0443
    UZBEK_CYRILLIC             = 0X0843
    VIETNAMESE                 = 0X042A
    HID_USAGE_DATA_DESCRIPTOR  = 0X04FF
    HID_VENDOR_DEFINED_1       = 0XF0FF
    HID_VENDOR_DEFINED_2       = 0XF4FF
    HID_VENDOR_DEFINED_3       = 0XF8FF
    HID_VENDOR_DEFINED_4       = 0XFCFF


class DescriptorTypes(IntEnum):
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


class USBSynchronizationType(IntEnum):
    NONE         = 0x00
    ASYNC        = 0x01
    ADAPTIVE     = 0x02
    SYNCHRONOUS  = 0x03


class USBUsageType(IntEnum):
    DATA              = 0
    FEEDBACK          = 1
    IMPLICIT_FEEDBACK = 2


class USBStandardRequests(IntEnum):
    GET_STATUS        = 0
    CLEAR_FEATURE     = 1
    SET_FEATURE       = 3
    SET_ADDRESS       = 5
    GET_DESCRIPTOR    = 6
    SET_DESCRIPTOR    = 7
    GET_CONFIGURATION = 8
    SET_CONFIGURATION = 9
    GET_INTERFACE     = 10
    SET_INTERFACE     = 11
    SYNCH_FRAME       = 12


# Based on libusb's LIBUSB_SPEED_* constants.
#
# See: https://github.com/libusb/libusb/blob/master/libusb/libusb.h#L1126
class DeviceSpeed(IntEnum):
    UNKNOWN = 0
    LOW = 1
    FULL = 2
    HIGH = 3
    SUPER = 4
    SUPER_PLUS = 5


# Contains definition of USB class, which is just a container for a bunch of
# constants/enums associated with the USB protocol.
#
# TODO: would be nice if this module could re-export the other USB* classes so
# one need import only USB to get all the functionality
#
# TODO: check if it still makes sense to keep this around in facedancer v3, it's
# only used by USBProxyDevice

class USB:
    state_detached                      = 0
    state_attached                      = 1
    state_powered                       = 2
    state_default                       = 3
    state_address                       = 4
    state_configured                    = 5
    state_suspended                     = 6

    request_direction_host_to_device    = 0
    request_direction_device_to_host    = 1

    request_type_standard               = 0
    request_type_class                  = 1
    request_type_vendor                 = 2

    request_recipient_device            = 0
    request_recipient_interface         = 1
    request_recipient_endpoint          = 2
    request_recipient_other             = 3

    feature_endpoint_halt               = 0
    feature_device_remote_wakeup        = 1
    feature_test_mode                   = 2

    desc_type_device                    = 1
    desc_type_configuration             = 2
    desc_type_string                    = 3
    desc_type_interface                 = 4
    desc_type_endpoint                  = 5
    desc_type_device_qualifier          = 6
    desc_type_other_speed_configuration = 7
    desc_type_interface_power           = 8
    desc_type_hid                       = 33
    desc_type_report                    = 34

    # while this holds for HID, it may not be a correct model for the USB
    # ecosystem at large
    if_class_to_desc_type = {
            3 : desc_type_hid
    }

    def interface_class_to_descriptor_type(interface_class):
        return USB.if_class_to_desc_type.get(interface_class, None)
