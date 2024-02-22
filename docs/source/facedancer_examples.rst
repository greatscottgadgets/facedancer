================================================
Facedancer Examples
================================================

There are a number of `Facedancer examples <https://github.com/greatscottgadgets/Facedancer/blob/master/examples/>`__ available that demonstrate emulation of various USB device functions.


`rubber-ducky <https://github.com/greatscottgadgets/Facedancer/blob/master/examples/rubber-ducky.py>`__
-------------------------------------------------------------------------------------------------------

The canonical "Hello World" of USB emulation, the rubber ducky implements a minimal subset of the USB HID class specification in order to emulate a USB keyboard.

.. list-table:: Compatibility
   :widths: 30 30 30
   :header-rows: 1

   * - Linux
     - macOS
     - Windows
   * - ✅
     - ✅
     - ✅



`ftdi-echo <https://github.com/greatscottgadgets/Facedancer/blob/master/examples/ftdi-echo.py>`__
-------------------------------------------------------------------------------------------------

An emulation of an FTDI USB-to-serial converter, ``ftdi-echo`` converts input received from a connected terminal to uppercase and echoes the result back to the sender.

.. list-table:: Compatibility
   :widths: 30 30 30
   :header-rows: 1

   * - Linux
     - macOS
     - Windows
   * - ✅
     - ❌
     - ✅



`mass-storage <https://github.com/greatscottgadgets/Facedancer/blob/master/examples/mass-storage.py>`__
-------------------------------------------------------------------------------------------------------

An emulation of a USB Mass Storage device, ``mass-storage`` can take a raw disk image file as input and present it to a target host as drive that can be mounted, read and written to.

You can create an empty disk image for use with the emulation using:

.. code-block :: sh

    dd if=/dev/zero of=disk.img bs=1M count=100
    mkfs -t ext4 disk.img

You can also test or modify the disk image locally by mounting it with:

.. code-block :: sh

    mount -t auto -o loop disk.img /mnt

Remember to unmount it before using it with the device emulation!


.. list-table:: Compatibility
   :widths: 30 30 30
   :header-rows: 1

   * - Linux
     - macOS
     - Windows
   * - ✅
     - ✅
     - ❌
