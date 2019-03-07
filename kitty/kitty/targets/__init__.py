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
The kitty.target package provides basic target classes.
The target classes should be extended in most cases.

:class:`~kitty.targets.base.BaseTarget` should not be instantiated, and only
serves as a common parent for :class:`~kitty.targets.client.ClientTarget`,
:class:`~kitty.targets.empty.EmptyTarget` and
:class:`~kitty.targets.server.ServerTarget`.

:class:`~kitty.targets.client.ClientTarget` should be used when fuzzing a
client. In most cases it should not be extended, as the special functionality
(triggering the victim) is done by its :class:`~kitty.controllers.client.ClientController`

:class:`~kitty.targets.empty.EmptyTarget` can be used in server-like fuzzing
when no communication should be done.

:class:`~kitty.targets.server.ServerTarget` should be used when fuzzing a
server. In most cases it should be extended to provide the appropriate
communication means with the server.
'''

from kitty.targets.base import BaseTarget
from kitty.targets.client import ClientTarget
from kitty.targets.empty import EmptyTarget
from kitty.targets.server import ServerTarget
