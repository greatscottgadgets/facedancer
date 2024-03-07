================================================
Using USB Proxy
================================================

Introduction
------------

A major new feature of the newer Facedancer codebase is the ability to MITM (Meddler-In-The-Middle) USB connections -- replacing the authors' original `USBProxy <https://github.com/dominicgs/usbproxy>`__ project. This opens up a whole new realm of applications -- including protocol analysis and live manipulation of USB packets -- and is especially useful when you don't control the software running on the target device (e.g. on embedded systems or games consoles).

.. code-block:: text

                     +-----------------------------------------------------------------------+
    +------------+   |  +--------------------------------+   +---------------------------+   |  +--------------+
    |            |   |  |                                |   |                           |   |  |              |
    |  PROXIED   |   |  |         HOST COMPUTER          |   |    FACEDANCER DEVICE      |   |  |  TARGET USB  |
    |   DEVICE   <------>  running Facedancer software   <--->  acts as USB-Controlled   <------>     HOST     |
    |            |   |  |                                |   |      USB Controller       |   |  |              |
    |            |   |  |                                |   |                           |   |  |              |
    +------------+   |  +--------------------------------+   +---------------------------+   |  +--------------+
                     |                                                                       |
                     |                    MITM Setup (HOST + FACEDANCER)                     |
                     +-----------------------------------------------------------------------+



The Simplest USB Proxy
----------------------

The simplest use for USB Proxy is to transparently forward USB transactions between the host to the device and log them to the console.

.. literalinclude:: ../../examples/usbproxy.py
   :language: python
   :lines: 7-
   :lineno-start: 7
   :linenos:

Setting up a USB Proxy begins by creating an instance of the :class:`~facedancer.proxy.USBProxyDevice` with the vendor and product id's of the proxied device as arguments.

The actual behaviour of USB Proxy is governed by adding :mod:`~facedancer.filters` to the proxy that can intercept, read, modify and forward USB transactions between the host and device.

The first filter is a :class:`~facedancer.filters.standard.USBProxySetupFilters` which is a simple forwarding filter that ensures all control transfers are forwarded between the target host and the proxied device. Without the presence of this script the target host will detect your proxied device but all attempts at enumeration would fail.

The second filter is a :class:`~facedancer.filters.logging.USBProxyPrettyPrintFilter` which will intercept all transactions and then log them to the console.


Writing USB Proxy Filters
-------------------------

To write your own proxy filter you'd derive a new filter from :class:`~facedancer.filters.base.USBProxyFilter` and override the request handlers for the transactions you want to intercept.

For example, a simple filter to intercept and modify data from a MIDI controller could look like this:

.. code-block:: python

    from facedancer.filters import USBProxyFilter

    class MyFilter(USBProxyFilter):

        # intercept the midi controllers IN endpoint
        def filter_in(self, ep_num, data):

            # check if the data is from the correct endpoint and a midi message
            if ep_num == (0x82 & 0x7f) and len(data) == 4:

                # check if it is a midi note-on/off message
                if data[1] in [0x80, 0x90]:
                    # transpose the note up by an octave - 7f
                    data[2] += 12

            # return the endpoint number and modified data
            return ep_num, data

Which you can then add to the proxy using :class:`~facedancer.proxy.USBProxyDevice`'s :meth:`~facedancer.proxy.USBProxyDevice.add_filter` method:

.. code-block:: python

    # add my filter to the proxy
    proxy.add_filter(MyFilter())

You can find more information about the supported handlers in the :class:`~facedancer.filters.base.USBProxyFilter` documentation.
