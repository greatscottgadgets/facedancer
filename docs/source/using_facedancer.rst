================================================
Using Facedancer
================================================

Facedancer allows you to

Introduction
------------

Facedancer makes it possible to define emulations using a simple declarative DSL that mirrors the hierarchical structure of the abstract USB device model.

Let's look at a simple example that defines a USB device with two endpoints and a control interface:

.. literalinclude:: ../../examples/minimal.py
   :language: python
   :lines: 7-
   :lineno-start: 7
   :linenos:


Device Descriptor
-----------------

The entry-point for most Facedancer emulations is the :class:`~facedancer.device.USBDevice` class which maintains the configuration as well as the transfer handling implementation of the device under emulation.

.. note::

    In some cases you may want to use the :class:`~facedancer.device.USBBaseDevice` class if you'd like to
    provide your own implementation of the standard request handlers.

    See, for example, :class:`~facedancer.proxy.USBProxyDevice`.


Starting with the initial class declaration we can define our device as:

.. code-block:: python

    from facedancer import *

    @use_inner_classes_automatically
    class MyDevice(USBDevice):
        product_string      : str = "Example USB Device"
        manufacturer_string : str = "Facedancer"
        vendor_id           : int = 0x1209 # https://pid.codes/1209/
        product_id          : int = 0x0001

We start by importing the Facedancer library and declaring a class `MyDevice` derived from :class:`~facedancer.device.USBDevice`.

We also annotate our class with the :func:`@use_inner_classes_automatically <facedancer.magic.use_inner_classes_automatically>` decorator which allows us to use a declarative style when including our devices configuration, interface and endpoints. It's  :mod:`~facedancer.magic`!

Finally, we fill in some basic fields Facedancer will use to populate the device descriptor: ``product_string``, ``manufacturer_string``, ``vendor_id`` and ``product_id``.

.. note:: You can find a full list of supported fields in the :class:`~facedancer.device.USBDevice` API documentation.



Configuration Descriptor
------------------------

Once we have provided Facedancer with the basic information it needs to build a device descriptor we can move on to declare and define our device's configuration descriptor.

Most devices consist of a single configuration managed by the :class:`~facedancer.configuration.USBConfiguration` class containing at least one :class:`~facedancer.interface.USBInterface` class containing zero or more   :class:`~facedancer.endpoint.USBEndpoint` class.

Here we define a configuration with a single interface containing two endpoints. The first endpoint has direction :class:`~facedancer.types.USBDirection.IN` and will be responsible for responding to data requests from the host. The second endpoint has direction :class:`~facedancer.types.USBDirection.OUT` and will be responsible for receiving data from the host.

.. code-block:: python
    :emphasize-lines: 5-

    ...
    class MyDevice(USBDevice):
        ...

        class MyConfiguration(USBConfiguration):
            class MyInterface(USBInterface):
                class MyInEndpoint(USBEndpoint):
                    number    : int          = 1
                    direction : USBDirection = USBDirection.IN
                class MyOutEndpoint(USBEndpoint):
                    number    : int          = 1
                    direction : USBDirection = USBDirection.OUT

We've now provided enough information in our emulation for it to be successfully enumerated and recognized by the host but there is still one thing missing!



Request Handlers
----------------

For our device to actually do something we also need a way to:

* Respond to a request for data from the host.
* Receive data sent by the host.

.. note:: USB is a polled protocol where the host always initiates all transactions. Data will only ever be sent from the device if the host has first requested it from the device.

The Facedancer :mod:`facedancer.endpoint` and :mod:`facedancer.request` modules provides the functionality for responding to requests on the device's endpoints and the control interface. (All USB devices support a control endpoint -- usually endpoint zero.)


Endpoint Request Handlers
~~~~~~~~~~~~~~~~~~~~~~~~~

Endpoint request handlers are usually either class-specific or vendor-defined and can be declared inside the device's endpoint declaration.

Here we will define two simple handlers for each endpoint.

For our IN endpoint we will reply to any data request from the host with a fixed message and for our OUT endpoint we will just print the received data to the terminal.

