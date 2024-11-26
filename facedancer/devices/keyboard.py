# pylint: disable=unused-wildcard-import, wildcard-import
#
# This file is part of Facedancer.
#

import asyncio

from typing                   import Iterable

from .                        import default_main

from ..                       import *
from ..classes.hid.usage      import *
from ..classes.hid.descriptor import *
from ..classes.hid.keyboard   import *


# Specifies how many simultaneously keys we want to support.
KEY_ROLLOVER = 8


@use_inner_classes_automatically
class USBKeyboardDevice(USBDevice):
    """ Simple USB keyboard device. """

    name           : str = "USB keyboard device"
    product_string : str = "Non-suspicious Keyboard"


    class KeyboardConfiguration(USBConfiguration):
        """ Primary USB configuration: act as a keyboard. """


        class KeyboardInterface(USBInterface):
            """ Core HID interface for our keyboard. """

            name         : str = "USB keyboard interface"
            class_number : int = 3


            class KeyEventEndpoint(USBEndpoint):
                number        : int             = 3
                direction     : USBDirection    = USBDirection.IN
                transfer_type : USBTransferType = USBTransferType.INTERRUPT
                interval      : int             = 10


            #
            # Raw descriptors -- TODO: build these from their component parts.
            #


            class HIDDescriptor(USBDescriptor):
                number            : int   = 0
                type_number       : int   = USBDescriptorTypeNumber.HID
                raw               : bytes = b'\x09\x21\x10\x01\x00\x01\x22\x2b\x00'
                include_in_config : bool  = True


            class ReportDescriptor(HIDReportDescriptor):
                number : int   =  0
                fields : tuple = (

                    # Identify ourselves as a keyboard.
                    USAGE_PAGE       (HIDUsagePage.GENERIC_DESKTOP),
                    USAGE            (HIDGenericDesktopUsage.KEYBOARD),
                    COLLECTION       (HIDCollection.APPLICATION),
                    USAGE_PAGE       (HIDUsagePage.KEYBOARD),

                    # Modifier keys.
                    # These span the full range of modifier key codes (left control to right meta),
                    # and each has two possible values (0 = unpressed, 1 = pressed).
                    USAGE_MINIMUM    (KeyboardKeys.LEFTCTRL),
                    USAGE_MAXIMUM    (KeyboardKeys.RIGHTMETA),
                    LOGICAL_MINIMUM  (0),
                    LOGICAL_MAXIMUM  (1),
                    REPORT_SIZE      (1),
                    REPORT_COUNT     (KeyboardKeys.RIGHTMETA - KeyboardKeys.LEFTCTRL + 1),
                    INPUT            (variable=True),

                    # One byte of constant zero-padding.
                    # This is required for compliance; and Windows will ignore this report
                    # if the zero byte isn't present.
                    REPORT_SIZE      (8),
                    REPORT_COUNT     (1),
                    INPUT            (constant=True),

                    # Capture our actual, pressed keyboard keys.
                    # Support a standard, 101-key keyboard; which has
                    # keycodes from 0 (NONE) to 101 (COMPOSE).
                    #
                    # We provide the capability to press up to eight keys
                    # simultaneously. Setting the REPORT_COUNT effectively
                    # sets the key rollover; so 8 reports means we can have
                    # up to eight keys pressed at once.
                    USAGE_MINIMUM    (KeyboardKeys.NONE),
                    USAGE_MAXIMUM    (KeyboardKeys.COMPOSE),
                    LOGICAL_MINIMUM  (KeyboardKeys.NONE),
                    LOGICAL_MAXIMUM  (KeyboardKeys.COMPOSE),

                    REPORT_SIZE      (8),
                    REPORT_COUNT     (KEY_ROLLOVER),
                    INPUT            (),

                    # End the report.
                    END_COLLECTION   (),
                )


            @class_request_handler(number=USBStandardRequests.GET_INTERFACE)
            @to_this_interface
            def handle_get_interface_request(self, request):
                # Silently stall GET_INTERFACE class requests.
                request.stall()


    def __post_init__(self):
        super().__post_init__()

        # Keep track of any pressed keys, and any pressed modifiers.
        self.active_keys = set()
        self.modifiers   = 0


    def _generate_hid_report(self) -> bytes:
        """ Generates a single HID report for the given keyboard state. """

        # If we have active keypresses, compose a set of scancodes from them.
        scancodes = \
             list(self.active_keys)[:KEY_ROLLOVER] + \
             [0] * (KEY_ROLLOVER - len(self.active_keys))

        return bytes([self.modifiers, 0, *scancodes])


    def handle_data_requested(self, endpoint: USBEndpoint):
        """ Provide data once per host request. """
        report = self._generate_hid_report()
        endpoint.send(report)


    #
    # User-facing API.
    #


    def key_down(self, code: KeyboardKeys):
        """ Marks a given key as pressed; should be a scancode from KeyboardKeys. """
        self.active_keys.add(code)


    def key_up(self, code: KeyboardKeys):
        """ Marks a given key as released; should be a scancode from KeyboardKeys. """
        self.active_keys.remove(code)


    def modifier_down(self, code: KeyboardModifiers):
        """ Marks a given modifier as pressed; should be a flag from KeyboardModifiers. """
        if code is not None:
            self.modifiers |= code


    def modifier_up(self, code: KeyboardModifiers):
        """ Marks a given modifier as released; should be a flag from KeyboardModifiers. """
        if code is not None:
            self.modifiers &= ~code


    async def type_scancode(self, code: KeyboardKeys, duration: float = 0.1, modifiers: KeyboardModifiers = None):
        """ Presses, and then releases, a single key.

        Parameters:
            code      -- The keyboard key to be pressed's scancode.
            duration  -- How long the given key should be pressed, in seconds.
            modifiers -- Any modifier keys that should be held while typing.
        """

        self.modifier_down(modifiers)
        self.key_down(code)

        await asyncio.sleep(duration)

        self.key_up(code)
        self.modifier_up(modifiers)

        await asyncio.sleep(duration)


    async def type_scancodes(self, *codes: Iterable[KeyboardKeys], duration: float = 0.1):
        """ Presses, and then releases, a collection of keys, in order.

        Parameters:
            *code     -- The keyboard keys to be pressed's scancodes.
            duration  -- How long each key should be pressed, in seconds.
        """
        for code in codes:
            await self.type_scancode(code, duration=duration)


    async def type_letter(self, letter: str, duration: float = 0.1, modifiers: KeyboardModifiers = None):
        """ Attempts to type a single letter, based on its ASCII string representation.

        Parameters:
            letter    -- A single-character string literal, to be typed.
            duration  -- How long each key should be pressed, in seconds.
            modifiers -- Any modifier keys that should be held while typing.
        """
        shift, code = KeyboardKeys.get_scancode_for_ascii(letter)
        modifiers   = shift if modifiers is None else modifiers | shift

        await self.type_scancode(code, modifiers=modifiers, duration=duration)


    async def type_letters(self, *letters: Iterable[str], duration:float = 0.1):
        """ Attempts to type a string of letters, based on ASCII string representations.

        Parameters:
            *letters  -- A collection of single-character string literal, to be typed in order.
            duration  -- How long each key should be pressed, in seconds.
        """
        for letter in letters:
            await self.type_letter(letter, duration=duration)


    async def type_string(self, to_type: str, *, duration:float = 0.1, modifiers: KeyboardModifiers = None):
        """ Attempts to type a python string into the remote host.

        Parameters:
            letter    -- A collection of single-character string literal, to be typed in order.
            duration  -- How long each key should be pressed, in seconds.
            modifiers -- Any modifier keys that should be held while typing.
        """

        self.modifier_down(modifiers)

        for letter in to_type:
            await self.type_letter(letter, duration=duration)

        self.modifier_up(modifiers)


    def all_keys_up(self, *, include_modifiers: bool = True):
        """ Releases all keys currently pressed.

        Parameters:
            include_modifiers -- If set to false, modifiers will be left at their current states.
        """
        self.active_keys.clear()

        if include_modifiers:
            self.all_modifiers_up()


    def all_modifiers_up(self):
        """ Releases all modifiers currently held. """
        self.modifiers = 0


if __name__ == "__main__":
    default_main(USBKeyboardDevice)
