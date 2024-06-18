#
# This file is part of Facedancer.
#
""" Helpers for HID keyboards. """

import string
from enum import IntEnum, IntFlag


# Table mapping ASCII codes to their equivalent HID keycodes.
# From the Adafruit HID library; https://github.com/adafruit/Adafruit_CircuitPython_HID/.
# Used under copyright exemption (as these are facts, rather than implementation).
#
# Like their table; the most significant bit is used to indicate whether we should press shift.
#
_ASCII_TO_KEYCODE = (
    b'\x00'    # NUL
    b'\x00'    # SOH
    b'\x00'    # STX
    b'\x00'    # ETX
    b'\x00'    # EOT
    b'\x00'    # ENQ
    b'\x00'    # ACK
    b'\x00'    # BEL \a
    b'\x2a'    # BS BACKSPACE \b (called DELETE in the usb.org document)
    b'\x2b'    # TAB \t
    b'\x28'    # LF \n (called Return or ENTER in the usb.org document)
    b'\x00'    # VT \v
    b'\x00'    # FF \f
    b'\x00'    # CR \r
    b'\x00'    # SO
    b'\x00'    # SI
    b'\x00'    # DLE
    b'\x00'    # DC1
    b'\x00'    # DC2
    b'\x00'    # DC3
    b'\x00'    # DC4
    b'\x00'    # NAK
    b'\x00'    # SYN
    b'\x00'    # ETB
    b'\x00'    # CAN
    b'\x00'    # EM
    b'\x00'    # SUB
    b'\x29'    # ESC
    b'\x00'    # FS
    b'\x00'    # GS
    b'\x00'    # RS
    b'\x00'    # US
    b'\x2c'    # SPACE
    b'\x9e'    # ! x1e|SHIFT_FLAG (shift 1)
    b'\xb4'    # " x34|SHIFT_FLAG (shift ')
    b'\xa0'    # # x20|SHIFT_FLAG (shift 3)
    b'\xa1'    # $ x21|SHIFT_FLAG (shift 4)
    b'\xa2'    # % x22|SHIFT_FLAG (shift 5)
    b'\xa4'    # & x24|SHIFT_FLAG (shift 7)
    b'\x34'    # '
    b'\xa6'    # ( x26|SHIFT_FLAG (shift 9)
    b'\xa7'    # ) x27|SHIFT_FLAG (shift 0)
    b'\xa5'    # * x25|SHIFT_FLAG (shift 8)
    b'\xae'    # + x2e|SHIFT_FLAG (shift =)
    b'\x36'    # ,
    b'\x2d'    # -
    b'\x37'    # .
    b'\x38'    # /
    b'\x27'    # 0
    b'\x1e'    # 1
    b'\x1f'    # 2
    b'\x20'    # 3
    b'\x21'    # 4
    b'\x22'    # 5
    b'\x23'    # 6
    b'\x24'    # 7
    b'\x25'    # 8
    b'\x26'    # 9
    b'\xb3'    # : x33|SHIFT_FLAG (shift ;)
    b'\x33'    # ;
    b'\xb6'    # < x36|SHIFT_FLAG (shift ,)
    b'\x2e'    # =
    b'\xb7'    # > x37|SHIFT_FLAG (shift .)
    b'\xb8'    # ? x38|SHIFT_FLAG (shift /)
    b'\x9f'    # @ x1f|SHIFT_FLAG (shift 2)
    b'\x84'    # A x04|SHIFT_FLAG (shift a)
    b'\x85'    # B x05|SHIFT_FLAG (etc.)
    b'\x86'    # C x06|SHIFT_FLAG
    b'\x87'    # D x07|SHIFT_FLAG
    b'\x88'    # E x08|SHIFT_FLAG
    b'\x89'    # F x09|SHIFT_FLAG
    b'\x8a'    # G x0a|SHIFT_FLAG
    b'\x8b'    # H x0b|SHIFT_FLAG
    b'\x8c'    # I x0c|SHIFT_FLAG
    b'\x8d'    # J x0d|SHIFT_FLAG
    b'\x8e'    # K x0e|SHIFT_FLAG
    b'\x8f'    # L x0f|SHIFT_FLAG
    b'\x90'    # M x10|SHIFT_FLAG
    b'\x91'    # N x11|SHIFT_FLAG
    b'\x92'    # O x12|SHIFT_FLAG
    b'\x93'    # P x13|SHIFT_FLAG
    b'\x94'    # Q x14|SHIFT_FLAG
    b'\x95'    # R x15|SHIFT_FLAG
    b'\x96'    # S x16|SHIFT_FLAG
    b'\x97'    # T x17|SHIFT_FLAG
    b'\x98'    # U x18|SHIFT_FLAG
    b'\x99'    # V x19|SHIFT_FLAG
    b'\x9a'    # W x1a|SHIFT_FLAG
    b'\x9b'    # X x1b|SHIFT_FLAG
    b'\x9c'    # Y x1c|SHIFT_FLAG
    b'\x9d'    # Z x1d|SHIFT_FLAG
    b'\x2f'    # [
    b'\x31'    # \ backslash
    b'\x30'    # ]
    b'\xa3'    # ^ x23|SHIFT_FLAG (shift 6)
    b'\xad'    # _ x2d|SHIFT_FLAG (shift -)
    b'\x35'    # `
    b'\x04'    # a
    b'\x05'    # b
    b'\x06'    # c
    b'\x07'    # d
    b'\x08'    # e
    b'\x09'    # f
    b'\x0a'    # g
    b'\x0b'    # h
    b'\x0c'    # i
    b'\x0d'    # j
    b'\x0e'    # k
    b'\x0f'    # l
    b'\x10'    # m
    b'\x11'    # n
    b'\x12'    # o
    b'\x13'    # p
    b'\x14'    # q
    b'\x15'    # r
    b'\x16'    # s
    b'\x17'    # t
    b'\x18'    # u
    b'\x19'    # v
    b'\x1a'    # w
    b'\x1b'    # x
    b'\x1c'    # y
    b'\x1d'    # z
    b'\xaf'    # { x2f|SHIFT_FLAG (shift [)
    b'\xb1'    # | x31|SHIFT_FLAG (shift \)
    b'\xb0'    # } x30|SHIFT_FLAG (shift ])
    b'\xb5'    # ~ x35|SHIFT_FLAG (shift `)
    b'\x4c'    # DEL DELETE (called Forward Delete in usb.org document)
)



class KeyboardModifiers(IntFlag):
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
    def get_scancode_for_ascii(cls, letter_or_code):
        """ Returns the (modifiers, scancode) used to type a given ASCII letter. """

        # Look up the relevant ASCII code in our table.
        ascii_code = letter_or_code if isinstance(letter_or_code, int) else ord(letter_or_code)
        composite = _ASCII_TO_KEYCODE[ascii_code]

        # The Adafruit table uses bits [6:0] to indicate keycode; and bit [7] to indicate
        # if shift is necessary.
        modifiers = KeyboardModifiers.MOD_LEFT_SHIFT if (composite & 0x80) else 0
        scancode  = composite & 0x7F

        return (modifiers, scancode)
