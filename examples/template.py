#!/usr/bin/env python3
# pylint: disable=unused-wildcard-import, wildcard-import
#
# This file is part of Facedancer.
#
""" Example template for creating new Facedancer devices. """

import logging

from facedancer         import main
from facedancer         import *
from facedancer.classes import USBDeviceClass

@use_inner_classes_automatically
class TemplateDevice(USBDevice):
    """ This class is meant to act as a template to help you get acquainted with Facedancer."""

    #
    # Core 'dataclass' definitions.
    # These define the basic way that a Facedancer device advertises itself to the host.
    #
    # Every one of these is optional. The defaults are relatively sane, so you can mostly
    # ignore these unless you want to change them! See the other examples for more minimal
    # data definitions.
    #

    # The USB device class, subclass, and protocol for the given device.
    # Often, we'll leave these all set to 0, which means the actual class is read
    # from the interface.
    #
    # Note that we _need_ the type annotations on these. Without them, Python doesn't
    # consider them valid dataclass members, and ignores them. (This is a detail of python3.7+
    # dataclasses.)
    #
    device_class             : int  = 0
    device_subclass          : int  = 0
    protocol_revision_number : int  = 0

    # The maximum packet size on EP0. For most devices, the default value of 64 is fine.
    max_packet_size_ep0      : int  = 64

    # The vendor ID and product ID that we want to give our device.
    vendor_id                : int  = 0x610b
    product_id               : int  = 0x4653

    # The string descriptors we'll provide for our device.
    # Note that these should be Python strings, and _not_ bytes.
    manufacturer_string      : str  = "Facedancer"
    product_string           : str  = "Generic USB Device"
    serial_number_string     : str  = "S/N 3420E"

    # This tuple is a list of languages we're choosing to support.
    # This gives us an opportunity to provide strings in various languages.
    # We don't typically use this; so we can leave this set to a language of
    # your choice.
    supported_languages      : tuple = (LanguageIDs.ENGLISH_US,)

    # The revision of the device hardware. This doesn't matter to the USB specification,
    # but it's sometimes read by drivers. 0x0001 represents "0.1" in BCD.
    device_revision          : int  = 0x0001

    # The revision of the USB specification that this device adheres to.
    # Typically, you'll leave this at 0x0200 which represents "2.0" in BCD.
    usb_spec_version         : int  = 0x0200


    #
    # We'll define a single configuration on our device. To be compliant,
    # every device needs at least a configuration and an interface.
    #
    # Note that we don't need to do anything special to have this be used.
    # As long as we're using the @use_inner_classes_automatically decorator,
    # this configuration will automatically be instantiated and used.
    #
    class TemplateConfiguration(USBConfiguration):

        #
        # Configuration fields.
        #
        # Again, all of these are optional; and the default values
        # are sane and useful.
        #

        # Configuration number. Every configuration should have a unique
        # number, which should count up from one. Note that a configuration
        # shouldn't have a number of 0, as that's USB for "unconfigured".
        configuration_number : int            = 1

        # A simple, optional descriptive name for the configuration. If provided,
        # this is referenced in the configuration's descriptor.
        configuration_string : str            = None

        # This setting is set to true if the device can run without bus power,
        # or false if it pulls its power from the USB bus.
        self_powered           : bool         = False

        # This setting is set to true if the device can ask that the host
        # wake it up from sleep. If set to true, the host may choose to
        # leave power on to the device when the host is suspended.
        supports_remote_wakeup : bool         = True

        # The maximum power the device will use in this configuration, in mA.
        # Typically, most devices will request 500mA, the maximum allowed.
        max_power              : int            = 500


        class TemplateInterface(USBInterface):

            #
            # Interface fields.
            # Again, all optional and with useful defaults.
            #

            # The interface index. Each interface should have a unique index,
            # starting from 0.
            number                 : int = 0

            # The information about the USB class implemented by this interface.
            # This is the place where you'd specify if this is e.g. a HID device.
            class_number           : int = USBDeviceClass.VENDOR_SPECIFIC
            subclass_number        : int = 0
            protocol_number        : int = 0

            # A short description of the interface. Optional and typically only informational.
            interface_string       : str = None


            #
            # Here's where we define any endpoints we want to add to the device.
            # These behave essentially the same way as the above.
            #
            class TemplateInEndpoint(USBEndpoint):

                #
                # Endpoints are unique in that they have two _required_
                # properties -- their number and direction.
                #
                # Together, these two fields form the endpoint's address.
                # Endpoint numbers should be > 0, since endpoint 0 is reserved as the default pipe by the spec.
                number               : int                    = 1
                direction            : USBDirection           = USBDirection.IN

                #
                # The remainder of the fields are optional and have useful defaults.
                #

                # The transfer type selects how data will be transferred over the endpoints.
                # The currently supported types are BULK and INTERRUPT.
                transfer_type        : USBTransferType        = USBTransferType.BULK

                # The maximum packet size determines how large packets are allowed to be.
                # For a full speed device, a max-size value of 64 is typical.
                max_packet_size      : int = 64

                # For interrupt endpoints, the interval specifies how often the host should
                # poll the endpoint, in milliseconds. 10ms is a typical value.
                interval             : int = 0


                #
                # Let's add an event handler. This one is called whenever the host
                # wants to read data from the device.
                #
                def handle_data_requested(self):

                    # We can reply to this request using the .send() method on this
                    # endpoint, like so:
                    self.send(b"Hello!")

                    # We can also get our parent interface using .parent;
                    # or a reference to our device using .get_device().


            class TemplateOutEndpoint(USBEndpoint):
                #
                # We'll use a more typical set of properties for our OUT endpoint.
                #
                number               : int                    = 1
                direction            : USBDirection           = USBDirection.OUT


                #
                # We'll also demonstrate use of another event handler.
                # This one is called whenever data is sent to this endpoint.
                #
                def handle_data_received(self, data):
                    logging.info(f"Received data: {data}")


    #
    # Any of our components can use callback functions -- not just our endpoints!
    # The callback names are the same no matter where we use them.
    #
    def handle_data_received(self, endpoint, data):

        #
        # When using a callback on something other than an endpoint, our function's
        # signature is slightly different -- it takes the relevant endpoint as an
        # argument, as well.
        #

        # We'll delegate this back to the core handler, here, so it propagates to our subordinate
        # endpoints -- but we don't have to! If we wanted to, we could call functions on the
        # endpoint itself. This is especially useful if we're hooking handle_data_requested(),
        # where we can use endpoint.send() to provide the relevant data.
        super().handle_data_received(endpoint, data)

        # Note that non-endpoints have a get_endpoint() method, which you can use to get references
        # to endpoints by their endpoint numbers / directions. This is useful if you want to
        # send something on another endpoint in response to data received.
        #
        # The device also has a .send() method, which accepts an endpoint number and the data to
        # be sent. This is equivalent to calling .send() on the relevant endpoint.


    #
    # We can very, very easily add request handlers to our devices.
    #
    @vendor_request_handler(number=12)
    def handle_my_request(self, request):

        #
        # By decorating this function with "vendor_request_handler", we've ensured this
        # function is called to handle vendor request 12. We can also add other arguments to
        # the vendor_request_handler function -- it'll accept a keyword argument for every
        # property on the request. If you provide these, the handler will only be called
        # if the request matches the relevant constraint.
        #
        # For example, @vendor_request_handler(number=14, direction=USBDirection.IN, index_low=3)
        # means the decorated function is only called to handle vendor request 14 for IN requests
        # where the low byte of the index is 3.
        #
        # Other handler decorators exist -- like "class_request_handler" or "standard_request_handler"
        #

        # Replying to an IN request is easy -- you just provide the reply data using request.reply().
        request.reply(b"Hello, there!")


    @vendor_request_handler(number=1, direction=USBDirection.OUT)
    @to_device
    def handle_another_request(self, request):

        #
        # Another set of convenience decorators exist to refine requests.
        # Decorators like `to_device` or `to_any_endpoint` chain with our
        # request decorators, and are syntax sugar for having an argument like
        # ``recipient=USBRequestRecipient.DEVICE`` in the handler decorator.
        #

        # For out requests, in lieu of a response, we typically want to acknowledge
        # the request. This can be accomplished by calling .acknowledge() or .ack()
        # on the request.
        request.ack()

        # Of course, if we want to let the host know we can't handle a request, we
        # may also choose to stall it. This is as simple as calling request.stall().


    #
    # Note that request handlers can be used on configurations, interfaces, and
    # endpoints as well. For the latter two cases, the decorators `to_this_interface`
    # and `to_this_endpoint` are convenient -- they tell a request to run only if
    # it's directed at that endpoint in particular, as selected by its ``index`` parameter.
    #


# Facedancer ships with a default main() function that you can use to set up and run
# your device. It ships with some nice features -- including a ``--suggest`` function
# that can suggest pieces of boilerplate code that might be useful in device emulation.
#
# main() will accept either the type of device to emulate, or an device instance.
# It'll also accept asyncio coroutines, in case you want to run things alongside the
# relevant device code. See e.g. `examples/rubber-ducky.py` for an example.
#
main(TemplateDevice)


#
# Of course, this template looks verbose as heck.
# For an example that's much less verbose, check out `examples/hackrf-info.py`.
#
