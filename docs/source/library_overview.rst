================================================
Library Overview
================================================

The Facedancer library may be somewhat overwhelming at first but the modules can be broken down into a number of clearly delineated categories:


Core USB Device Model
~~~~~~~~~~~~~~~~~~~~~

These packages contain the functionality used to define devices and their organisation closely mirrors the hierarchical USB device model:

.. code-block:: text

    +--------------------------------+
    | USB Device                     |
    |   - Device Descriptor          |
    |   - Configuration Descriptor   |
    |      - Interface Descriptor    |     +----------------------------------+
    |         - Endpoint Descriptor  |     | Host                             |
    |           - Request Handler    | --> |   - Function                     |
    |         - Endpoint Descriptor  |     |                                  |
    |           - Request Handler    | <-- |   - Function                     |
    |   - Control Interface          |     |                                  |
    |      - Request Handlers        | <-> |   - Enumeration, Status, Command |
    +--------------------------------+     +----------------------------------+

    (simplified diagram for didactic purposes, not drawn to scale)

* :mod:`facedancer.device`
    -- :class:`~facedancer.device.USBDevice` is the device root. It is responsible for managing the device's descriptors and marshalling host requests.
* :mod:`facedancer.configuration`
    -- :class:`~facedancer.configuration.USBConfiguration` is responsible for managing the device's configuration descriptor(s).
* :mod:`facedancer.interface`
    -- :class:`~facedancer.interface.USBInterface` is responsible for managing the device's interface descriptor(s).
* :mod:`facedancer.endpoint`
    -- :class:`~facedancer.endpoint.USBEndpoint` is responsible for managing the device's endpoints.
* :mod:`facedancer.request`
    -- :class:`~facedancer.request.USBControlRequest` is responsible for managing USB control transfers.

In addition to the core device model there are also two modules containing support functionality:

* :mod:`facedancer.descriptor`
    -- contains functionality for working with USB descriptors.
* :mod:`facedancer.magic`
    -- contains functionality for Facedancer's declarative device definition syntax.



Device Emulation Support
~~~~~~~~~~~~~~~~~~~~~~~~

These modules contain a small selection of example USB device classes and device emulations.

* :mod:`facedancer.classes`
* :mod:`facedancer.devices`



USB Proxy
~~~~~~~~~

These modules contain the USB Proxy implementation.

* :mod:`facedancer.proxy`
    -- contains the :class:`~facedancer.proxy.USBProxyDevice` implementation.
* :mod:`facedancer.filters`
    -- contains a selection of filters to intercept, view or modify proxied USB transfers.



Facedancer Board Backends
~~~~~~~~~~~~~~~~~~~~~~~~~

Contains backend implementations for the various supported Facedancer boards.

* :mod:`facedancer.backends`



Supporting Functionality
~~~~~~~~~~~~~~~~~~~~~~~~

* :mod:`facedancer.core`
    -- the Facedancer scheduler and execution core.
* :mod:`facedancer.errors`
    -- an error type, there should probably be more.
* :mod:`facedancer.types`
    -- various type definitions and constants.
* :mod:`facedancer.logging`
    -- logging boilerplate.
