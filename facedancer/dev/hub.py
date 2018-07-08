'''
Contains class definitions to implement a USB hub.
'''
import struct
from umap2.core.usb import DescriptorType
from facedancer.usb.USBClass import USBClass
from facedancer.usb.USBDevice import USBDevice
from facedancer.usb.USBConfiguration import USBConfiguration
from facedancer.usb.USBInterface import USBInterface
from facedancer.usb.USBEndpoint import USBEndpoint
from facedancer.fuzz.helpers import mutable

class USBHubClass(USBClass):
    name = 'HubClass'

    def __init__(self, phy):
        super(USBHubClass, self).__init__(phy)
        self.num_ports = 7
        self.hub_chars = 0x0000
        self.pwr_on_2_pwr_good = 2
        self.hub_contr_current = 50

    def setup_local_handlers(self):
        self.local_handlers = {
            0x00: self.handle_get_hub_status,
            0x03: self.handle_set_port_feature,
            0x06: self.handle_get_descriptor
        }

    @mutable('hub_get_hub_status_response')
    def handle_get_hub_status(self, req):
        i = req.index
        if i:
            self.info('GetPortStatus (%d)' % i)
        else:
            self.info('GetHubStatus')
        return b'\x00\x00\x00\x00'

    @mutable('hub_set_port_feature_response')
    def handle_set_port_feature(self, req):
        return b'\x01'

    @mutable('hub_descriptor')
    def handle_get_descriptor(self, req):
        d = struct.pack(
            '<BBHBB',
            DescriptorType.hub,
            self.num_ports,
            self.hub_chars,
            self.pwr_on_2_pwr_good,
            self.hub_contr_current,
        )
        num_bytes = self.num_ports // 7
        if self.num_ports % 7 != 0:
            num_bytes += 1
        d += b'\x00' * num_bytes
        d += b'\xff' * num_bytes
        d = struct.pack('B', len(d) + 1) + d
        return d


class USBHubInterface(USBInterface):
    name = 'HubInterface'

    def __init__(self, phy, num=0):
        # TODO: un-hardcode string index
        super(USBHubInterface, self).__init__(
            phy=phy,
            interface_number=num,
            interface_alternate=0,
            interface_class=USBClass.Hub,
            interface_subclass=0,
            interface_protocol=0,
            interface_string_index=0,
            endpoints=[
                USBEndpoint(
                    phy=phy,
                    number=0x2,
                    direction=USBEndpoint.direction_in,
                    transfer_type=USBEndpoint.transfer_type_interrupt,
                    sync_type=USBEndpoint.sync_type_none,
                    usage_type=USBEndpoint.usage_type_data,
                    max_packet_size=0x40,
                    interval=0x40,
                    handler=self.handle_buffer_available
                )
            ],
            descriptors={
                DescriptorType.hub: self.get_hub_descriptor
            },
            usb_class=USBHubClass(phy)
        )

    @mutable('hub_descriptor')
    def get_hub_descriptor(self, **kwargs):
        bLength = 9
        bDescriptorType = 0x29
        bNbrPorts = 4
        wHubCharacteristics = 0xe000
        bPwrOn2PwrGood = 0x32
        bHubContrCurrent = 0x64
        DeviceRemovable = 0
        PortPwrCtrlMask = 0xff

        return struct.pack(
            '<BBBHBBBB',
            bLength,
            bDescriptorType,
            bNbrPorts,
            wHubCharacteristics,
            bPwrOn2PwrGood,
            bHubContrCurrent,
            DeviceRemovable,
            PortPwrCtrlMask
        )

    def handle_buffer_available(self):
        return


class USBHubDevice(USBDevice):
    name = 'HubDevice'

    def __init__(self, phy, vid=0x05e3, pid=0x0610, rev=0x7732, **kwargs):
        super(USBHubDevice, self).__init__(
            phy=phy,
            device_class=USBClass.Hub,
            device_subclass=0,
            protocol_rel_num=1,
            max_packet_size_ep0=64,
            vendor_id=vid,
            product_id=pid,
            device_rev=rev,
            manufacturer_string='Genesys Logic, Inc',
            product_string='USB2.0 Hub',
            serial_number_string='1234',
            configurations=[
                USBConfiguration(
                    phy=phy,
                    configuration_index=1,
                    configuration_string_or_index='Emulated Hub',
                    interfaces=[
                        USBHubInterface(phy)
                    ],
                    attributes=USBConfiguration.ATTR_SELF_POWERED,
                )
            ],
        )


usb_device = USBHubDevice
