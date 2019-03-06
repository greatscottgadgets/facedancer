'''
Clean implementation of audio device

Based on:

  - http://www.usb.org/developers/docs/devclass_docs/audio10.pdf

The specific parameters of this implementation is based on a SilverLine
headset.
However, it does not contain alternate settings for the interfaces
and no HID interface (as we don't really need it here)
'''
import struct
import facedancer
try:
    from six.moves.queue import Queue # Python 3
except ImportError:
    from six.moves.queue import queue as Queue # Python 2

from facedancer.usb.USBClass import *
from facedancer.usb.USBConfiguration import *
from facedancer.usb.USBCSEndpoint import *
from facedancer.usb.USBCSInterface import *
from facedancer.usb.USBDevice import *
from facedancer.usb.USBEndpoint import *
from facedancer.usb.USBInterface import *
from facedancer.fuzz.helpers import mutable


SUBCLASS_UNDEFINED = 0x00
SUBCLASS_AUDIOCONTROL = 0x01
SUBCLASS_AUDIOSTREAMING = 0x02
SUBCLASS_MIDISTREAMING = 0x03


class USBAudioClass(USBClass):
    name = 'AudioClass'

    def setup_local_handlers(self):
        self.local_handlers = {
            0x01: self.handle_audio_set_cur,
            0x04: self.handle_audio_set_res,
            0x0a: self.handle_audio_set_idle,
            0x81: self.handle_audio_get_cur,
            0x82: self.handle_audio_get_min,
            0x83: self.handle_audio_get_max,
            0x84: self.handle_audio_get_res,
        }
        self._settings = {
            # (val, index): [cur, min, max, res, (idle)]
            (0x0100, 0x0001): [b'\x44\xac\x00', b'\x44\xac\x00', b'\x80\xbb\x00', b'\x80\xbb\x00'],
            # (0x0100, 0x0002): ['\x44\xac\x00', '\x44\xac\x00', '\x80\xbb\x00', '\x80\xbb\x00'],
            (0x0100, 0x0082): [b'\x44\xac\x00', b'\x44\xac\x00', b'\x80\xbb\x00', b'\x80\xbb\x00'],
            (0x0100, 0x0900): [b'\x00', b'\x00', b'\xff', b'\x00'],
            (0x0100, 0x0a00): [b'\x01', b'\x00', b'\xff', b'\x00'],
            (0x0100, 0x0d00): [b'\x01', b'\x00', b'\xff', b'\x00'],
            (0x0101, 0x0f00): [b'\x01', b'\x00', b'\xff', b'\x00'],
            (0x0102, 0x0f00): [b'\x01', b'\x00', b'\xff', b'\x00'],
            (0x0200, 0x0a00): [b'\x00\x00', b'\x00\x00', b'\xd0\x17', b'\x30\x00', b'\x00\x00'],
            (0x0200, 0x0d00): [b'\x80\x22', b'\x00\x00', b'\xd0\x2f', b'\x30\x00'],
            (0x0201, 0x0900): [b'\x80\x22', b'\xa0\xe3', b'\xf0\xff', b'\x30\x00'],
            (0x0201, 0x0f00): [b'\x01', b'\x00', b'\xff', b'\x00'],
            (0x0202, 0x0900): [b'\xcf\x00', b'\x00\x00', b'\xcf\x00', b'\x30\x00'],
            (0x0202, 0x0f00): [b'\x01', b'\x00', b'\xff', b'\x00'],
            (0x0301, 0x0f00): [b'\x01', b'\x00', b'\xff', b'\x00'],
            (0x0302, 0x0f00): [b'\x00\x00', b'\x00\x00', b'\x00\x00', b'\x00\x00'],
            (0x0700, 0x0a00): [b'\x01', b'\x00', b'\xff', b'\x00'],
        }

        self._cur = b'\x44\xac\x00'
        self._res = b'\x30\x00'
        self._min = b'\x00\x20'
        self._max = b'\x00\x21'
        self._idle = b''

    def set_param_val(self, req, param):
        try:
            self._settings[(req.value, req.index)][param] = req.data
        except:
            raise Exception('Cannot find tuple (%#x, %#x, %#x) in settings' % (req.value, req.index, param))

    def get_param_val(self, req, param):
        try:
            return self._settings[(req.value, req.index)][param]
        except:
            raise Exception('Cannot find tuple (%#x, %#x, %#x) in settings' % (req.value, req.index, param))

    @mutable('audio_set_cur_response', silent=True)
    def handle_audio_set_cur(self, req):
        self.set_param_val(req, 0)
        return b''

    @mutable('audio_set_res_response', silent=True)
    def handle_audio_set_res(self, req):
        self.set_param_val(req, 3)
        return b''

    @mutable('audio_set_idle_response', silent=True)
    def handle_audio_set_idle(self, req):
        self.set_param_val(req, 4)
        return b''

    @mutable('audio_get_cur_response', silent=True)
    def handle_audio_get_cur(self, req):
        return self.get_param_val(req, 0)

    @mutable('audio_get_min_response', silent=True)
    def handle_audio_get_min(self, req):
        return self.get_param_val(req, 1)

    @mutable('audio_get_max_response', silent=True)
    def handle_audio_get_max(self, req):
        return self.get_param_val(req, 2)

    @mutable('audio_get_res_response', silent=True)
    def handle_audio_get_res(self, req):
        return self.get_param_val(req, 3)


