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

from kitty.targets.server import ServerTarget


class EmptyTarget(ServerTarget):
    '''
    Target that does nothing. Weird, but sometimes it is required.
    '''

    def __init__(self, name, logger=None):
        '''
        :param name: name of the target
        :param logger: logger for this object (default: None)
        '''
        super(EmptyTarget, self).__init__(name, logger)
        self.expect_response = False

    def _send_to_target(self, payload):
        pass

    def _receive_from_target(self):
        return ''
