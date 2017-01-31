# USB.py
#
# Contains definition of USB class, which is just a container for a bunch of
# constants/enums associated with the USB protocol.
#
# TODO: would be nice if this module could re-export the other USB* classes so
# one need import only USB to get all the functionality

class USB:
    state_detached                      = 0
    state_attached                      = 1
    state_powered                       = 2
    state_default                       = 3
    state_address                       = 4
    state_configured                    = 5
    state_suspended                     = 6

    request_direction_host_to_device    = 0
    request_direction_device_to_host    = 1

    request_type_standard               = 0
    request_type_class                  = 1
    request_type_vendor                 = 2

    request_recipient_device            = 0
    request_recipient_interface         = 1
    request_recipient_endpoint          = 2
    request_recipient_other             = 3

    feature_endpoint_halt               = 0
    feature_device_remote_wakeup        = 1
    feature_test_mode                   = 2

    desc_type_device                    = 1
    desc_type_configuration             = 2
    desc_type_string                    = 3
    desc_type_interface                 = 4
    desc_type_endpoint                  = 5
    desc_type_device_qualifier          = 6
    desc_type_other_speed_configuration = 7
    desc_type_interface_power           = 8
    desc_type_hid                       = 33
    desc_type_report                    = 34

    # while this holds for HID, it may not be a correct model for the USB
    # ecosystem at large
    if_class_to_desc_type = {
            3 : desc_type_hid
    }

    def interface_class_to_descriptor_type(interface_class):
        return USB.if_class_to_desc_type.get(interface_class, None)

