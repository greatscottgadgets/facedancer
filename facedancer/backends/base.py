from typing    import List
from ..        import *


class FacedancerBackend:
    def __init__(self, device: USBDevice=None, verbose: int=0, quirks: List[str]=[]):
        """
        Initializes the backend.

        Args:
            device  :  The device that will act as our Facedancer.   (Optional)
            verbose : The verbosity level of the given application. (Optional)
            quirks  :  List of USB platform quirks.                  (Optional)
        """
        raise NotImplementedError


    @classmethod
    def appropriate_for_environment(cls, backend_name: str) -> bool:
        """
        Determines if the current environment seems appropriate
        for using this backend.

        Args:
            backend_name : Backend name being requested. (Optional)
        """
        raise NotImplementedError


    def get_version(self):
        """
        Returns information about the active Facedancer version.
        """
        raise NotImplementedError


    def connect(self, usb_device: USBDevice, max_packet_size_ep0: int=64, device_speed: DeviceSpeed=DeviceSpeed.FULL):
        """
        Prepares backend to connect to the target host and emulate
        a given device.

        Args:
            usb_device : The USBDevice object that represents the emulated device.
            max_packet_size_ep0 : Max packet size for control endpoint.
            device_speed : Requested usb speed for the Facedancer board.
        """
        raise NotImplementedError


    def disconnect(self):
        """ Disconnects Facedancer from the target host. """
        raise NotImplementedError


    def reset(self):
        """
        Triggers the Facedancer to handle its side of a bus reset.
        """
        raise NotImplementedError


    def set_address(self, address: int, defer: bool=False):
        """
        Sets the device address of the Facedancer. Usually only used during
        initial configuration.

        Args:
            address : The address the Facedancer should assume.
            defer   : True iff the set_address request should wait for an active transaction to
                      finish.
        """
        raise NotImplementedError


    def configured(self, configuration: USBConfiguration):
        """
        Callback that's issued when a USBDevice is configured, e.g. by the
        SET_CONFIGURATION request. Allows us to apply the new configuration.

        Args:
            configuration : The USBConfiguration object applied by the SET_CONFIG request.
        """
        raise NotImplementedError


    def read_from_endpoint(self, endpoint_number: int) -> bytes:
        """
        Reads a block of data from the given endpoint.

        Args:
            endpoint_number : The number of the OUT endpoint on which data is to be rx'd.
        """
        raise NotImplementedError


    def send_on_control_endpoint(self, endpoint_number: int, in_request: USBControlRequest, data: bytes, blocking: bool=True):
        """
        Sends a collection of USB data in response to a IN control request by the host.

        Args:
            endpoint_number  : The number of the IN endpoint on which data should be sent.
            in_request       : The control request being responded to.
            data             : The data to be sent.
            blocking         : If true, this function should wait for the transfer to complete.
        """
        # Truncate data to requested length and forward to `send_on_endpoint()` for backends
        # that do not need to support this method.
        return self.send_on_endpoint(endpoint_number, data[:in_request.length], blocking)


    def send_on_endpoint(self, endpoint_number: int, data: bytes, blocking: bool=True):
        """
        Sends a collection of USB data on a given endpoint.

        Args:
            endpoint_number : The number of the IN endpoint on which data should be sent.
            data : The data to be sent.
            blocking : If true, this function should wait for the transfer to complete.
        """
        raise NotImplementedError


    def ack_status_stage(self, direction: USBDirection=USBDirection.OUT, endpoint_number:int =0, blocking: bool=False):
        """
        Handles the status stage of a correctly completed control request,
        by priming the appropriate endpoint to handle the status phase.

        Args:
            direction : Determines if we're ACK'ing an IN or OUT vendor request.
                       (This should match the direction of the DATA stage.)
            endpoint_number : The endpoint number on which the control request
                              occurred.
            blocking : True if we should wait for the ACK to be fully issued
                       before returning.
        """


    def stall_endpoint(self, endpoint_number:int, direction: USBDirection=USBDirection.OUT):
        """
        Stalls the provided endpoint, as defined in the USB spec.

        Args:
            endpoint_number : The number of the endpoint to be stalled.
        """
        raise NotImplementedError


    def clear_halt(self, endpoint_number:int, direction: USBDirection):
        """ Clears a halt condition on the provided non-control endpoint.

        Args:
            endpoint_number : The endpoint number
            direction       : The endpoint direction; or OUT if not provided.
        """
        # FIXME do nothing as only the moondancer backend supports this for now
        # raise NotImplementedError
        pass


    def service_irqs(self):
        """
        Core routine of the Facedancer execution/event loop. Continuously monitors the
        Facedancer's execution status, and reacts as events occur.
        """
        raise NotImplementedError
