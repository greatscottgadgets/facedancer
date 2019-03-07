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

import six
from kitty.fuzzers import ServerFuzzer
from kitty.interfaces import WebInterface
from katnip.targets.file import FileTarget
from kitty.model import GraphModel
from kitty.model import String
from kitty.model import Template
from kitty.remote.actor import RemoteActor


t1 = Template(name='T1', fields=[
    String('The default string', name='S1_1'),
])

# Writes content to files
target = FileTarget('FileTarget', 'tmp/', 'fuzzed')

#
# connects to actual actor (controller) over RPC
#
controller = RemoteActor('127.0.0.1', 25002)
target.set_controller(controller)

model = GraphModel()
model.connect(t1)

fuzzer = ServerFuzzer(name='Example 4 - File Generator(Remote Controller)')
fuzzer.set_interface(WebInterface(port=26001))
fuzzer.set_model(model)
fuzzer.set_target(target)
# No need for delay, we only create files
# fuzzer.set_delay_between_tests(0.02)
# No need for range, generate all
# fuzzer.set_range(50)
fuzzer.start()
print('-------------- done with fuzzing -----------------')
six.moves.input('press enter to exit')
fuzzer.stop()
