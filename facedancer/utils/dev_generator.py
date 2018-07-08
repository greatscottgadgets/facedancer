#!/usr/bin/env python
'''
Generate a umap2 USB device python code from device and configuration descriptors

Usage:
    umap2mkdevice <DEVICE_DESCRIPTOR> <CONFIGURATION_DESCRIPTOR> ...

Arguments:
    DEVICE_DESCRIPTOR           device descriptor (hex)
    CONFIGURATION_DESCRIPTOR    one (or more) configuration descriptors

Example(write in one line ...):

    umap2mkdevice 120100020000004012831283000001020001 \\
    09022e00010100c0fa0904000004ff00000007058203000401070504020002000705860200020007058802000200
'''
from docopt import docopt
from binascii import unhexlify, hexlify
import struct
from umap2.core.usb import DescriptorType


def get_device_descriptor(opts):
    return unhexlify(opts['<DEVICE_DESCRIPTOR>'])


def get_configuration_descriptors(opts):
    return [unhexlify(desc) for desc in opts['<CONFIGURATION_DESCRIPTOR>']]


def add_indentation(s, count=1):
    ind = '\n' + '    ' * count
    return ind + ind.join(s.split('\n'))


class DescriptorNode(object):

    def __init__(self, node_type):
        self.node_type = node_type
        self.deps = []
        self.parent = None

    def get_by_type(self, req_type):
        # print 'get_by_type: %02x (%02x)' % (req_type, self.node_type)
        if self.node_type == req_type:
            return self
        elif self.parent is None:
            raise Exception('Can\'t find node of type %s' % (req_type))
        else:
            return self.parent.get_by_type(req_type)

    def get_dep_by_type(self, def_node):
        for dep in self.deps:
            if dep.node_type == def_node.node_type:
                return dep
        self.deps.append(def_node)
        def_node.parent = self
        return def_node

    def get_pre(self):
        # print 'to_code(node_type: %02x)' % (self.node_type)
        pre_code = ''
        available_list_types = set([n.node_type for n in self.deps if isinstance(n, ListNode)])
        known_list_types = set(t for t in self.list_names)
        if any(x not in known_list_types for x in available_list_types):
            example = [x not in known_list_types for x in available_list_types][0]
            raise Exception('An unknown list found, of type: %02x' % (example))
        for t in known_list_types:
            if t not in available_list_types:
                pre_code += '%s = None\n' % (self.list_names[t])
        for dep in self.deps:
            if isinstance(dep, ListNode):
                pre_code += dep.get_pre()
                pre_code += '%s = %s\n' % (self.list_names[dep.node_type], dep.get_text())
            else:
                pre_code += '%s\n' % (dep.to_code())
        return pre_code

    def get_text(self):
        return self.text

    def to_code(self):
        return self.get_pre() + self.get_text()


class RootNode(DescriptorNode):

    def __init__(self):
        super(RootNode, self).__init__(0xff)

    def to_code(self):
        fres = ''
        for dep in self.deps:
            pre_code = '''# This script was auto generated from descriptors
from umap2.core.usb_device import USBDevice
from umap2.core.usb_configuration import USBConfiguration
from umap2.core.usb_interface import USBInterface
from umap2.core.usb_endpoint import USBEndpoint
from umap2.core.usb_cs_interface import USBCSInterface
from umap2.core.usb_cs_endpoint import USBCSEndpoint


class USBMyDevice(USBDevice):

    def __init__(self, app, phy, vid=0x%04x, pid=0x%04x, **kwargs):''' % (dep.vendor_id, dep.product_id)
            res = ''
            res += 'strings_dict = {}\n'
            res += 'usb_class = None\n'
            res += 'usb_vendor = None\n'
            res += dep.get_pre()
            res += dep.get_text()
            res = add_indentation(res, 2)
            res += '\n\nusb_device = USBMyDevice\n'
            fres += pre_code + res
        return fres


class ListNode(DescriptorNode):

    def __init__(self, node_type):
        super(ListNode, self).__init__(node_type)

    def get_pre(self):
        res = ''.join(dep.get_pre() for dep in self.deps)
        return res

    def get_text(self):
        res = '['
        res += ','.join(add_indentation(dep.get_text()) for dep in self.deps)
        res += '\n]'
        return res


def parse_pfn(desc_type):
    def parser_wrapper(pfn):
        def wrapper(self, desc):
            # print 'Parsing desc %02x: %s' % (desc_type, hexlify(desc))
            self.select_node(desc_type)
            node = DescriptorNode(desc_type)
            node.text = pfn(self, desc, node)
            self.push_node(node)
        return wrapper
    return parser_wrapper


