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
The kitty.fuzzers module provides fuzzer classes.
In most cases, there is no need to extend those classes, and they may be used
as is.

:class:`~kitty.fuzzers.base.BaseFuzzer` should not be instantiated, and only
serves as a common parent for :class:`~kitty.fuzzers.client.ClientFuzzer` and
:class:`~kitty.fuzzers.server.ServerFuzzer`.

:class:`~kitty.fuzzers.client.ClientFuzzer` should be used when the fuzzer
provides payloads to some server stack in a client fuzzing session.

:class:`~kitty.fuzzers.server.ServerFuzzer` should be used when the fuzzer
instantiates the communication, in cases such as fuzzing a server of some sort
or when writing payloads to files.
'''
from kitty.fuzzers.base import BaseFuzzer
from kitty.fuzzers.client import ClientFuzzer
from kitty.fuzzers.server import ServerFuzzer
