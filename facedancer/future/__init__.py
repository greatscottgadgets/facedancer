

# Standard types.
from .device        import USBDevice
from .configuration import USBConfiguration
from .interface     import USBInterface
from .endpoint      import USBEndpoint
from .descriptor    import USBDescriptor, USBClassDescriptor, USBDescriptorTypeNumber

# Raw types.
from .types         import USBDirection, USBTransferType, USBUsageType, USBSynchronizationType
from .types         import USBRequestType, USBRequestRecipient

# Decorators.
from .magic import use_automatically, use_inner_classes_automatically