def build_init(cls_name, params):
    params.insert(0, ('phy', 'phy'))
    params.insert(0, ('app', 'app'))
    s = '%s(\n    ' % (cls_name)
    s += ',\n    '.join('%s=%s' % (a, b if type(b) != int else hex(b)) for (a, b) in params)
    s += '\n)'
    return s


class Parser(object):
    transfer_types = ('USBEndpoint.transfer_type_', ['control', 'isochronous', 'bulk', 'interrupt'])
    sync_types = ('USBEndpoint.sync_type_', ['none', 'async', 'adaptive', 'synchronous'])
    usage_types = ('USBEndpoint.usage_type_', ['data', 'feedback', 'implicit_feedback'])

    def __init__(self, opts):
        self.opts = opts
        self.root_node = RootNode()
        self.curr_node = self.root_node
        self.parsers = {
            DescriptorType.configuration: self.parse_configuration_desc,
            DescriptorType.interface: self.parse_interface_desc,
            DescriptorType.cs_interface: self.parse_cs_interface_desc,
            DescriptorType.endpoint: self.parse_endpoint_desc,
            DescriptorType.cs_endpoint: self.parse_cs_endpoint_desc,
        }

    def endpoint_constant(self, const_types, value):
        if value < len(const_types[1]):
            return const_types[0] + const_types[1][value]
        else:
            return '%#x' % (value)

    def push_node(self, node):
        self.curr_node.deps.append(node)
        node.parent = self.curr_node
        self.curr_node = node

    def get_node(self, desc_type):
        list_node_reqs = {
            DescriptorType.configuration: DescriptorType.device,
            DescriptorType.interface: DescriptorType.configuration,
            DescriptorType.cs_interface: DescriptorType.interface,
            DescriptorType.endpoint: DescriptorType.interface,
            DescriptorType.cs_endpoint: DescriptorType.endpoint
        }
        if desc_type in list_node_reqs:
            p_node = self.curr_node.get_by_type(list_node_reqs[desc_type])
            return p_node.get_dep_by_type(ListNode(desc_type))
        elif desc_type == DescriptorType.device:
            return self.root_node

    def select_node(self, desc_type):
        self.curr_node = self.get_node(desc_type)

    @parse_pfn(DescriptorType.cs_endpoint)
    def parse_cs_endpoint_desc(self, desc, node):
        return build_init('CSEndpoint', [
            ('name', "'CSEndpoint'"),
            ('cs_config', "'%s'" % (desc[2:]))
        ])

    @parse_pfn(DescriptorType.endpoint)
    def parse_endpoint_desc(self, desc, node):
        if len(desc) != 7:
            raise Exception('endpoint descriptor length is not 7 bytes')
        (
            _, bDescriptorType, address,
            attributes, max_packet_size, interval
        ) = struct.unpack('<BBBBHB', desc)
        direction = 'in' if address & 0x80 == 0x80 else 'out'
        number = address & 0x7f
        handler_name = 'handle_ep%d_%s_available' % (number, direction)
        cs_endpoints_name = "endpoint_%s_cs_endpoints" % (number)
        s = build_init('USBEndpoint', [
            ("number", number),
            ("direction", 'USBEndpoint.direction_' + direction),
            ("transfer_type", self.endpoint_constant(self.transfer_types, attributes & 0x03)),
            ("sync_type", self.endpoint_constant(self.sync_types, (attributes >> 2) & 0x03)),
            ("usage_type", self.endpoint_constant(self.usage_types, (attributes >> 4) & 0x03)),
            ("max_packet_size", max_packet_size),
            ("interval", interval),
            ("handler", handler_name),
            ("cs_endpoints", cs_endpoints_name),
            ('usb_class', 'usb_class'),
            ('usb_vendor', 'usb_vendor'),
        ])
        node.list_names = {
            DescriptorType.cs_endpoint: cs_endpoints_name,
        }
        return s

    @parse_pfn(DescriptorType.cs_interface)
    def parse_cs_interface_desc(self, desc, node):
        return build_init('CSInterface', [
            ("cs_config", "'%s'" % (desc[2:])),
            ("name", "'CSInterface'")
        ])

    @parse_pfn(DescriptorType.interface)
    def parse_interface_desc(self, desc, node):
        if len(desc) != 9:
            raise Exception('interface descriptor length is not 9 bytes')
        (
            _, bDescriptorType, number, alternate,
            _, iclass, subclass, protocol,
            string_index
        ) = struct.unpack('<BBBBBBBBB', desc)
        if bDescriptorType != DescriptorType.interface:
            raise Exception('This is not an interface descriptor!')
        endpoints_name = 'interface_%s_endpoints' % (number)
        cs_interfaces_name = 'interface_%s_cs_interfaces' % (number)
        s = build_init('USBInterface', [
            ('interface_number', number),
            ('interface_alternate', alternate),
            ('interface_class', iclass),
            ('interface_subclass', subclass),
            ('interface_protocol', protocol),
            ('interface_string_index', string_index),
            ('endpoints', endpoints_name),
            # by default, no additional descriptors
            # ('descriptors', 'interface_%s_descriptors' % (number)),
            ('descriptors', 'None'),
            ('cs_interfaces', cs_interfaces_name),
            ('usb_class', 'usb_class'),
            ('usb_vendor', 'usb_vendor'),
        ])
        node.list_names = {
            DescriptorType.endpoint: endpoints_name,
            DescriptorType.cs_interface: cs_interfaces_name,
        }
        return s

    @parse_pfn(DescriptorType.configuration)
    def parse_configuration_desc(self, desc, node):
        if len(desc) != 9:
            raise Exception('configuration descriptor length is not 9 bytes')
        (
            _, bDescriptorType, _, _,
            index, string_index, attributes, max_power
        ) = struct.unpack('<BBHBBBBB', desc)
        if bDescriptorType != DescriptorType.configuration:
            raise Exception('This is not a configuration descriptor! %02x' % (bDescriptorType))
        interfaces_name = "config_%s_interfaces" % (index)
        s = build_init('USBConfiguration', [
            ('index', index),
            ('string', "strings_dict.get(%s, 'Config-%s')" % (string_index, string_index)),
            ('interfaces', interfaces_name),
            ('attributes', attributes),
            ('max_power', max_power),
        ])
        node.list_names = {
            DescriptorType.interface: interfaces_name,
        }
        return s

    @parse_pfn(DescriptorType.device)
    def parse_device_desc(self, desc, node):
        if len(desc) != 18:
            raise Exception('device descriptor length is not 18 bytes')
        (
            _, bDescriptorType, _, device_class, device_subclass, protocol_rel_num,
            max_packet_size_ep0, vendor_id, product_id, device_rev, manufacturer_string_id,
            product_string_id, serial_number_string_id, _
        ) = struct.unpack('<BBHBBBBHHHBBBB', desc)
        if bDescriptorType != DescriptorType.device:
            raise Exception('This is not a device descriptor!')
        configurations_name = 'configurations'
        s = build_init('super(USBMyDevice, self).__init__', [
            ('device_class', device_class),
            ('device_subclass', device_subclass),
            ('protocol_rel_num', protocol_rel_num),
            ('max_packet_size_ep0', max_packet_size_ep0),
            ('vendor_id', 'vid'),
            ('product_id', 'pid'),
            ('device_rev', device_rev),
            ('manufacturer_string', "strings_dict.get(%s, 'VID-%s')" % (manufacturer_string_id, manufacturer_string_id)),
            ('product_string', "strings_dict.get(%s, 'PID-%s')" % (product_string_id, product_string_id)),
            ('serial_number_string', "strings_dict.get(%s, 'S/N-%s')" % (serial_number_string_id, serial_number_string_id)),
            ('configurations', 'configurations'),
            # by default, no additional descriptors
            # ('descriptors', 'descriptors'),
            ('descriptors', 'None'),
            ('usb_class', 'usb_class'),
            ('usb_vendor', 'usb_vendor'),
        ])
        node.list_names = {
            DescriptorType.configuration: configurations_name,
        }
        node.vendor_id = vendor_id
        node.product_id = product_id
        return s

    def parse_config_desc(self, desc_buff):
        while len(desc_buff):
            if len(desc_buff) < 2:
                raise Exception('Invalid configuration descriptor')
            desc_len, desc_type = struct.unpack('BB', desc_buff[:2])
            if desc_len > len(desc_buff):
                raise Exception('Invalid descriptor length: %02x %s' % (desc_len, hexlify(desc_buff)))
            if desc_type not in self.parsers:
                raise Exception('Invalid descriptor type: %02x %s' % (desc_len, hexlify(desc_buff)))
            current_desc = desc_buff[:desc_len]
            desc_buff = desc_buff[desc_len:]
            self.parsers[desc_type](current_desc)

    def parse_config_descs(self, config_descs):
        for desc_buff in config_descs:
            self.parse_config_desc(desc_buff)

    def emit_output(self):
        print self.root_node.to_code()


def main():
    opts = docopt(__doc__)
    device_desc = get_device_descriptor(opts)
    config_descs = get_configuration_descriptors(opts)
    parser = Parser(opts)
    parser.parse_device_desc(device_desc)
    parser.parse_config_descs(config_descs)
    parser.emit_output()

if __name__ == '__main__':
    main()
