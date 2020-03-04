#!/usr/bin/env python3
#
# Interactive keyboard.
#
# Andrey Konovalov <andreyknvl@gmail.com>

import curses

try:
    screen = curses.initscr()
    screen.nodelay(True)
    screen.keypad(True)
    screen.scrollok(True)
    curses.noecho()
    curses.raw()
finally:
    curses.endwin()

# Replace the print builtin to not let curses mess up facedancer logs.

class PrintWrapper:
    def __init__(self):
        def fake_print(*args):
                screen.addstr(' '.join([str(arg) for arg in args]) + '\n')
                screen.refresh()
        self.original = __builtins__.__dict__['print']
        self.fake = fake_print

    def replace_print(self):
        __builtins__.__dict__['print'] = self.fake

    def restore_print(self):
        __builtins__.__dict__['print'] = self.original

print_wrapper = PrintWrapper()
print_wrapper.replace_print()

# Map curses key codes to USB HID key codes according to:
# https://www.usb.org/sites/default/files/documents/hut1_12v2.pdf

codes_mapping = {}

KEY_DEFAULT_MASK = 0
KEY_CTRL_MASK    = 1
KEY_SHIFT_MASK   = 2
KEY_ALT_MASK     = 4

# <KEY>
for code in range(ord('a'), ord('z') + 1):
    char = code
    codes_mapping[code] = bytes((KEY_DEFAULT_MASK, 0, char - ord('a') + 4))

# <CTRL + KEY>
for code in range(1, 26 + 1):
    char = code - 1 + ord('a')
    codes_mapping[code] = bytes((KEY_CTRL_MASK, 0, char - ord('a') + 4))

# <SHIFT + KEY>
for code in range(ord('A'), ord('Z') + 1):
    char = ord(chr(code).lower())
    codes_mapping[code] = bytes((KEY_SHIFT_MASK, 0, char - ord('a') + 4))

codes_mapping[ord('0')] = bytes((KEY_DEFAULT_MASK, 0, 0x27))
codes_mapping[ord('1')] = bytes((KEY_DEFAULT_MASK, 0, 0x1e))
codes_mapping[ord('2')] = bytes((KEY_DEFAULT_MASK, 0, 0x1f))
codes_mapping[ord('3')] = bytes((KEY_DEFAULT_MASK, 0, 0x20))
codes_mapping[ord('4')] = bytes((KEY_DEFAULT_MASK, 0, 0x21))
codes_mapping[ord('5')] = bytes((KEY_DEFAULT_MASK, 0, 0x22))
codes_mapping[ord('6')] = bytes((KEY_DEFAULT_MASK, 0, 0x23))
codes_mapping[ord('7')] = bytes((KEY_DEFAULT_MASK, 0, 0x24))
codes_mapping[ord('8')] = bytes((KEY_DEFAULT_MASK, 0, 0x25))
codes_mapping[ord('9')] = bytes((KEY_DEFAULT_MASK, 0, 0x26))

codes_mapping[ord(')')] = bytes((KEY_SHIFT_MASK, 0, 0x27))
codes_mapping[ord('!')] = bytes((KEY_SHIFT_MASK, 0, 0x1e))
codes_mapping[ord('@')] = bytes((KEY_SHIFT_MASK, 0, 0x1f))
codes_mapping[ord('#')] = bytes((KEY_SHIFT_MASK, 0, 0x20))
codes_mapping[ord('$')] = bytes((KEY_SHIFT_MASK, 0, 0x21))
codes_mapping[ord('%')] = bytes((KEY_SHIFT_MASK, 0, 0x22))
codes_mapping[ord('^')] = bytes((KEY_SHIFT_MASK, 0, 0x23))
codes_mapping[ord('&')] = bytes((KEY_SHIFT_MASK, 0, 0x24))
codes_mapping[ord('*')] = bytes((KEY_SHIFT_MASK, 0, 0x25))
codes_mapping[ord('(')] = bytes((KEY_SHIFT_MASK, 0, 0x26))

codes_mapping[ord('\n')] = bytes((KEY_DEFAULT_MASK, 0, 0x28))  # <ENTER>
codes_mapping[0x1b] = bytes((KEY_DEFAULT_MASK, 0, 0x29))       # <ESCAPE>

codes_mapping[curses.KEY_BACKSPACE] = bytes((KEY_DEFAULT_MASK, 0, 0x2a))

codes_mapping[ord('\t')] = bytes((KEY_DEFAULT_MASK, 0, 0x2b))
codes_mapping[ord(' ')] = bytes((KEY_DEFAULT_MASK, 0, 0x2c))

