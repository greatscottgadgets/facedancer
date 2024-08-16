================================================
Getting started with Facedancer
================================================

.. warning::

   Facedancer and USBProxy are not currently supported in a Control Host role on Windows with Cynthion. Attempting to use Facedancer or USBProxy with Cynthion on Windows may cause Cynthion USB analysis to stop working.

   For more information please see the tracking issue: `#170 <https://github.com/greatscottgadgets/cynthion/issues/170>`__

Install the Facedancer library
------------------------------

You can install the Facedancer library from the `Python Package Index (PyPI) <https://pypi.org/project/facedancer/>`__, a `release archive <https://github.com/greatscottgadgets/Facedancer/releases>`__ or directly from `source <https://github.com/greatscottgadgets/Facedancer/>`__.


Install From PyPI
^^^^^^^^^^^^^^^^^

You can use the `pip <https://pypi.org/project/pip/>`__ tool to install the Facedancer library from PyPI using the following command:

.. code-block :: sh

    pip install facedancer

For more information on installing Python packages from PyPI please refer to the `"Installing Packages" <https://packaging.python.org/en/latest/tutorials/installing-packages/>`__ section of the Python Packaging User Guide.


Install From Source
^^^^^^^^^^^^^^^^^^^

.. code-block :: sh

    git clone https://github.com/greatscottgadgets/facedancer.git
    cd facedancer/

Once you have the source code downloaded you can install the Facedancer library with:

.. code-block :: sh

    pip install .



Run a Facedancer example
------------------------

Create a new Python file called `rubber-ducky.py` with the following content:

.. code-block :: python

    import asyncio
    import logging

    from facedancer import main
    from facedancer.devices.keyboard     import USBKeyboardDevice
    from facedancer.classes.hid.keyboard import KeyboardModifiers

    device = USBKeyboardDevice()

    async def type_letters():
        # Wait for device to connect
        await asyncio.sleep(2)

        # Type a string with the device
        await device.type_string("echo hello, facedancer\n")

    main(device, type_letters())



Open a terminal and run:

.. code-block :: sh

    python ./rubber-ducky.py
