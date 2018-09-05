#!/usr/bin/env python3
#
# facedancer-keyboard.py

from facedancer import FacedancerUSBHostApp

u = FacedancerUSBHostApp(verbose=3)
u.initialize_device()

# Print the device state.
print("Device initialized: ")
print("\tDevice is: {}".format("Connected" if u.device_is_connected() else "Disconnected"))
print("\tDevice speed: {}".format(u.current_device_speed(as_string=True)))
print("\tPort is: {}".format("Enabled" if u.port_is_enabled() else "Disabled"))
print("\tPort power is: {}".format("On" if (u.port_is_powered()) else "Off"))
print("\tLine state: {}".format(u.current_line_state(as_string=True)))


print("Attached device: {}".format(u.get_device_descriptor()))