codes_mapping[ord('-')] = bytes((KEY_DEFAULT_MASK, 0, 0x2d))
codes_mapping[ord('_')] = bytes((KEY_SHIFT_MASK, 0, 0x2d))

codes_mapping[ord('=')] = bytes((KEY_DEFAULT_MASK, 0, 0x2e))
codes_mapping[ord('+')] = bytes((KEY_SHIFT_MASK, 0, 0x2e))

codes_mapping[ord('[')] = bytes((KEY_DEFAULT_MASK, 0, 0x2f))
codes_mapping[ord('{')] = bytes((KEY_SHIFT_MASK, 0, 0x2f))

codes_mapping[ord(']')] = bytes((KEY_DEFAULT_MASK, 0, 0x30))
codes_mapping[ord('}')] = bytes((KEY_SHIFT_MASK, 0, 0x30))

codes_mapping[ord('\\')] = bytes((KEY_DEFAULT_MASK, 0, 0x31))
codes_mapping[ord('|')] = bytes((KEY_SHIFT_MASK, 0, 0x31))

codes_mapping[ord(';')] = bytes((KEY_DEFAULT_MASK, 0, 0x33))
codes_mapping[ord(':')] = bytes((KEY_SHIFT_MASK, 0, 0x33))

codes_mapping[ord('\'')] = bytes((KEY_DEFAULT_MASK, 0, 0x34))
codes_mapping[ord('"')] = bytes((KEY_SHIFT_MASK, 0, 0x34))

codes_mapping[ord('`')] = bytes((KEY_DEFAULT_MASK, 0, 0x35))
codes_mapping[ord('~')] = bytes((KEY_SHIFT_MASK, 0, 0x35))

codes_mapping[ord(',')] = bytes((KEY_DEFAULT_MASK, 0, 0x36))
codes_mapping[ord('<')] = bytes((KEY_SHIFT_MASK, 0, 0x36))

codes_mapping[ord('.')] = bytes((KEY_DEFAULT_MASK, 0, 0x37))
codes_mapping[ord('>')] = bytes((KEY_SHIFT_MASK, 0, 0x37))

codes_mapping[ord('.')] = bytes((KEY_DEFAULT_MASK, 0, 0x37))
codes_mapping[ord('>')] = bytes((KEY_SHIFT_MASK, 0, 0x37))

codes_mapping[ord('/')] = bytes((KEY_DEFAULT_MASK, 0, 0x38))
codes_mapping[ord('?')] = bytes((KEY_SHIFT_MASK, 0, 0x38))

codes_mapping[curses.KEY_DC] = bytes((KEY_DEFAULT_MASK, 0, 0x4c))  # <DELETE>

codes_mapping[curses.KEY_RIGHT] = bytes((KEY_DEFAULT_MASK, 0, 0x4f))
codes_mapping[curses.KEY_LEFT] = bytes((KEY_DEFAULT_MASK, 0, 0x50))
codes_mapping[curses.KEY_DOWN] = bytes((KEY_DEFAULT_MASK, 0, 0x51))
codes_mapping[curses.KEY_UP] = bytes((KEY_DEFAULT_MASK, 0, 0x52))

# Define USB interface and device.

from USBKeyboard import *

class InteractiveUSBKeyboardInterface(USBKeyboardInterface):
    def __init__(self, verbose=0):
        USBKeyboardInterface.__init__(self, verbose)
        self.keys = []

    def handle_buffer_available(self):
        code = screen.getch()
        if code == 29:  # <CTRL + ]>
            raise KeyboardInterrupt
        if code in codes_mapping.keys():
            self.keys.append(codes_mapping[code])                 # <KEY DOWN>
            self.keys.append(bytes((KEY_DEFAULT_MASK, 0, 0x00)))  # <KEY UP>

        if len(self.keys) == 0:
            return
        data = self.keys.pop(0)
        if self.verbose > 2:
            print(self.name, "sending keypress {}".format(data))
        self.endpoint.send(data)

class InteractiveUSBKeyboardDevice(USBKeyboardDevice):
    def __init__(self, maxusb_app, verbose=0):
        config = USBConfiguration(
                1,
                "Emulated Keyboard",
                [ InteractiveUSBKeyboardInterface(verbose=verbose) ]
        )
        USBKeyboardDevice.__init__(self, maxusb_app, verbose, config)

# Run. Press CTRL+] to exit.

from facedancer import FacedancerUSBApp

try:
    u = FacedancerUSBApp(verbose=1)
    d = InteractiveUSBKeyboardDevice(u, verbose=5)
    d.connect()
    try:
        d.run()
    except KeyboardInterrupt:
        d.disconnect()
finally:
    print_wrapper.restore_print()
    curses.endwin()
