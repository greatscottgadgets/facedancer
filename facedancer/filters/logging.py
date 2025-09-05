#
# USBProxy logging filters
#

import datetime

from facedancer.request import USBControlRequest

from ..logging import log

from .         import USBProxyFilter


class USBProxyPrettyPrintFilter(USBProxyFilter):
    """
    Filter that pretty prints USB transactions according to log levels.
    """

    def __init__(self, verbose=4, decoration=''):
        """
        Sets up a new USBProxy pretty printing filter.
        """
        self.verbose = verbose
        self.decoration = decoration



    def filter_control_in(self, req: USBControlRequest | None, data, stalled):
        """
        Log IN control requests without modification.
        """

        if self.verbose > 3 and req is None:
            log.info("{} {}< --filtered out-- ".format(self.timestamp(), self.decoration))
            return req, data, stalled

        if self.verbose > 3:
            log.info("{} {}< control {}".format(self.timestamp(), self.decoration, req))

        if self.verbose > 3 and stalled:
            log.info("{} {}< --STALLED-- ".format(self.timestamp(), self.decoration))

        if self.verbose > 4 and data:
            is_string = (req.request == 6) and (req.value >> 8 == 3)
            self._pretty_print_data(data, '<', self.decoration, is_string)

        return req, data, stalled


    def filter_control_out(self, req, data):
        """
        Log OUT control requests without modification.
        """

        # TODO: just call control_in, it's the same:

        if self.verbose > 3 and req is None:
            log.info("{} {}> --filtered out-- ".format(self.timestamp(), self.decoration))
            return req, data

        if self.verbose > 3:
            log.info("{} {}> control {}".format(self.timestamp(), self.decoration, req))

        if self.verbose > 4 and data:
            self._pretty_print_data(data, '>', self.decoration)

        return req, data


    def handle_out_request_stall(self, req, data, stalled):
        """
        Handles cases where OUT requests are stalled (and thus we don't get data).
        """
        if self.verbose > 3 and req is None:
            if stalled:
                log.info("{} {}> --STALLED-- ".format(self.timestamp(), self.decoration))
            else:
                log.info("{} {}> --STALLED, but unstalled by filter-- ".format(self.timestamp(), self.decoration))

        return req, data, stalled


    def filter_in(self, ep_num, data):
        """
        Log IN transfers without modification.
        """

        if self.verbose > 4 and data:
            self._pretty_print_data(data, '<', self.decoration, ep_marker=ep_num)

        return ep_num, data

    def filter_out(self, ep_num, data):
        """
        Log OUT transfers without modification.
        """

        if self.verbose > 4 and data:
            self._pretty_print_data(data, '>', self.decoration, ep_marker=ep_num)

        return ep_num, data


    def timestamp(self):
        """ Generate a quick timestamp for printing. """
        return datetime.datetime.now().strftime("[%H:%M:%S.%f]")

    def _magic_decode(self, data):
        """ Simple decode function that attempts to find a nice string representation for the console."""
        try:
            return bytes(data).decode('utf-16le')
        except:
            return bytes(data).hex(' ', 2)


    def _pretty_print_data(self, data, direction_marker, decoration='', is_string=False, ep_marker=''):
        decoded = self._magic_decode(data) if is_string else bytes(data).hex(' ', 2)
        if self.verbose < 6 and len(data) >= 30:
            decoded = decoded[:30] + '…'
        log.info("{} {}{}{}: {} ({})".format(self.timestamp(), ep_marker, decoration, direction_marker, decoded, len(data)))
