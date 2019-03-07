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
Usage:
    ./runner [--kitty-options=<kitty-options>]

Options:
    -k --kitty-options <kitty-options>  options for the kitty fuzzer, use --kitty-options=--help to get a full list

This example stores the mutations in files under ./tmp/
It also demonstrate how to user kitty fuzzer command line options.
'''

import docopt
import six
from kitty.fuzzers import ServerFuzzer
from kitty.interfaces import WebInterface
from kitty.controllers import EmptyController
from katnip.targets.file import FileTarget
from kitty.model import GraphModel
from kitty.model import String
from kitty.model import Template

opts = docopt.docopt(__doc__)
t1 = Template(name='T1', fields=[
    String('The default string', name='S1_1'),
    String('Another string', name='S1_2'),
])

# Writes content to files
target = FileTarget('FileTarget', 'tmp/', 'fuzzed')
controller = EmptyController('EmptyController')
target.set_controller(controller)

model = GraphModel()
model.connect(t1)

fuzzer = ServerFuzzer(name="Example 1 - File Generator", option_line=opts['--kitty-options'])
fuzzer.set_interface(WebInterface(port=26001))
fuzzer.set_model(model)
fuzzer.set_target(target)
fuzzer.start()
print('-------------- done with fuzzing -----------------')
six.moves.input('press enter to exit')
fuzzer.stop()
