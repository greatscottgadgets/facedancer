# USB.py
#
# Contains definition of USB class, which is just a container for a bunch of
# constants/enums associated with the USB protocol.
#
# TODO: would be nice if this module could re-export the other USB* classes so
# one need import only USB to get all the functionality
import time
import logging
start_time = time.time()

class DescriptorType(object):
    device = 0x01
    configuration = 0x02
    string = 0x03
    interface = 0x04
    endpoint = 0x05
    device_qualifier = 0x06
    other_speed_configuration = 0x07
    interface_power = 0x08
    bos = 0x0f
    device_capability = 0x10
    hid = 0x21
    report = 0x22
    cs_interface = 0x24
    cs_endpoint = 0x25
    hub = 0x29


class USB(object):
    feature_endpoint_halt = 0
    feature_device_remote_wakeup = 1
    feature_test_mode = 2

    # while this holds for HID, it may not be a correct model for the USB
    # ecosystem at large
    if_class_to_desc_type = {
        0x03: DescriptorType.hid,
        0x0b: DescriptorType.hid
    }
    
def interface_class_to_descriptor_type(interface_class):
    return USB.if_class_to_desc_type.get(interface_class, None)


class State(object):
    detached = 0
    attached = 1
    powered = 2
    default = 3
    address = 4
    configured = 5
    suspended = 6


class Request(object):
    direction_host_to_device = 0
    direction_device_to_host = 1

    type_standard = 0
    type_class = 1
    type_vendor = 2

    recipient_device = 0
    recipient_interface = 1
    recipient_endpoint = 2
    recipient_other = 3 


class USBDescribable(object):
    """
    Abstract base class for objects that can be created from USB descriptors.
    """

    # Override me!
    DESCRIPTOR_TYPE_NUMBER = None

    def __init__(self, phy):
        self.phy = phy
        self.session_data = {}
        self.str_dict = {}
        self.logger = logging.getLogger('facedancer')

    def get_mutation(self, stage, data=None):
        '''
        :param stage: stage name
        :param data: dictionary (string: bytearray) of data for the fuzzer (default: None)
        :return: mutation for current stage, None if not current fuzzing stage
        '''
        return self.phy.get_mutation(stage, data)

    def send_on_endpoint(self, ep, data):
        '''
        Send data on a given endpoint

        :param ep: endpoint number
        :param data: data to send
        '''
        self.phy.send_on_endpoint(ep, data)

        
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

    def get_session_data(self, stage):
        '''
        If an entity wants to pass specific data to the fuzzer when getting a mutation,
        it could return a session data here.
        This session data should be a dictionary of string:bytearray.
        The keys of the dictionary should match the keys in the templates.

        :param stage: stage that the session data is for
        :return: dictionary of session data
        '''
        return self.session_data

    def usb_function_supported(self, reason=None):
        '''
        Mark current USB function as supported by the host.
        This will tell the application to stop emulating current device.

        :param reason: reason why we decided it is supported (default: None)
        '''
        self.phy.usb_function_supported(reason)

    def add_string_with_id(self, str_id, s):
        '''
        Add a string to the string dictionary

        :param str_id: id of the string
        :param s: the string
        '''
        self.str_dict[str_id] = s

    def get_string_by_id(self, str_id):
        '''
        Get a string by it's id

        :param str_id: string id
        :return: the string, or None if id does not exist
        '''
        self.debug('Getting string by id %#x' % (str_id))
        if str_id in self.str_dict:
            return self.str_dict[str_id]
        return None

    def verbose(self, msg, *args, **kwargs):
        self.logger.verbose('[%s] %s' % (self.name, msg), *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.logger.debug('[%s] %s' % (self.name, msg), *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info('[%s] %s' % (self.name, msg), *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning('[%s] %s' % (self.name, msg), *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error('[%s] %s' % (self.name, msg), *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical('[%s] %s' % (self.name, msg), *args, **kwargs)

    def always(self, msg, *args, **kwargs):
        self.logger.always('[%s] %s' % (self.name, msg), *args, **kwargs)