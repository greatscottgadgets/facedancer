#!/usr/bin/env python3
#
# Simplest possible example of using the FaceDancer host API.

from facedancer import FacedancerUSBHostApp
import sys

class USBMassStorageHost:
    """
    Class that allows us to communicate with USB Mass Storage devices over USB.
    """

    USB_CLASS_UMS = 8
    USB_SUBCLASS_SCSI = 6
    USB_PROTOCOL_BULK_ONLY = 80

    def __init__(self, device_connection=None, verbose=0):
        """
        Sets the class up to work with the relevant UMS device.

        device_connection -- The USBHost connection to the UMS device, or None to
            try and automatically find one.
        """

        # If we haven't been provided a device connection, try to connect to it.
        if device_connection is None:
            device_connection = FacedancerUSBHostApp(verbose=verbose)

            # FIXME: support more than one configuration
            device_connection.initialize_device(assign_address=1, apply_configuration=1)

        # Store the device connection.
        self.host = device_connection

        # Find the USB mass storage interface used for this device.
        self._find_ums_interface()
        self._find_ums_endpoints()



    def _find_ums_interface(self):
        """ Locates the USB Mass Storage interface on the active device. """

        # Read information about the device's configurations.
        configuration = self.host.get_configuration_descriptor()

        # Look for the UMS interface.
        # TODO: use USBMassStorageClass?
        for interface in configuration.interfaces:

            # Skip any interfaces that aren't UMS.
            is_ums  = (interface.iclass.class_number == self.USB_CLASS_UMS)
            if not is_ums:
                continue

            # TODO: support devices that are UMS modes other than SCSI
            is_scsi = (interface.subclass == self.USB_SUBCLASS_SCSI)
            is_bulk_only = (interface.protocol == self.USB_PROTOCOL_BULK_ONLY)
            if not is_scsi or not is_bulk_only:
                continue

            # If we met all the conditions, this is our interface.
            self.interface = interface
            return

        # If we couldn't find an interface, return.
        raise DeviceNotFoundException("Connected device does not support UMS!")


    def _find_ums_endpoints(self):
        """ Locates the UMS endpoints used for the device. """

        # Find the in and out endpoints used to talk UMS.
        for endpoint in self.interface.endpoints:
            if endpoint.direction == endpoint.DIRECTION_IN:
                self.in_endpoint = endpoint
            if endpoint.direction == endpoint.DIRECTION_OUT:
                self.out_endpoint = endpoint


# Use our class to talk to the UMS device.
ums = USBMassStorageHost()
print(ums.in_endpoint)
print(ums.out_endpoint)