class AudioStreaming(object):
    name = "AudioStreaming"
    def __init__(self, phy, tx_ep, rx_ep):
        self.phy = phy
        self.tx_ep = tx_ep
        self.rx_ep = rx_ep
        self.txq = Queue()

    def buffer_available(self):
        self.phy.usb_function_supported()
        if self.txq.empty():
            self.phy.send_on_endpoint(self.tx_ep, b'\x00\x00\x00\x00\x00\x00\x00\x00')
        else:
            self.phy.send_on_endpoint(self.tx_ep, self.txq.get())

    def data_available(self, data):
        print(self.name,'[AudioStreaming] Got %#x bytes on streaming endpoint' % (len(data)))


class USBAudioStreamingInterface(USBInterface):

    def __init__(self, phy, iface_num, iface_alt, iface_str_idx, cs_ifaces, endpoints, usb_class):
        super(USBAudioStreamingInterface, self).__init__(
            phy=phy,
            interface_number=iface_num,
            interface_alternate=iface_alt,
            interface_class=USBClass.Audio,
            interface_subclass=SUBCLASS_AUDIOSTREAMING,
            interface_protocol=0,
            interface_string_index=iface_str_idx,
            cs_interfaces=cs_ifaces,
            endpoints=endpoints,
            usb_class=usb_class
        )

    @mutable('audio_streaming_interface_descriptor')
    def get_descriptor(self, usb_type='fullspeed', valid=False):
        return super(USBAudioStreamingInterface, self).get_descriptor(usb_type, valid)


class USBAudioControlInterface(USBInterface):

    def __init__(self, phy, iface_num, iface_alt, iface_str_idx, cs_ifaces, usb_class):
        super(USBAudioControlInterface, self).__init__(
            phy=phy,
            interface_number=iface_num,
            interface_alternate=iface_alt,
            interface_class=USBClass.Audio,
            interface_subclass=SUBCLASS_AUDIOCONTROL,
            interface_protocol=0,
            interface_string_index=iface_str_idx,
            cs_interfaces=cs_ifaces,
            usb_class=usb_class
        )

    @mutable('audio_control_interface_descriptor')
    def get_descriptor(self, usb_type='fullspeed', valid=False):
        return super(USBAudioControlInterface, self).get_descriptor(usb_type, valid)


class USBAudioDevice(USBDevice):

    name = 'AudioDevice'

    def __init__(self, phy, vid=0x0d8c, pid=0x000c, rev=0x0001, *args, **kwargs):
        audio_streaming = AudioStreaming(phy, 2, 1)
        usb_class = USBAudioClass(phy)
        super(USBAudioDevice, self).__init__(
            phy=phy,
            device_class=USBClass.Unspecified,
            device_subclass=0,
            protocol_rel_num=0,
            max_packet_size_ep0=0x40,
            vendor_id=vid,
            product_id=pid,
            device_rev=rev,
            manufacturer_string='FD Sound Inc.',
            product_string='FD Audio Adapter',
            serial_number_string='FD2-12345-AUDIO',
            configurations=[
                USBConfiguration(
                    phy=phy,
                    configuration_index=1,
                    configuration_string_or_index='Facedancer Audio Configuration',
                    attributes=USBConfiguration.ATTR_BASE,
                    interfaces=[
                        # standard AC interface (4.3.1)
                        # At this point - with no endpoints
                        USBAudioControlInterface(
                            phy=phy, iface_num=0, iface_alt=0, iface_str_idx=0,
                            cs_ifaces=[
                                # Class specific AC interface: header (4.3.2)
                                USBCSInterface('ACHeader', phy, b'\x01\x00\x01\x64\x00\x02\x01\x02'),
                                # Class specific AC interface: input terminal (Table 4.3.2.1)
                                USBCSInterface('ACInputTerminal0', phy, b'\x02\x01\x01\x01\x00\x02\x03\x00\x00\x00'),
                                USBCSInterface('ACInputTerminal1', phy, b'\x02\x02\x01\x02\x00\x01\x01\x00\x00\x00'),
                                # Class specific AC interface: output terminal (Table 4.3.2.2)
                                USBCSInterface('ACOutputTerminal0', phy, b'\x03\x06\x01\x03\x00\x09\x00'),
                                USBCSInterface('ACOutputTerminal1', phy, b'\x03\x07\x01\x01\x00\x08\x00'),
                                # Class specific AC interface: selector unit (Table 4.3.2.4)
                                USBCSInterface('ACSelectorUnit', phy, b'\x05\x08\x01\x0a\x00'),
                                # Class specific AC interface: feature unit (Table 4.3.2.5)
                                USBCSInterface('ACFeatureUnit0', phy, b'\x06\x09\x0f\x01\x01\x02\x02\x00'),
                                USBCSInterface('ACFeatureUnit1', phy, b'\x06\x0a\x02\x01\x43\x00\x00'),
                                USBCSInterface('ACFeatureUnit2', phy, b'\x06\x0d\x02\x01\x03\x00\x00'),
                                # Class specific AC interface: mixer unit (Table 4.3.2.3)
                                USBCSInterface('ACMixerUnit', phy, b'\x04\x0f\x02\x01\x0d\x02\x03\x00\x00\x00\x00'),
                            ],
                            usb_class=usb_class
                        ),
                        USBAudioStreamingInterface(
                            phy=phy, iface_num=1, iface_alt=0, iface_str_idx=0,
                            cs_ifaces=[
                                USBCSInterface('ASGeneral', phy, b'\x01\x01\x01\x01\x00'),
                                USBCSInterface('ASFormatType', phy, b'\x02\x01\x02\x02\x10\x02\x44\xac\x00\x44\xac\x00'),
                            ],
                            endpoints=[
                                USBEndpoint(
                                    phy=phy, number=1,
                                    direction=USBEndpoint.direction_out,
                                    transfer_type=USBEndpoint.transfer_type_isochronous,
                                    sync_type=USBEndpoint.sync_type_adaptive,
                                    usage_type=USBEndpoint.usage_type_data,
                                    max_packet_size=0x40,
                                    interval=1,
                                    handler=audio_streaming.data_available,
                                    cs_endpoints=[
                                        USBCSEndpoint('ASEndpoint', phy, b'\x01\x01\x01\x01\x00')
                                    ],
                                    usb_class=usb_class,
                                )
                            ],
                            usb_class=usb_class,
                        ),
                        USBAudioStreamingInterface(
                            phy=phy, iface_num=2, iface_alt=0, iface_str_idx=0,
                            cs_ifaces=[
                                USBCSInterface('ASGeneral', phy, b'\x01\x07\x01\x01\x00'),
                                USBCSInterface('ASFormatType', phy, b'\x02\x01\x01\x02\x10\x02\x44\xac\x00\x44\xac\x00'),
                            ],
                            endpoints=[
                                USBEndpoint(
                                    phy=phy, number=2,
                                    direction=USBEndpoint.direction_in,
                                    transfer_type=USBEndpoint.transfer_type_isochronous,
                                    sync_type=USBEndpoint.sync_type_async,
                                    usage_type=USBEndpoint.usage_type_data,
                                    max_packet_size=0x40,
                                    interval=1,
                                    handler=audio_streaming.buffer_available,
                                    cs_endpoints=[
                                        USBCSEndpoint('ASEndpoint', phy, b'\x01\x01\x00\x00\x00')
                                    ],
                                    usb_class=usb_class,
                                )
                            ],
                            usb_class=usb_class,
                        )
                    ]
                ),
            ],
            usb_vendor=None
        )


usb_device = USBAudioDevice
