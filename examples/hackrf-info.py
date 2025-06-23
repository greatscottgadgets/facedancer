#!/usr/bin/env python3
# pylint: disable=unused-wildcard-import, wildcard-import
#
# This file is part of Facedancer.
#

from facedancer import *
from facedancer import main


@use_inner_classes_automatically
class HackRF(USBDevice):
    """ Device that emulates a HackRF enough to appear in ``hackrf_info``.

    You can try to create this script yourself! It's relatively easy using the
    --suggest option and the ``template.py`` example.
    """

    # Show up as a HackRF.
    product_string      : str = "HackRF One (Emulated)"
    manufacturer_string : str = "Great Scott Gadgets"
    vendor_id           : int = 0x1d50
    product_id          : int = 0x6089

    # Most hosts won't accept a device unless it has a configuration
    # and an interface. We'll add some default/empty ones. Facedancer
    # provides sane defaults, so we don't need to do anything else!
    class DefaultConfiguration(USBConfiguration):
        class DefaultInterface(USBInterface):
            pass

    #
    # Vendor requests.
    #
    # These templates were generated using --suggest, and then modified
    # by the author to get the functionality she wanted.
    #
    @vendor_request_handler(number=14, direction=USBDirection.IN)
    @to_device
    def handle_control_request_14(self, request):

        # The --suggest command gives us the following info:
        # Most recent request was for 1B of data.

        # Theoretically, this is the point where you'd experiment
        # with providing one-byte responses and see what `hackrf_info` does.
        request.reply(bytes([2]))


    #
    # From here on out, we'll give these requests more descriptive names,
    # rather than using the ones from --suggest. When creating this, we'd
    # theoretically do our reverse engineering, and then rename the request.
    #
    # Because the decorator indicates to the backend that this is a vendor
    # request handler, these names can be whatever we'd like -- and we don't
    # have to update anything when we change them!
    #
    @vendor_request_handler(number=15, direction=USBDirection.IN)
    @to_device
    def handle_get_version_request(self, request):
        # Most recent request was for 255B of data.

        # When hackrf_info gets to this point, we can see that it's
        # failing with "hackrf_version_string_read() failed: Pipe error (-1000)."
        #
        # That's a pretty good hint of what it expects.
        request.reply(b"Sekret Facedancer Version")


    @vendor_request_handler(number=18, direction=USBDirection.IN)
    @to_device
    def handle_get_serial_request(self, request):
        # Most recent request was for 24B of data.
        request.reply(b'A' * 24)


    #
    # There's one last thing to do -- we'll need to implement one more
    # simple request. We'll leave this last one as an exercise to the reader. :)
    #


main(HackRF)
