from enum import IntEnum

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
