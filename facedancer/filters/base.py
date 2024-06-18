#
# This file is part of Facedancer.
#


class USBProxyFilter:
    """
    Base class for filters that modify USB data.
    """

    def filter_control_in_setup(self, request, stalled):
        """
        Filters a SETUP stage for an IN control request. This allows us to modify
        the SETUP stage before it's proxied to the real device.

        Args:
            request : The request to be issued.
            stalled : True iff the packet has been stalled by a previous filter.

        Returns:
            Modified versions of the arguments. If stalled is set to true,
            the packet will be immediately stalled an not proxied. If stalled is
            false, but request is returned as None, the packet will be NAK'd instead
            of proxied.
        """
        return request, stalled


    def filter_control_in(self, request, data, stalled):
        """
        Filters the data response from the proxied device during an IN control
        request. This allows us to modify the data returned from the proxied
        device during a setup stage.

        Args:
            request : The request that was issued to the target host.
            data    : The data being proxied during the data stage.
            stalled : True if the proxied device (or a previous filter) stalled the request.

        Returns:
            Modified versions of the arguments. Note that modifying request
            will _only_ modify the request as seen by future filters, as the
            SETUP stage has already passed and the request has already been
            sent to the device.
        """
        return request, data, stalled


    def filter_control_out(self, request, data):
        """
        Filters handling of an OUT control request, which contains both a
        request and (optional) data stage.

        Args:
            request : The request issued by the target host.
            data :    The data sent by the target host with the request.

        Returns:
            Modified versions of the arguments. Returning a request of
            None will absorb the packet silently and not proxy it to the
            device.
        """
        return request, data


    def handle_out_request_stall(self, request, data, stalled):
        """
        Handles an OUT request that was stalled by the proxied device.

        Args:
            request : The request header for the request that stalled.
            data    : The data stage for the request that stalled, if appropriate.
            stalled : True iff the request is still considered stalled. This can
                      be overridden by previous filters, so it's possible for this to be false.
        """
        return request, data, stalled


    def filter_in_token(self, ep_num):
        """
        Filters an IN token before it's passed to the proxied device.
        This allows modification of e.g. the endpoint or absorption of
        the IN token before it's issued to the real device.

        Args:
            ep_num : The endpoint number on which the IN token is to be proxied.

        Returns:
            A modified version of the arguments. If ep_num is set to None,
            the token will be absorbed and not issued to the target host.
        """
        return ep_num


    def filter_in(self, ep_num, data):
        """
        Filters the response to an IN token (the data packet received in response
        to the host issuing an IN token).

        Args:
            ep_num : The endpoint number associated with the data packet.
            data   : The data packet received from the proxied device.

        Returns:
            A modified version of the arguments. If data is set to none,
            the packet will be absorbed, and a NAK will be issued instead of
            responding to the IN request with data.
        """
        return ep_num, data


    def filter_out(self, ep_num, data):
        """
        Filters a packet sent from the host via an OUT token.

        Args:
            ep_num: The endpoint number associated with the data packet.
            data: The data packet received from host.

        Returns:
            A modified version of the arguments. If data is set to none,
            the packet will be absorbed,
        """
        return ep_num, data


    def handle_out_stall(self, ep_num, data, stalled):
        """
        Handles an OUT transfer that was stalled by the victim.

        Args:
            ep_num  : The endpoint number for the data that stalled.
            data    : The data for the transfer that stalled, if appropriate.
            stalled : True iff the transfer is still considered stalled. This can
                      be overridden by previous filters, so it's possible for this to
                      be false.
        """
        return ep_num, data, stalled
