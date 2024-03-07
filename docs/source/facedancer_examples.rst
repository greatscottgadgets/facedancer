===================
Facedancer Examples
===================

There are a number of :repo:`Facedancer examples<examples/>` available that demonstrate emulation of various USB device functions.


:example:`rubber-ducky.py`
--------------------------

The canonical "Hello World" of USB emulation, the rubber-ducky example implements a minimal subset of the USB HID class specification in order to emulate a USB keyboard.

.. list-table:: Host Compatibility
   :widths: 30 30 30
   :header-rows: 1

   * - Linux
     - macOS
     - Windows
   * - ✅
     - ✅
     - ✅



:example:`ftdi-echo.py`
-----------------------

An emulation of an FTDI USB-to-serial converter, the ftdi-echo example converts input received from a connected terminal to uppercase and echoes the result back to the sender.

.. list-table:: Host Compatibility
   :widths: 30 30 30
   :header-rows: 1

   * - Linux
     - macOS
     - Windows
   * - ✅
     - ❌
     - ✅



:example:`mass-storage.py`
--------------------------

An emulation of a USB Mass Storage device, the mass-storage example can take a raw disk image file as input and present it to a target host as drive that can be mounted, read and written to.

You can create an empty disk image for use with the emulation using:

.. code-block :: sh

    dd if=/dev/zero of=disk.img bs=1M count=100
    mkfs -t ext4 disk.img

You can also test or modify the disk image locally by mounting it with:

.. code-block :: sh

    mount -t auto -o loop disk.img /mnt

Remember to unmount it before using it with the device emulation!


.. list-table:: Host Compatibility
   :widths: 30 30 30
   :header-rows: 1

   * - Linux
     - macOS
     - Windows
   * - ✅
     - ✅
     - ❌
