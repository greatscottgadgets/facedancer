# pylint: disable=unused-wildcard-import, wildcard-import
#
# This file is part of Facedancer.
#
""" Emulation of an FTDI USB-to-serial converter. """

import asyncio

from enum   import IntFlag
from typing import Union

from .         import default_main
from ..        import *
from ..classes import USBDeviceClass

from ..logging import log


OUT_ENDPOINT = 1
IN_ENDPOINT  = 3


class FTDIFlowControl(IntFlag):
    """ Constants describing how FTDI flow control works. """
    NO_FLOW_CONTROL = 0
    RTS_CTS         = 1
    DTR_DSR         = 2
    XON_XOFF        = 4


@use_inner_classes_automatically
class FTDIDevice(USBDevice):
    """ Class implementing an emulated FTDI device. """

    vendor_id           : int = 0x0403
    product_id          : int = 0x6001
    device_revision     : int = 1

    product_string      : str = "FTDI emulation"
    manufacturer_string : str = "not-FTDI"


    class _Configuration(USBConfiguration):
        configuration_string : str = "FTDI config"

        class _Interface(USBInterface):

            # This is a completely vendor-specific device.
            class_number    : int = USBDeviceClass.VENDOR_SPECIFIC
            subclass_number : int = USBDeviceClass.VENDOR_SPECIFIC
            protocol_number : int = USBDeviceClass.VENDOR_SPECIFIC

            class _OutEndpoint(USBEndpoint):
                number        : int          = OUT_ENDPOINT
                direction     : USBDirection = USBDirection.OUT
                transfer_type : USBTransferType = USBTransferType.BULK

            class _InEndpoint(USBEndpoint):
                number        : int          = IN_ENDPOINT
                direction     : USBDirection = USBDirection.IN
                transfer_type : USBTransferType = USBTransferType.BULK


    def __post_init__(self):
        super().__post_init__()
        self.reset_ftdi()


    def reset_ftdi(self):
        """ Resets the FTDI driver back to its original state. """

        # Create a fake baud rate.
        self.baud_rate          = 9600

        # Start off with DTR/RTS disabled.
        self.use_dtr             = False
        self.use_rts             = False

        # Create synthetic values for our control signals.
        self.clear_to_send       = True
        self.data_set_ready      = True
        self.ring_detect         = False
        self.line_status_detect  = True
        self.data_terminal_ready = False
        self.ready_to_send       = False

        # Start off with no flow control.
        self.flow_control        = FTDIFlowControl.NO_FLOW_CONTROL


    #
    # Request handlers.
    #

    @vendor_request_handler(number=0)
    def handle_reset_request(self, request):
        log.debug("Received FTDI reset; assuming initial settings.")

        self.reset_ftdi()
        request.acknowledge()


    @vendor_request_handler(number=1)
    def handle_modem_ctrl_request(self, req):
        log.debug("received modem_ctrl request")

        dtr          = bool(req.value & 0x0001)
        rts          = bool(req.value & 0x0002)
        self.use_dtr = bool(req.value & 0x0100)
        self.use_rts = bool(req.value & 0x0200)

        if dtr:
            log.info("DTR set -- host appears to have connected via virtual serial.")
        else:
            log.info("DTR cleared -- host appears to have disconnected from virtual serial.")

        if self.use_dtr:
            self.data_terminal_ready = dtr
        if self.use_rts:
            self.ready_to_send = rts

        req.acknowledge()



    @vendor_request_handler(number=2)
    def handle_set_flow_ctrl_request(self, request):
        """ Control request to set up flow control. """

        try:
            self.flow_control = FTDIFlowControl(request.value)

            if self.flow_control:
                log.info(f"Host has set up {self.flow_control.name} flow control.")
            else:
                log.info(f"Host has disabled flow control.")

            request.acknowledge()
        except KeyError:
            request.stall()



    @vendor_request_handler(number=3)
    def handle_set_baud_rate_request(self, request):
        """ Control request to set our baud rate. """

        if request.value > 9:
            log.warning("Host specified an unknown baud rate value. Stalling.")
            request.stall()
            return

        # For most values, the FTDI device uses the value to set the baud divisor,
        # such that 0 = 300, 1 = 600, etc.
        if request.value < 8:
            self.baud_rate = 300 * (2 ** request.value)

        # For values of 8/9, it jumps up to hit two more standard bauds.
        elif request.value == 8:
            self.baud_rate = 57600
        elif request.value == 9:
            self.baud_rate = 115200

        log.info(f"Host set baud rate to {self.baud_rate}.")
        request.acknowledge()


    @vendor_request_handler(number=4)
    def handle_set_data_request(self, request):
        log.debug("received set_data request")
        request.acknowledge()


    @vendor_request_handler(number=5)
    def handle_get_modem_status_request(self, request):
        """ Handles requests for the FTDI device's modem status. """

        # Currently, we're emulating the original FTDI SIO, so we only provide
        # a single byte of status. Otherwise, we'd have an second byte with line status.
        response = \
            (1 << 4) if self.clear_to_send      else 0 | \
            (1 << 5) if self.data_set_ready     else 0 | \
            (1 << 6) if self.ring_detect        else 0 | \
            (1 << 7) if self.line_status_detect else 0
        request.reply((response,))


    @vendor_request_handler(number=6)
    def handle_set_event_char_request(self, request):
        log.debug("received set_event_char request")
        request.acknowledge()


    @vendor_request_handler(number=7)
    def handle_set_error_char_request(self, request):
        log.debug("received set_error_char request")
        request.acknowledge()


    @vendor_request_handler(number=9)
    def handle_set_latency_timer_request(self, request):
        log.debug("received set_latency_timer request")
        request.acknowledge()


    @vendor_request_handler(number=10)
    def handle_get_latency_timer_request(self, request):
        log.debug("received get_latency_timer request")

        # Per Travis Goodspeed, this is a "bullshit value".
        request.reply(b'\x01')


    #
    # Internal event handlers.
    #

    def handle_data_received(self, endpoint, data):
        """ Called back whenever data is received. """
        log.debug(f"received {len(data)} bytes on {endpoint}")
        self.handle_serial_data_received(data[1:])


    #
    # User I/O interface.
    #
    async def wait_for_host(self):
        """ Waits until the host connects by waiting for DTR assertion. """

        # Wait for the host to assert DTR.
        while not self.data_terminal_ready:
            await asyncio.sleep(0.1)


    def handle_serial_data_received(self, data):
        """ Callback executed when serial data is received.

        Subclasses should override this to capture data from the host.
        """
        log.debug(f"Received serial data: {data}")


    def transmit(self, data: Union[str, bytes], *, blocking: bool = False, adjust_endings: bool = True):
        """ Transmits a block of data over the provided FTDI link to the host.

        Parameters:
            data           -- The data to be sent.
            blocking       -- If true, this method will wait for completion before returning.
            adjust_endings -- If true, line endings will be adjusted before sending.
        """

        FTDI_PAYLOAD_LENGTH = 62

        # If this isn't a set of raw bytes, encode it into bytes.
        if hasattr(data, 'encode'):
            if adjust_endings:
                data = data.replace("\n", "\r\n")

            data = data.encode('utf-8')

        # Packetize and send the relevant data.
        data = bytearray(data)

        while data:
            packet = data[0:FTDI_PAYLOAD_LENGTH]
            del data[0:FTDI_PAYLOAD_LENGTH]

            self._transmit_packet(packet, blocking=blocking)


    def _transmit_packet(self, data: bytes, *, blocking: bool = False):
        """ Sends a single packet of up to 63 data bytes over our link. """

        # Generate an FTDI packet.
        packet = bytearray()

        # Our first/header byte contains the payload length in bits [7:2], and a packet ID of 01 in [1:0].
        packet.append((len(data) << 2) | 0b01)
        packet.append(0)

        # The remainder of the packet is our payload.
        packet.extend(data)
        self.send(IN_ENDPOINT, packet, blocking=blocking)



if __name__ == "__main__":
    default_main(FTDIDevice)
