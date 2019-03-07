# Copyright (C) 2016 Cisco Systems, Inc. and/or its affiliates. All rights reserved.
#
# This file is part of Kitty.
#
# Kitty is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Kitty is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Kitty.  If not, see <http://www.gnu.org/licenses/>.

'''
The controller is in charge of preparing the victim for the test.
It should make sure that the victim is in an appropriate state before
the target initiates the transfer session. Sometimes it means doing nothing,
other times it means starting or reseting a VM, killing a process
or performing a hard reset to the victim hardware.
Since the controller is reponsible for the state of the victim,
it is expected to perform a basic monitoring as well, and report whether
the victim is ready for the next test.
'''
from kitty.core.actor import KittyActorInterface


class BaseController(KittyActorInterface):
    '''
    Base class for controllers. Defines basic variables and implements basic behavior.
    '''
    pass
