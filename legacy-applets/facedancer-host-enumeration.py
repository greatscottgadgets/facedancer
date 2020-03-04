#!/usr/bin/env python3
#
# Simplest possible example of using the FaceDancer host API.

from facedancer import FacedancerUSBHostApp

# Enumerate and configure the attached device.
u = FacedancerUSBHostApp(verbose=3)
u.initialize_device(assign_address=1, apply_configuration=1)

# At this point, we can perform whatever communications we need to to use the target device.
# Usually, this is accomplsihed using the send_on_endpoint and read_from_endpoint functions
# for non-control requests, and the control_request_in and control_request out functions
# for control requests.

# Print the device state.
print("Device initialized: ")
print("\tDevice is: {}".format("Connected" if u.device_is_connected() else "Disconnected"))
print("\tDevice speed: {}".format(u.current_device_speed(as_string=True)))
print("\tPort is: {}".format("Enabled" if u.port_is_enabled() else "Disabled"))
print("\tPort power is: {}".format("On" if (u.port_is_powered()) else "Off"))
print("\tLine state: {}".format(u.current_line_state(as_string=True)))

# Print information about the attached device...
print("Attached device: {}".format(u.get_device_descriptor()))

# .. and its configuration.
configuration = u.get_configuration_descriptor()
print("Using first configuration: {}".format(configuration))

for interface in configuration.interfaces:
    print("\t - {}".format(interface))

    for endpoint in interface.endpoints:
        print("\t\t - {}".format(endpoint))
