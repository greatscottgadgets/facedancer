from ..usb import USB


class USBDescribable(object):
    """
    Abstract base class for objects that can be created from USB descriptors.
    """

    # Override me!
    DESCRIPTOR_TYPE_NUMBER = None

    @classmethod
    def handles_binary_descriptor(cls, data):
        """
        Returns truee iff this class handles the given descriptor. By deafault,
        this is based on the class's DESCRIPTOR_TYPE_NUMBER declaration.
        """
        return data[1] == cls.DESCRIPTOR_TYPE_NUMBER



    @classmethod
    def from_binary_descriptor(cls, data):
        """
        Attempts to create a USBDescriptor subclass from the given raw
        descriptor data.
        """

        for subclass in cls.__subclasses__():
            # If this subclass handles our binary descriptor, use it to parse the given descriptor.
            if subclass.handles_binary_descriptor(data):
                return subclass.from_binary_descriptor(data)

        return None
