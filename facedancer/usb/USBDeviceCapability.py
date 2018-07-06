'''
Device capabilities

As defined in USB 3.1 spec, section 9.6.2
'''
import struct
from .USB import *


class USBDeviceCapability(USBDescribable):

    WIRELESS_USB = 0x01
    USB_20_EXTENSION = 0x02
    SUPERSPEED_USB = 0x03
    CONTAINER_ID = 0x04
    PLATFORM = 0x05
    POWER_DELIVERY_CAPABILITY = 0x06
    BATTERY_INFO_CAPABILITY = 0x07
    PD_CONSUMER_PORT_CAPABILITY = 0x08
    PD_PROVIDER_PORT_CAPABILITY = 0x09
    SUPERSPEED_PLUS = 0x0A
    PRECISION_TIME_MEASUREMENT = 0x0B
    WIRELESS_USB_EXT = 0x0C

    def __init__(self, phy, cap_type, data):
        '''
        :param app: Umap2 application
        :param phy: Physical connection
        :param cap_type: Capability type
        :param data: the capability data (string)
        '''
        super(USBDeviceCapability, self).__init__(phy)
        self.cap_type = cap_type
        self.cap_data = data

    #@mutable('device_capability_descriptor')
    def get_descriptor(self, usb_type='fullspeed', valid=False):
        bDescriptorType = DescriptorType.device_capability
        bLength = 3 + len(self.cap_data)
        d = struct.pack(
            '<BBB',
            bLength,
            bDescriptorType,
            self.cap_type
        )
        return d + self.cap_data


#
# Specific device capability classes
#

class DCUsb20Extension(USBDeviceCapability):
    '''
    USB 2.0 Extension capability is defined in USB 3.1 spec, section 9.6.2.1
    '''

    ATTR_LPM = 0x00000002
    ATTR_NONE = 0x00000000

    def __init__(self, phy, attributes=ATTR_NONE):
        data = struct.pack('<I', attributes)
        super(DCUsb20Extension, self).__init__(phy, self.USB_20_EXTENSION, data)
        self.attributes = attributes


class DCSuperspeedUsb(USBDeviceCapability):
    '''
    Superspeed USB capability is defined in USB 3.1 spec, section 9.6.2.2
    '''

    def __init__(self, phy, attributes, speeds_supported, functionality_support, u1dev_exit_lat, u2dev_exit_lat):
        data = struct.pack('<BHBBH', attributes, speeds_supported, functionality_support, u1dev_exit_lat, u2dev_exit_lat)
        super(DCSuperspeedUsb, self).__init__(phy, self.SUPERSPEED_USB, data)
        self.attributes = attributes
        self.speeds_supported = speeds_supported
        self.functionality_support = functionality_support
        self.u1dev_exit_lat = u1dev_exit_lat
        self.u2dev_exit_lat = u2dev_exit_lat


class DCContainerId(USBDeviceCapability):
    '''
    Container ID capability is defined in USB 3.1 spec, section 9.6.2.3
    '''

    def __init__(self, phy, container_id):
        data = b'\x00' + container_id
        super(DCContainerId, self).__init__(phy, self.CONTAINER_ID, data)
        self.container_id = container_id


class DCPlatform(USBDeviceCapability):
    '''
    Platform capability is defined in USB 3.1 spec, section 9.6.2.4
    '''

    def __init__(self, phy, platform_capability_uuid, capability_data=b''):
        data = b'\x00' + platform_capability_uuid + capability_data
        super(DCPlatform, self).__init__(phy, self.PLATFORM, data)
        self.platform_capability_uuid = platform_capability_uuid
        self.capability_data = capability_data


class DCSuperspeedPlusUsb(USBDeviceCapability):
    '''
    Superspeed Plus USB capability is defined in USB 3.1 spec, section 9.6.2.5
    '''

    def __init__(self, phy, attributes, functionality_support, sublink_speed_attributes):
        data = struct.pack('<BIHH', 0, attributes, 0, functionality_support)
        for sls_attr in sublink_speed_attributes:
            data += struct.pack('<I', sls_attr)
        super(DCSuperspeedPlusUsb, self).__init__(phy, self.SUPERSPEED_PLUS, data)
        self.attributes = attributes
        self.functionality_support = functionality_support
        self.sublink_speed_attributes = sublink_speed_attributes


class DCPrecisionTimeMeasurement(USBDeviceCapability):
    '''
    Precision Time Measurement capability is defined in USB 3.1 spec, section 9.6.2.6
    '''
    def __init__(self, phy):
        super(DCPrecisionTimeMeasurement, self).__init__(phy, self.PRECISION_TIME_MEASUREMENT, b'')
