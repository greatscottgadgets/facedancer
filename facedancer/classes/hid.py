#
# This file is part of FaceDancer.
#
""" Code for implementing HID classes. """

import string
from enum import IntEnum, IntFlag


class Modifiers(IntFlag):
    MOD_LEFT_CTRL   = 0x01
    MOD_LEFT_SHIFT  = 0x02
    MOD_LEFT_ALT    = 0x04
    MOD_LEFT_META   = 0x08
    MOD_RIGHT_CTRL  = 0x10
    MOD_RIGHT_SHIFT = 0x20
    MOD_RIGHT_ALT   = 0x40
    MOD_RIGHT_META  = 0x80

class KeyboardKeys(IntEnum):
    NONE            = 0x00 # No key pressed
    ERR_OVF         = 0x01 #  Keyboard Error Roll Over - used for all slots if too many keys are pressed ("Phantom key")
    A               = 0x04 # Keyboard a and A
    B               = 0x05 # Keyboard b and B
    C               = 0x06 # Keyboard c and C
    D               = 0x07 # Keyboard d and D
    E               = 0x08 # Keyboard e and E
    F               = 0x09 # Keyboard f and F
    G               = 0x0a # Keyboard g and G
    H               = 0x0b # Keyboard h and H
    I               = 0x0c # Keyboard i and I
    J               = 0x0d # Keyboard j and J
    K               = 0x0e # Keyboard k and K
    L               = 0x0f # Keyboard l and L
    M               = 0x10 # Keyboard m and M
    N               = 0x11 # Keyboard n and N
    O               = 0x12 # Keyboard o and O
    P               = 0x13 # Keyboard p and P
    Q               = 0x14 # Keyboard q and Q
    R               = 0x15 # Keyboard r and R
    S               = 0x16 # Keyboard s and S
    T               = 0x17 # Keyboard t and T
    U               = 0x18 # Keyboard u and U
    V               = 0x19 # Keyboard v and V
    W               = 0x1a # Keyboard w and W
    X               = 0x1b # Keyboard x and X
    Y               = 0x1c # Keyboard y and Y
    Z               = 0x1d # Keyboard z and Z
    NUM_1           = 0x1e # Keyboard 1 and !
    NUM_2           = 0x1f # Keyboard 2 and @
    NUM_3           = 0x20 # Keyboard 3 and #
    NUM_4           = 0x21 # Keyboard 4 and $
    NUM_5           = 0x22 # Keyboard 5 and %
    NUM_6           = 0x23 # Keyboard 6 and ^
    NUM_7           = 0x24 # Keyboard 7 and &
    NUM_8           = 0x25 # Keyboard 8 and *
    NUM_9           = 0x26 # Keyboard 9 and (
    NUM_0           = 0x27 # Keyboard 0 and )
    ENTER           = 0x28 # Keyboard Return (ENTER)
    ESC             = 0x29 # Keyboard ESCAPE
    BACKSPACE       = 0x2a # Keyboard DELETE (Backspace)
    TAB             = 0x2b # Keyboard Tab
    SPACE           = 0x2c # Keyboard Spacebar
    MINUS           = 0x2d # Keyboard - and _
    EQUAL           = 0x2e # Keyboard = and +
    LEFTBRACE       = 0x2f # Keyboard [ and {
    RIGHTBRACE      = 0x30 # Keyboard ] and }
    BACKSLASH       = 0x31 # Keyboard \ and |
    HASHTILDE       = 0x32 # Keyboard Non-US # and ~
    SEMICOLON       = 0x33 # Keyboard ; and :
    APOSTROPHE      = 0x34 # Keyboard ' and "
    GRAVE           = 0x35 # Keyboard ` and ~
    COMMA              = 0x36 # Keyboard, and <
    DOT                = 0x37 # Keyboard . and >
    SLASH              = 0x38 # Keyboard / and ?
    CAPSLOCK           = 0x39 # Keyboard Caps Lock
    F1                 = 0x3a # Keyboard F1
    F2                 = 0x3b # Keyboard F2
    F3                 = 0x3c # Keyboard F3
    F4                 = 0x3d # Keyboard F4
    F5                 = 0x3e # Keyboard F5
    F6                 = 0x3f # Keyboard F6
    F7                 = 0x40 # Keyboard F7
    F8                 = 0x41 # Keyboard F8
    F9                 = 0x42 # Keyboard F9
    F10                = 0x43 # Keyboard F10
    F11                = 0x44 # Keyboard F11
    F12                = 0x45 # Keyboard F12
    SYSRQ              = 0x46 # Keyboard Print Screen
    SCROLLLOCK         = 0x47 # Keyboard Scroll Lock
    PAUSE              = 0x48 # Keyboard Pause
    INSERT             = 0x49 # Keyboard Insert
    HOME               = 0x4a # Keyboard Home
    PAGEUP             = 0x4b # Keyboard Page Up
    DELETE             = 0x4c # Keyboard Delete Forward
    END                = 0x4d # Keyboard End
    PAGEDOWN           = 0x4e # Keyboard Page Down
    RIGHT              = 0x4f # Keyboard Right Arrow
    LEFT               = 0x50 # Keyboard Left Arrow
    DOWN               = 0x51 # Keyboard Down Arrow
    UP                 = 0x52 # Keyboard Up Arrow
    NUMLOCK            = 0x53 # Keyboard Num Lock and Clear
    KPSLASH            = 0x54 # Keypad /
    KPASTERISK         = 0x55 # Keypad *
    KPMINUS            = 0x56 # Keypad -
    KPPLUS             = 0x57 # Keypad +
    KPENTER            = 0x58 # Keypad ENTER
    KP1                = 0x59 # Keypad 1 and End
    KP2                = 0x5a # Keypad 2 and Down Arrow
    KP3                = 0x5b # Keypad 3 and PageDn
    KP4                = 0x5c # Keypad 4 and Left Arrow
    KP5                = 0x5d # Keypad 5
    KP6                = 0x5e # Keypad 6 and Right Arrow
    KP7                = 0x5f # Keypad 7 and Home
    KP8                = 0x60 # Keypad 8 and Up Arrow
    KP9                = 0x61 # Keypad 9 and Page Up
    KP0                = 0x62 # Keypad 0 and Insert
    KPDOT              = 0x63 # Keypad . and Delete
    COMPOSE            = 0x65 # Keyboard Application
    POWER              = 0x66 # Keyboard Power
    KPEQUAL            = 0x67 # Keypad   =
    F13                = 0x68 # Keyboard F13
    F14                = 0x69 # Keyboard F14
    F15                = 0x6a # Keyboard F15
    F16                = 0x6b # Keyboard F16
    F17                = 0x6c # Keyboard F17
    F18                = 0x6d # Keyboard F18
    F19                = 0x6e # Keyboard F19
    F20                = 0x6f # Keyboard F20
    F21                = 0x70 # Keyboard F21
    F22                = 0x71 # Keyboard F22
    F23                = 0x72 # Keyboard F23
    F24                = 0x73 # Keyboard F24
    OPEN               = 0x74 # Keyboard Execute
    HELP               = 0x75 # Keyboard Help
    PROPS              = 0x76 # Keyboard Menu
    FRONT              = 0x77 # Keyboard Select
    STOP               = 0x78 # Keyboard Stop
    AGAIN              = 0x79 # Keyboard Again
    UNDO               = 0x7a # Keyboard Undo
    CUT                = 0x7b # Keyboard Cut
    COPY               = 0x7c # Keyboard Copy
    PASTE              = 0x7d # Keyboard Paste
    FIND               = 0x7e # Keyboard Find
    MUTE               = 0x7f # Keyboard Mute
    VOLUMEUP           = 0x80 # Keyboard Volume Up
    VOLUMEDOWN         = 0x81 # Keyboard Volume Down
    KPCOMMA            = 0x85 # Keypad Comma
    RO                 = 0x87 # Keyboard International1
    KATAKANAHIRAGANA   = 0x88 # Keyboard International2
    YEN                = 0x89 # Keyboard International3
    HENKAN             = 0x8a # Keyboard International4
    MUHENKAN           = 0x8b # Keyboard International5
    KPJPCOMMA          = 0x8c # Keyboard International6
    HANGEUL            = 0x90 # Keyboard LANG1
    HANJA              = 0x91 # Keyboard LANG2
    KATAKANA           = 0x92 # Keyboard LANG3
    HIRAGANA           = 0x93 # Keyboard LANG4
    ZENKAKUHANKAKU     = 0x94 # Keyboard LANG5
    #SYSRQ              = 0x9a # Keyboard SysReq/Attention
    KEYPAD_00          = 0xb0 # Keypad 00
    KEYPAD_000         = 0xb1 #  Keypad 000
    KPLEFTPAREN        = 0xb6 # Keypad (
    KPRIGHTPAREN       = 0xb7 # Keypad )
    LEFTCTRL           = 0xe0 # Keyboard Left Control
    LEFTSHIFT          = 0xe1 # Keyboard Left Shift
    LEFTALT            = 0xe2 # Keyboard Left Alt
    LEFTMETA           = 0xe3 # Keyboard Left GUI
    RIGHTCTRL          = 0xe4 # Keyboard Right Control
    RIGHTSHIFT         = 0xe5 # Keyboard Right Shift
    RIGHTALT           = 0xe6 # Keyboard Right Alt
    RIGHTMETA          = 0xe7 # Keyboard Right GUI
    MEDIA_PLAYPAUSE    = 0xe8
    MEDIA_STOPCD       = 0xe9
    MEDIA_PREVIOUSSONG = 0xea
    MEDIA_NEXTSONG     = 0xeb
    MEDIA_EJECTCD      = 0xec
    MEDIA_VOLUMEUP     = 0xed
    MEDIA_VOLUMEDOWN   = 0xee
    MEDIA_MUTE         = 0xef
    MEDIA_WWW          = 0xf0
    MEDIA_BACK         = 0xf1
    MEDIA_FORWARD      = 0xf2
    MEDIA_STOP         = 0xf3
    MEDIA_FIND         = 0xf4
    MEDIA_SCROLLUP     = 0xf5
    MEDIA_SCROLLDOWN   = 0xf6
    MEDIA_EDIT         = 0xf7
    MEDIA_SLEEP        = 0xf8
    MEDIA_COFFEE       = 0xf9
    MEDIA_REFRESH      = 0xfa
    MEDIA_CALC         = 0xfb


    @classmethod
    def get_simple_code(cls, symbol):
        replacements = {
            '<': '',
            '>': '',
            '\n': 'enter',
            ' ': 'space',
            ',': 'comma',
            '.': 'dot',
            '=': 'equal',
        }

        for original, new in replacements.items():
            symbol = symbol.replace(original, new)

        symbol = symbol.upper().strip()

        if not symbol:
            return 0

        if symbol in string.digits:
            symbol = f"NUM_{symbol}"

        return cls[symbol]

