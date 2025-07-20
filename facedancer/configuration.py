from pathlib import Path

# Full updated content of configuration.py with IAD-safe parsing and orphan descriptor support
updated_configuration_py = """
# This file is part of Facedancer.
#
\"\"\" Functionality for describing USB device configurations. \"\"\"

import struct
import textwrap

from dataclasses  import field
from typing       import Iterable

from .types       import USBDirection
from .magic       import instantiate_subordinates, AutoInstantiable
from .request     import USBRequestHandler

from .interface   import USBInterface
from .descriptor  import USBDescribable, USBDescriptor, StringRef
from .endpoint    import USBEndpoint


class USBConfiguration(USBDescribable, AutoInstantiable, USBRequestHandler):
    DESCRIPTOR_TYPE_NUMBER  = 0x02
    DESCRIPTOR_SIZE_BYTES   = 9

    number                 : int            = 1
    configuration_string   : StringRef      = None
    max_power              : int            = 500
    self_powered           : bool           = True
    supports_remote_wakeup : bool           = True
    parent                 : USBDescribable = None
    interfaces             : USBInterface   = field(default_factory=dict)

    @classmethod
    def from_binary_descriptor(cls, data, strings={}):
        length = data[0]
        descriptor_type, total_length, num_interfaces, index, string_index, \
            attributes, half_max_power = struct.unpack_from('<xBHBBBBB', data[0:length])

        configuration = cls(
            number=index,
            configuration_string=StringRef.lookup(strings, string_index),
            max_power=half_max_power * 2,
            self_powered=bool((attributes >> 6) & 1),
            supports_remote_wakeup=bool((attributes >> 5) & 1),
        )

        data = data[length:total_length]
        last_interface = None
        last_endpoint  = None
        configuration._orphan_descriptors = []

        while data:
            length = data[0]
            if length < 2 or length > len(data):
                break

            descriptor = USBDescribable.from_binary_descriptor(data[:length], strings=strings)

            if isinstance(descriptor, USBInterface):
                configuration.add_interface(descriptor)
                last_interface = descriptor
                last_endpoint = None

            elif isinstance(descriptor, USBEndpoint):
                if last_interface is not None:
                    last_interface.add_endpoint(descriptor)
                    last_endpoint = descriptor
                else:
                    configuration._orphan_descriptors.append(descriptor)

            elif isinstance(descriptor, USBDescriptor):
                descriptor.include_in_config = True
                if last_interface is not None:
                    if last_endpoint:
                        last_endpoint.add_descriptor(descriptor)
                    else:
                        last_interface.add_descriptor(descriptor)
                else:
                    configuration._orphan_descriptors.append(descriptor)

            data = data[length:]

        return configuration

    def __post_init__(self):
        self.configuration_string = StringRef.ensure(self.configuration_string)
        for interface in instantiate_subordinates(self, USBInterface):
            self.add_interface(interface)

    @property
    def attributes(self):
        attributes = 0b10000000
        attributes |= (1 << 6) if self.self_powered else 0
        attributes |= (1 << 5) if self.supports_remote_wakeup else 0
        return attributes

    def get_device(self):
        return self.parent

    def add_interface(self, interface: USBInterface):
        identifier = interface.get_identifier()
        num, alt = identifier

        if identifier in self.interfaces:
            other = self.interfaces[identifier]
            raise Exception(
                f"Interface conflict: {type(interface).__name__} conflicts with {type(other).__name__} "
                f"at interface number {num} alt {alt}")
        else:
            self.interfaces[identifier] = interface
            interface.parent = self

    def get_endpoint(self, number: int, direction: USBDirection) -> USBEndpoint:
        for interface in self.active_interfaces.values():
            endpoint = interface.get_endpoint(number, direction)
            if endpoint is not None:
                return endpoint
        return None

    def handle_data_received(self, endpoint: USBEndpoint, data: bytes):
        for interface in self.active_interfaces.values():
            if interface.has_endpoint(endpoint.number, direction=USBDirection.OUT):
                interface.handle_data_received(endpoint, data)
                return
        self.get_device().handle_unexpected_data_received(endpoint.number, data)

    def handle_data_requested(self, endpoint: USBEndpoint):
        for interface in self.active_interfaces.values():
            if interface.has_endpoint(endpoint.number, direction=USBDirection.IN):
                interface.handle_data_requested(endpoint)
                return
        self.get_device().handle_unexpected_data_requested(endpoint.number)

    def handle_buffer_empty(self, endpoint: USBEndpoint):
        for interface in self.active_interfaces.values():
            if interface.has_endpoint(endpoint.number, direction=USBDirection.IN):
                interface.handle_buffer_empty(endpoint)
                return

    def get_interfaces(self) -> Iterable[USBInterface]:
        return self.interfaces.values()

    def get_descriptor(self) -> bytes:
        interface_descriptors = bytearray()

        for desc in getattr(self, "_orphan_descriptors", []):
            interface_descriptors += desc.get_descriptor()

        for interface in self.interfaces.values():
            interface_descriptors += interface.get_descriptor()

        total_len = len(interface_descriptors) + 9
        string_manager = self.get_device().strings

        d = bytes([
            9,
            2,
            total_len & 0xff,
            (total_len >> 8) & 0xff,
            len(set(interface.number for interface in self.interfaces.values())),
            self.number,
            string_manager.get_index(self.configuration_string),
            self.attributes,
            self.max_power // 2
        ])

        return d + interface_descriptors

    def get_identifier(self) -> int:
        return self.number

    def _request_handlers(self) -> Iterable[callable]:
        return ()

    def _get_subordinate_handlers(self) -> Iterable[USBInterface]:
        return self.interfaces.values()

    def generate_code(self, name=None, indent=0):
        if name is None:
            name = f"Configuration_{self.number}"

        code = f\"\"\"
class {name}(USBConfiguration):
    number                 = {self.number}
    configuration_string   = {self.configuration_string.generate_code()}
    max_power              = {self.max_power}
    self_powered           = {repr(self.self_powered)}
    supports_remote_wakeup = {repr(self.supports_remote_wakeup)}
\"\"\"

        for interface in self.interfaces.values():
            code += interface.generate_code(indent=4)

        return textwrap.indent(code, indent * ' ')

"""

# Save it to a file for download
output_path = "/mnt/data/configuration.py"
Path(output_path).write_text(updated_configuration_py)

output_path
