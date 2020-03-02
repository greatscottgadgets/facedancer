

# Standard types.
from .device        import USBDevice
from .configuration import USBConfiguration
from .interface     import USBInterface
from .endpoint      import USBEndpoint
from .descriptor    import USBDescriptor, USBClassDescriptor, USBDescriptorTypeNumber

# Control request handlers.
from .request       import standard_request_handler, class_request_handler, vendor_request_handler
from .request       import to_device, to_endpoint, to_interface, to_other

# Raw types.
from .types         import USBDirection, USBTransferType, USBUsageType, USBSynchronizationType
from .types         import USBRequestType, USBRequestRecipient

# Decorators.
from .magic import use_automatically, use_inner_classes_automatically
