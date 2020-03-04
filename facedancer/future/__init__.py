
# Standard types.
from .device        import USBDevice
from .configuration import USBConfiguration
from .interface     import USBInterface
from .endpoint      import USBEndpoint
from .descriptor    import USBDescriptor, USBClassDescriptor, USBDescriptorTypeNumber

# Control request handlers.
from .request       import standard_request_handler, class_request_handler, vendor_request_handler
from .request       import to_device, to_this_endpoint, to_this_interface, to_other
from .request       import to_any_endpoint, to_any_interface

# Raw types.
from .types         import USBDirection, USBTransferType, USBUsageType, USBSynchronizationType
from .types         import USBRequestType, USBRequestRecipient, USBStandardRequests, LanguageIDs

# Decorators.
from .magic import use_automatically, use_inner_classes_automatically

# Wildcard import.
__all__ = [
    'USBDevice', 'USBConfiguration', 'USBInterface', 'USBEndpoint', 'USBDescriptor',
    'USBClassDescriptor', 'USBDescriptorTypeNumber', 'standard_request_handler',
    'class_request_handler', 'vendor_request_handler', 'to_device', 'to_this_endpoint',
    'to_any_endpoint', 'to_this_interface', 'to_any_interface', 'to_other',
    'USBDirection', 'USBTransferType', 'USBUsageType', 'USBSynchronizationType',
    'USBRequestType', 'USBRequestRecipient', 'USBStandardRequests', 'LanguageIDs',
    'use_automatically', 'use_inner_classes_automatically',
]
