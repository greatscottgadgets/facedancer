#
# This file is part of Facedancer.
#
""" Code for working with HID usages. """


from enum import IntEnum


class HIDUsagePage(IntEnum):
    """ HID Usage Page numbers; from USB HID Usage Tables [Table 1]. """
    GENERIC_DESKTOP      = 0x01
    SIMULATION           = 0x02
    VR                   = 0x03
    SPORT                = 0x04
    GAME                 = 0x05
    GENERIC              = 0x06
    KEYBOARD             = 0x07
    LEDS                 = 0x08
    BUTTONS              = 0x09
    ORDINAL              = 0x0A
    TELEPHONY            = 0x0B
    CONSUMER             = 0x0C
    DIGITIZER            = 0x0D
    PID                  = 0x0F
    UNICODE              = 0x10
    ALPHANUMERIC_DISPLAY = 0x14
    MEDICAL_INSTRUMENTS  = 0x40
    BARCODE_SCANNER      = 0x8C
    SCALE                = 0x8D
    MAGNETIC_STRIPE      = 0x8E
    CAMERA_CONTROL       = 0x90
    ARCADE               = 0x91
    VENDOR_DEFINED       = 0xFFFF


class HIDGenericDesktopUsage(IntEnum):
    """ HID Usages for Generic Desktop Control; from [Table 6]. """
    POINTER                    = 0x01
    MOUSE                      = 0x02
    JOYSTICK                   = 0x04
    GAMEPAD                    = 0x05
    KEYBOARD                   = 0x06
    KEYPAD                     = 0x07
    MULTIAXIS_CONTROLLER       = 0x08
    TABLET_PC_SYSTEM_CONTROLS  = 0x09
    X                          = 0x30
    Y                          = 0x31
    Z                          = 0x32
    RX                         = 0x33
    RY                         = 0x34
    RZ                         = 0x35
    SLIDER                     = 0x36
    DIAL                       = 0x37
    WHEEL                      = 0x38
    HAT_SWITCH                 = 0x39
    COUNTED_BUFFER             = 0x3A
    BYTE_COUNT                 = 0x3B
    MOTION_WAKEUP              = 0x3C
    START                      = 0x3D
    SELECT                     = 0x3E
    VX                         = 0x40
    VY                         = 0x41
    VZ                         = 0x42
    VBRX                       = 0x43
    VBRY                       = 0x44
    VBRZ                       = 0x45
    VNO                        = 0x46
    FEATURE_NOTIFICATION       = 0x47
    RESOLUTION_MULTIPLIER      = 0x48
    SYSTEM_CONTROL             = 0x80
    SYSTEM_POWER_DOWN          = 0x81
    SYSTEM_SLEEP               = 0x82
    SYSTEM_WAKE_UP             = 0x83
    SYSTEM_CONTEXT_MENU        = 0x84
    SYSTEM_MAIN_MENU           = 0x85
    SYSTEM_APP_MENU            = 0x86
    SYSTEM_MENU_HELP           = 0x87
    SYSTEM_MENU_EXIT           = 0x88
    SYSTEM_MENU_SELECT         = 0x89
    SYSTEM_MENU_RIGHT          = 0x8A
    SYSTEM_MENU_LEFT           = 0x8B
    SYSTEM_MENU_UP             = 0x8C
    SYSTEM_MENU_DOWN           = 0x8D
    SYSTEM_COLD_RESTART        = 0x8E
    SYSTEM_WARM_UP             = 0x8F
    DPAD_UP                    = 0x90
    DPAD_DOWN                  = 0x91
    DPAD_RIGHT                 = 0x92
    DPAD_LEFT                  = 0x93
    SYSTEM_DOCK                = 0xA0
    SYSTEM_UNDOCK              = 0xA1
    SYSTEM_SETUP               = 0xA2
    SYSTEM_BREAK               = 0xA3
    SYSTEM_DEBUGGER_BREAK      = 0xA4
    APPLICATION_BREAK          = 0xA5
    APPLICATION_DEBUGGER_BREAK = 0xA6
    SYSTEM_SPEAKER_MUTE        = 0xA7
    SYSTEM_HIBERNATE           = 0xA8
    SYSTEM_DISPLAY_INVERT      = 0xB0
    SYSTEM_DISPLAY_INTERNAL    = 0xB1
    SYSTEM_DISPLAY_EXTERNAL    = 0xB2
    SYSTEM_DISPLAY_BOTH        = 0xB3
    SYSTEM_DISPLAY_DUAL        = 0xB4
    SYSTEM_DISPLAY_TOGGLE      = 0xB5
    SYSTEM_DISPLAY_SWAP        = 0xB6
    SYSTEM_DISPLAY_AUTOSCALE   = 0xB7

