# Copyright (C) 2016 Cisco Systems, Inc. and/or its affiliates. All rights reserved.
#
# This file is part of Katnip.
#
# Katnip is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Katnip is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Katnip.  If not, see <http://www.gnu.org/licenses/>.
'''
Legos to generate USB HID reports
'''
from facedancer.usb.USB import DescriptorType
from kitty.model import Template, Container, OneOf, TakeFrom
from kitty.model import MutableField
from kitty.model import UInt8, LE16, BitField, Static
from kitty.model import ENC_INT_LE
from kitty.core import KittyException
from random import Random
from generic import DynamicInt, Descriptor


opcodes = {
    0x04: 'Usage Page',
    0x08: 'Usage',
    0x14: 'Logical Minimum',
    0x18: 'Usage Minimum',
    0x24: 'Logical Maximum',
    0x28: 'Usage Maximum',
    0x34: 'Physical Minimum',
    0x38: 'Designator Index',
    0x44: 'Physical Maximum',
    0x48: 'Designator Minimum',
    0x54: 'Unit Exponent',
    0x58: 'Designator Maximum',
    0x64: 'Unit',
    0x74: 'Report Size',
    0x78: 'String Index',
    0x80: 'Input',
    0x84: 'Report ID',
    0x88: 'String Minimum',
    0x90: 'Output',
    0x94: 'Report Count',
    0x98: 'String Maximum',
    0xA0: 'Collection',
    0xA4: 'Push',
    0xA8: 'Delimiter',
    0xB0: 'Feature',
    0xB4: 'Pop',
    0xC0: 'End Collection',
}


class NameGen(object):
    def __init__(self):
        self.names = {}

    def gen(self, opcode):
        args = opcode & 0x3
        tag = opcode & 0xfc
        base_name = ('opcode_%02x' % tag) if tag not in opcodes else opcodes[tag]
        base_name += '[%d]' % args
        if base_name not in self.names:
            self.names[base_name] = 0
            cur_name = base_name
        else:
            self.names[base_name] += 1
            cur_name = '%s <%d>' % (base_name, self.names[base_name])
        return cur_name


class RandomHidReport(TakeFrom):
    '''
    Generate random sequences of valid, interesting opcodes, and try to screw them up.
    '''

    def __init__(self, name=None, fuzzable=True):
        namer = NameGen()
        fields = []
        r = Random()
        for tag in opcodes:
            for i in range(4):
                opcode = tag | i
                current = chr(opcode)
                for j in range(i):
                    current += chr(r.randint(0, 255))
                fields.append(Static(name=namer.gen(opcode), value=current))
        super(RandomHidReport, self).__init__(
            fields=fields,
            min_elements=10,
            max_elements=40,
            fuzzable=fuzzable,
            name=name
        )


def GenerateHidReport(report_str, name=None):
    '''
    Generate an HID report Container from a HID report string

    :param report_str: HID report string
    :param name: name of generated Container (default: None)
    :raises: KittyException if not enough bytes are left for command

    :examples:

        ::

            Template(
                name='MyHidReport',
                fields=GenerateHidReport(
                    '05010906A101050719E029E7150025017501950881029501750881011900296515002565750895018100C0',
                )
            )
    '''
    fields = []
    index = 0
    namer = NameGen()
    while index < len(report_str):
        opcode = ord(report_str[index])
        num_args = opcode & 3
        if index + num_args >= len(report_str):
            raise KittyException('Not enough bytes in hid report for last opcode')
        index += 1
        cur_name = namer.gen(opcode)
        if num_args == 0:
            fields.append(UInt8(opcode, name=cur_name))
        else:
            args = report_str[index:index + num_args]
            value = sum(ord(args[i]) << (i * 8) for i in range(len(args)))  # little endian...
            fields.append(Container(
                name=cur_name,
                fields=[
                    UInt8(opcode, name='opcode'),
                    BitField(value, 8 * len(args), encoder=ENC_INT_LE, name='value')
                ]
            ))
        index += num_args
    return OneOf(
        name=name,
        fields=[
            Container(
                name='generation',
                fields=fields
            ),
            MutableField(
                name='mutation',
                value=report_str
            ),
            RandomHidReport(
                name='random_sequences'
            ),
        ])

# ############### Templates ############### #

hid_descriptor = Descriptor(
    name='hid_descriptor',
    descriptor_type=DescriptorType.hid,
    fields=[
        DynamicInt('bcdHID', LE16(value=0x0110)),
        DynamicInt('bCountryCode', UInt8(value=0x00)),
        DynamicInt('bNumDescriptors', UInt8(value=0x01)),
        DynamicInt('bDescriptorType2', UInt8(value=DescriptorType.hid)),
        DynamicInt('wDescriptorLength', LE16(value=0x27)),
    ])


# this descriptor is based on umap
# https://github.com/nccgroup/umap
# commit 3ad812135f8c34dcde0e055d1fefe30500196c0f
hid_report_descriptor = Template(
    name='hid_report_descriptor',
    fields=GenerateHidReport(
        '05010906A101050719E029E7150025017501950881029501750881011900296515002565750895018100C0'.decode('hex')
    )
)
