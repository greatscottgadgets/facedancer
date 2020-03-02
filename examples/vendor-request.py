#
# This file is part of FaceDancer.
#

from facedancer.device      import default_main
from facedancer.future      import USBDevice, vendor_request_handler
from facedancer.future      import use_inner_classes_automatically


@use_inner_classes_automatically
class VendorOnlyDevice(USBDevice):

    name           : str = "Proprietary Company"
    product_string : str = "Very vendor device"

    vendor_id      : int = 0x3456
    product_id     : int = 0x1234


    @vendor_request_handler(number=3)
    def handle_silly_request(self, request):

        # NOTE: these are the old names; this will be cleaned up
        self.send_control_message(b"1234")
        self.ack_status_stage()


