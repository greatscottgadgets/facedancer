'''
Hub templates
'''
from facedancer.usb.USB import DescriptorType
from kitty.model import UInt8, LE16, RandomBytes
from kitty.model import Size
from generic import Descriptor


# hub_descriptor

'''
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
        d += '\x00' * num_bytes
        d += '\xff' * num_bytes
        d = struct.pack('B', len(d) + 1) + d
        return d
'''

hub_descriptor = Descriptor(
    name='hub_descriptor',
    descriptor_type=DescriptorType.hub,
    fields=[
        Size(name='bNbrPorts', sized_field='DeviceRemovable', length=8, calc_func=lambda x: len(x) * 7),
        LE16(name='wHubCharacteristics', value=0x0000),
        UInt8(name='bPwrOn2PwrGood', value=0x00),
        UInt8(name='bHubContrCurrent', value=0x02),
        RandomBytes(name='DeviceRemovable', value='\x00', min_length=0, max_length=250),
    ])
