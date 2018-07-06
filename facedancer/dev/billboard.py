'''
USB Billboard implementation

Based on USB_Billboard_Revision_1_0_20140801.pdf
All references in this script ar to this pdf.
'''
import struct
from facedancer.usb.USBDevice import *
from facedancer.usb.USBClass import *
from facedancer.usb.USBConfiguration import *
from facedancer.usb.USBBos import USBBinaryObjectStore
from facedancer.usb.USBDeviceCapability import USBDeviceCapability,DCContainerId


class DCBillboard(USBDeviceCapability):
    '''Section 3.1.5.2'''

    BILLBOARD_CAPABILITY_TYPE = 0x0d

    def __init__(
        self, phy,
        additional_info_idx,
        preferred_alternate_mode,
        vconn_power,
        bm_configured,
        alternate_modes,
    ):
        data = struct.pack('<BBBH', additional_info_idx, len(alternate_modes), preferred_alternate_mode, vconn_power)
        data += bm_configured
        data += struct.pack('<I', 0)
        for mode in alternate_modes:
            data += struct.pack('<HBB', *mode)
        super(DCBillboard, self).__init__(phy, self.BILLBOARD_CAPABILITY_TYPE, data)
        self.additional_info_idx = additional_info_idx
        self.preferred_alternate_mode = preferred_alternate_mode
        self.vconn_power = vconn_power
        self.bm_configured = bm_configured
        self.alternate_modes = alternate_modes


class USBBillboardDevice(USBDevice):

    def __init__(self, phy, vid=0x8312, pid=0x8312, **kwargs):
        usb_class = None
        usb_vendor = None
        configurations = [
            USBConfiguration(
                phy=phy,
                index=0x1,
                string='Billboard configuration',
                interfaces=[],
                attributes=0xc0,
                max_power=0xfa
            )
        ]
        super(USBBillboardDevice, self).__init__(
            phy=phy,
            device_class=USBClass.Billboard,
            device_subclass=0x0,
            protocol_rel_num=0x0,
            max_packet_size_ep0=0x40,
            vendor_id=vid,
            product_id=pid,
            device_rev=0x0,
            manufacturer_string='Umap2 Inc.',
            product_string='Umap2 Billboard',
            serial_number_string='UMAP2-BILL-0123',
            configurations=configurations,
            descriptors=None,
            usb_class=usb_class,
            usb_vendor=usb_vendor,
        )
        self.usb_spec_version = 0x0210
        self.bos = USBBinaryObjectStore(phy, capabilities=[
            DCContainerId(phy, container_id=b'UMAP2-BILL-12345'),
            DCBillboard(
                phy,
                additional_info_idx=self.get_string_id('https://additional.info/umap2'),
                preferred_alternate_mode=0,
                vconn_power=0x8000,
                bm_configured=b'\xff' * 16,
                alternate_modes=[
                    (vid, 0, self.get_string_id('alternate_mode_0'))
                ],
            )
        ])


usb_device = USBBillboardDevice
