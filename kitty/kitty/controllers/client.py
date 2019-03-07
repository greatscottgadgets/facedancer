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
``ClientController`` is a controller for victim in client mode,
it inherits from :class:`~kitty.controllers.base.BaseController`,
and implements one additional method:
:func:`~kitty.controllers.client.ClientController.trigger`.
'''
from kitty.controllers.base import BaseController


class ClientController(BaseController):
    '''
    Base class for client controllers.
    '''

    def trigger(self):
        '''
        Trigger a data exchange from the tested client
        '''
        self.not_implemented('trigger')
