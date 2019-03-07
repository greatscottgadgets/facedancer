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

import os
from kitty.model import Template
from kitty.model import GraphModel
from kitty.fuzzers import ClientFuzzer
from kitty.interfaces import WebInterface
from katnip.controllers.client.process import ClientProcessController
from kitty.targets import ClientTarget
from kitty.remote import RpcServer

from katnip.legos.xml import XmlElement


def main():
    test_name = 'GET fuzzed'
    get_template = Template(name=test_name, fields=[
        XmlElement(name='html', element_name='html', content=[
            XmlElement(name='head', element_name='head', content='<meta http-equiv="refresh" content="5; url=/">'),
            XmlElement(name='body', element_name='body', content='123', fuzz_content=True),
        ])
    ])

    fuzzer = ClientFuzzer(name='Example 2 - Browser Fuzzer (Remote)')
    fuzzer.set_interface(WebInterface(host='0.0.0.0', port=26000))

    target = ClientTarget(name='BrowserTarget')

    #
    # Note: to avoid opening the process on our X server, we use another display for it
    # display ':2' that is specified below was started this way:
    # >> sudo apt-get install xvfb
    # >> Xvfb :2 -screen 2 1280x1024x8
    #
    env = os.environ.copy()
    env['DISPLAY'] = ':2'
    controller = ClientProcessController(
        'BrowserController',
        '/usr/bin/opera',
        ['http://localhost:8082/fuzzed'],
        process_env=env
    )
    target.set_controller(controller)
    target.set_mutation_server_timeout(20)

    model = GraphModel()
    model.connect(get_template)
    fuzzer.set_model(model)
    fuzzer.set_target(target)

    #
    # only fuzz the half of the mutations, just as an example
    fuzzer.set_range(end_index=model.num_mutations() // 2)
    fuzzer.set_delay_between_tests(0.1)

    remote = RpcServer(host='localhost', port=26007, impl=fuzzer)
    remote.start()


if __name__ == '__main__':
    main()
