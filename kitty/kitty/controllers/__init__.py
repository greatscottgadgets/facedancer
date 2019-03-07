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
The kitty.controllers package provide the basic controller classes.
The controller role is to provide means to start/stop the victim and put it in
the appropriate state for a test.

:class:`~kitty.controllers.base.BaseController` should not be instantiated. It
should be extended when performing server fuzzing.

:class:`~kitty.controllers.client.ClientController` is used for client fuzzing.
It should be extended with an implementation for the
:func:`~kitty.controllers.client.ClientController.trigger` function to trigger
the victim to start the communications.

:class:`~kitty.controllers.empty.EmptyController` is used when no actual work
should be done by the controller.
'''
from kitty.controllers.base import BaseController
from kitty.controllers.client import ClientController
from kitty.controllers.empty import EmptyController
