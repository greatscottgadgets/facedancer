# USBVendor.py
#
# Contains class definition for USBVendor, intended as a base class (in the OO
# sense) for implementing device vendors.
from .USB import USBDescribable

class USBVendor(USBDescribable):
    name = "generic USB device vendor"

    # maps bRequest to handler function
    request_handlers = { }

    def __init__(self, phy, verbose=0):
        super(USBVendor, self).__init__(phy) 
        self.setup_request_handlers()
        self.device = None
        self.interface = None
        self.endpoint = None
        self.verbose = verbose

    def set_device(self, device):
        self.device = device

    def setup_request_handlers(self):
        self.setup_local_handlers()
        self.request_handlers = {
            x: self.handle_all for x in self.local_handlers
        }

    def setup_local_handlers(self):
        self.local_handlers = {}

    def handle_all(self, req):
        handler = self.local_handlers[req.request]
        response = handler(req)
        if response is not None:
            self.phy.send_on_endpoint(0, response)
        print('vendor specific setup request received') 