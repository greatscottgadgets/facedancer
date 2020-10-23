#!/usr/bin/env python3
# pylint: disable=unused-wildcard-import, wildcard-import
#
# This file is part of FaceDancer.
#
""" Example for using the imperative API. """

#
# The other FaceDancer examples tend to use the declarative API,
# as it's more succinct, and typically can be created faster.
#
# However, the new API still supports an imperative syntax,
# which may be useful in some circumstances.
#

from facedancer         import logger
from facedancer         import main
from facedancer.future  import *


class ImperativeDevice(USBDevice):

    def __init__(self):

        # We can still implement our types imperatively, like in the old API.
        super().__init__(
            vendor_id=0x1234,
            product_string="Imperatively-created Device"
        )

        # The constructor arguments to each type accept the same fields as the declarative
        # API -- and like the declarative API, parameters have sane defaults...
        configuration = USBConfiguration()
        self.add_configuration(configuration)

        #  ... which means we don't really need to do much to create the various components.
        interface = USBInterface()
        configuration.add_interface(interface)

        # Like the declarative APIs, endpoints require a number and direction.
        out_endpoint = USBEndpoint(number=3, direction=USBDirection.OUT)
        interface.add_endpoint(out_endpoint)


    #
    # We'll still use our request decorators to declare request handlers
    # on the relevant objects...
    #
    @vendor_request_handler(number=13)
    def handle_my_request(self, request):
        request.acknowledge()


    #
    # ... and callbacks continue to work the same way.
    #
    def handle_data_received(self, endpoint, data):
        logger.info(f"New data: {data} on {endpoint}.")


main(ImperativeDevice())