.. code-block:: python
    :emphasize-lines: 11-13, 19-21

    ...
    class MyDevice(USBDevice):
        ...

        class MyConfiguration(USBConfiguration):
            class MyInterface(USBInterface):
                class MyInEndpoint(USBEndpoint):
                    number    : int          = 1
                    direction : USBDirection = USBDirection.IN

                    # called when the host requested data from the device on endpoint 0x81
                    def handle_data_requested(self: USBEndpoint):
                        self.send(b"device sent response on bulk endpoint", blocking=True)

                class MyOutEndpoint(USBEndpoint):
                    number    : int          = 1
                    direction : USBDirection = USBDirection.OUT

                    # called when the host sent data to the device on endpoint 0x01
                    def handle_data_received(self: USBEndpoint, data):
                        logging.info(f"device received '{data}' on bulk endpoint")

For more information on supported endpoint operations and fields see the :class:`~facedancer.endpoint.USBEndpoint` documentation.


Control Request Handlers
~~~~~~~~~~~~~~~~~~~~~~~~

Control Requests are typically used for command and status operations. While Facedancer will take care of responding to standard control requests used for device enumeration you may also want to implement custom vendor requests or even override standard control request handling.

To this end, Facedancer provides two sets of decorators to be used when defining a device's control interface:

The first set of decorators allows you to specify the type of control request to be handled:

* :func:`@control_request_handler <facedancer.request.control_request_handler>`
* :func:`@standard_request_handler <facedancer.request.standard_request_handler>`
* :func:`@vendor_request_handler <facedancer.request.vendor_request_handler>`
* :func:`@class_request_handler <facedancer.request.class_request_handler>`
* :func:`@reserved_request_handler <facedancer.request.reserved_request_handler>`

The second set defines the target for the control request:

* :func:`@to_device <facedancer.request.to_device>`
* :func:`@to_this_endpoint <facedancer.request.to_this_endpoint>`
* :func:`@to_any_endpoint <facedancer.request.to_any_endpoint>`
* :func:`@to_this_interface <facedancer.request.to_this_interface>`
* :func:`@to_any_interface <facedancer.request.to_any_interface>`
* :func:`@to_other <facedancer.request.to_other>`

For instance, to define some vendor request handlers you can do:

.. code-block:: python
    :emphasize-lines: 7-

    ...
    class MyDevice(USBDevice):
        ...
        class MyConfiguration(USBConfiguration):
        ...

        @vendor_request_handler(request_number=1, direction=USBDirection.IN)
        @to_device
        def my_vendor_request_handler(self: USBDevice, request: USBControlRequest):
            request.reply(b"device sent response on control endpoint")

        @vendor_request_handler(request_number=2, direction=USBDirection.OUT)
        @to_device
        def my_other_vendor_request_handler(self: USBDevice, request: USBControlRequest):
            logging.info(f"device received '{request.index}' '{request.value}' '{request.data}' on control endpoint")

            # acknowledge the request
            request.ack()

More information on the ``request`` parameter can be found in the :class:`~facedancer.request.USBControlRequest` documentation.


Testing The Emulation
---------------------

We now have a full USB device emulation that will enumerate and respond to requests from the host.

Give it a try!

.. literalinclude:: ../../examples/test_minimal.py
   :language: python
   :linenos:


Suggestion Engine
-----------------

Facedancer provides a suggestion engine that can help when trying to map an undocumented device's control interface.

It works by monitoring the control requests from the host and tracking any which are not supported by your emulation.

You can enable it by passing the `--suggest` flag when running an emulation:

.. code-block:: shell

    python ./emulation.py --suggest

When you exit the emulation it can then suggest the handler functions you still need to implement in order to support the emulated device's control interface:

.. code-block:: text

    Automatic Suggestions
    ---------------------
    These suggestions are based on simple observed behavior;
    not all of these suggestions may be useful / desirable.

    Request handler code:

    @vendor_request_handler(number=1, direction=USBDirection.IN)
    @to_device
    def handle_control_request_1(self, request):
        # Most recent request was for 64B of data.
        # Replace me with your handler.
        request.stall()


Annotated template
------------------

The Facedancer repository contains an :example:`annotated template <template.py>` which provides an excellent reference source when building your own devices:

.. literalinclude:: ../../examples/template.py
   :language: python
   :lines: 8-276
   :lineno-start: 8
   :linenos:
