# USBMtp.py
#
# Contains class definitions to implement a USB keyboard.
import struct
from facedancer.usb.USBDevice import USBDevice
from facedancer.usb.USBConfiguration import USBConfiguration
from facedancer.usb.USBInterface import USBInterface
from facedancer.usb.USBEndpoint import USBEndpoint
from facedancer.usb.USBVendor import USBVendor
from facedancer.usb.USBClass import USBClass
from facedancer.fuzz.helpers import mutable

try:
    from mtpdevice.mtp_device import MtpDevice, MtpDeviceInfo
    from mtpdevice.mtp_object import MtpObject
    from mtpdevice.mtp_storage import MtpStorage, MtpStorageInfo
    from mtpdevice.mtp_api import MtpApi
    from mtpdevice.mtp_property import MtpDeviceProperty, MtpDevicePropertyCode
    from mtpdevice.mtp_data_types import MStr, UInt8
    mtpdeviceloaded = True
except:
    print('Failed to load mtpdevice. please install pymtpdevice (https://github.com/BinyaminSharet/Mtp)')
    mtpdeviceloaded = False


class USBMtpInterface(USBInterface):
    name = 'MtpInterface'

    def __init__(self, phy):
        if not mtpdeviceloaded:
            raise Exception('You cannot use USBMtp until you install pymtpdevice')
        # TODO: un-hardcode string index
        super(USBMtpInterface, self).__init__(
            phy=phy,
            interface_number=0,
            interface_alternate=0,
            interface_class=USBClass.VendorSpecific,
            interface_subclass=0xff,
            interface_protocol=0,
            interface_string_index=0,
            endpoints=[
                USBEndpoint(
                    phy=phy,
                    number=1,
                    direction=USBEndpoint.direction_out,
                    transfer_type=USBEndpoint.transfer_type_bulk,
                    sync_type=USBEndpoint.sync_type_none,
                    usage_type=USBEndpoint.usage_type_data,
                    max_packet_size=64,
                    interval=0,
                    handler=self.handle_ep1_data_available
                ),
                USBEndpoint(
                    phy=phy,
                    number=2,
                    direction=USBEndpoint.direction_in,
                    transfer_type=USBEndpoint.transfer_type_bulk,
                    sync_type=USBEndpoint.sync_type_none,
                    usage_type=USBEndpoint.usage_type_data,
                    max_packet_size=64,
                    interval=0,
                    handler=None
                ),
                USBEndpoint(
                    phy=phy,
                    number=3,
                    direction=USBEndpoint.direction_in,
                    transfer_type=USBEndpoint.transfer_type_interrupt,
                    sync_type=USBEndpoint.sync_type_none,
                    usage_type=USBEndpoint.usage_type_data,
                    max_packet_size=64,
                    interval=32,
                    handler=None
                ),
            ],
        )
        self.object = MtpObject.from_fs_recursive('mtp_fs')
        # self.object = MtpObject.from_fs_recursive('mtp_fs/eits.mp3')
        self.storage_info = MtpStorageInfo(
            st_type=1,
            fs_type=2,
            access=0,
            max_cap=150000,
            free_bytes=0,
            free_objs=0,
            desc='MyStorage',
            vol_id='Python MTP Device Stack',
        )
        self.storage = MtpStorage(self.storage_info)
        self.storage.add_object(self.object)
        self.dev_info = MtpDeviceInfo(
            std_version=0x0064,
            mtp_vendor_ext_id=0x00000006,
            mtp_version=0x0064,
            mtp_extensions='microsoft.com: 1.0;',
            functional_mode=0x0000,
            capture_formats=[],
            playback_formats=[],
            manufacturer='Facedancer',
            model='Role',
            device_version='1.2',
            serial_number='3031323334353637',
        )
        properties = [
            MtpDeviceProperty(MtpDevicePropertyCode.MTP_DeviceFriendlyName, 0, MStr('FDMtpDevice'), MStr('')),
            MtpDeviceProperty(MtpDevicePropertyCode.BatteryLevel, 0, UInt8(100), UInt8(0))
        ]
        self.dev = MtpDevice(self.dev_info, properties, self.logger)
        self.dev.add_storage(self.storage)
        #self.dev.set_fuzzer(fuzzer)
        self.api = MtpApi(self.dev)

        # OS String descriptor
        # self.add_string_with_id(50, 'MTP'.encode('utf-16') + b'\x00\x00')
        self.add_string_with_id(0xee, 'MSFT100'.encode('utf-16') + b'\x00\x00')

    def handle_ep1_data_available(self, data):
        resps = self.api.handle_payload(data)
        if resps:
            for resp in resps:
                self.send_on_endpoint(2, resp)


class USBMsosVendor(USBVendor):

    def setup_local_handlers(self):
        self.local_handlers = {
            0x00: self.handle_msos_vendor_extended_config_descriptor,
        }

    @mutable('msos_vendor_extended_config_descriptor')
    def handle_msos_vendor_extended_config_descriptor(self, req):
        '''
        Taken from OS_Desc_CompatID
        https://msdn.microsoft.com/en-us/windows/hardware/gg463179
        '''
        def pad(data, pad_len=8):
            to_pad = pad_len - len(data)
            return data + (b'\x00' * to_pad)

        self.property_sections = [
            [0x00, 0x01, pad(b'MTP'), pad(b''), pad(b'', 6)]
        ]
        bcdVersion = 0x0100
        wIndex = 0x00
        bCount = len(self.property_sections)
        reserved = pad(b'\x00', 7)
        properties = b''
        for prop in self.property_sections:
            properties += struct.pack('BB', prop[0], prop[1]) + prop[2] + prop[3] + prop[4]
        payload = struct.pack('<HHB', bcdVersion, wIndex, bCount) + reserved + properties
        dwLength = len(payload) + 4
        payload = struct.pack('<I', dwLength) + payload
        return payload


class USBMtpDevice(USBDevice):
    name = 'MtpDevice'

    def __init__(self, phy, vid=0x4e8, pid=0x685c, rev=0x0002, **kwargs):
        super(USBMtpDevice, self).__init__(
            phy=phy,
            device_class=USBClass.Unspecified,
            device_subclass=0,
            protocol_rel_num=0,
            max_packet_size_ep0=64,
            vendor_id=vid,
            product_id=pid,
            device_rev=rev,
            manufacturer_string='Samsung Electronics Co., Ltd',
            product_string='GT-I9250 Phone [Galaxy Nexus]',
            serial_number_string='00001',
            configurations=[
                USBConfiguration(
                    phy=phy,
                    index=1,
                    string='Android MTP Device',
                    interfaces=[
                        USBMtpInterface(phy)
                    ]
                )
            ],
            usb_vendor=USBMsosVendor(phy=phy),
        )


usb_device = USBMtpDevice
