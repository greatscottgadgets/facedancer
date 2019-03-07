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
import logging
import sys

from kitty.model import Template
from kitty.model import GraphModel
from kitty.fuzzers import ClientFuzzer
from kitty.interfaces import WebInterface
from kitty.targets import ClientTarget
from katnip.controllers.client.process import ClientProcessController
from katnip.legos.xml import XmlElement
if sys.version_info >= (3,):
    from http.server import HTTPServer, BaseHTTPRequestHandler
else:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler


class MyHttpServer(HTTPServer):
    '''
    http://docs.python.org/lib/module-BaseHTTPServer.html
    '''

    def __init__(self, server_address, handler, fuzzer):
        HTTPServer.__init__(self, server_address, handler)
        self.fuzzer = fuzzer


class MyHttpHandler(BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        BaseHTTPRequestHandler.__init__(self, request, client_address, server)

    def do_GET(self):
        resp = None
        if self.path == '/fuzzed':
            resp = self.server.fuzzer.get_mutation(stage="GET fuzzed", data={})
        if resp is None:
            resp = self.default_response()
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        logger = logging.getLogger('kitty')
        logger.info('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
        logger.info('response:')
        logger.info(resp)
        logger.info('<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
        self.wfile.write(resp)

    def default_response(self):
        return """
        <html>
            <head>
                <title>Under test</title>
            </head>
            <body>This system is under test</body>
        </html>
        """


def main():
    test_name = 'GET fuzzed'
    get_template = Template(name=test_name, fields=[
        XmlElement(name='html', element_name='html', content=[
            XmlElement(name='head', element_name='head', content='<meta http-equiv="refresh" content="5; url=/">'),
            XmlElement(name='body', element_name='body', content='123', fuzz_content=True),
        ])
    ])

    fuzzer = ClientFuzzer(name='Example 3 - Browser Fuzzer')
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
    fuzzer.set_delay_between_tests(0.1)

    server = MyHttpServer(('localhost', 8082), MyHttpHandler, fuzzer)

    fuzzer.start()

    while True:
        server.handle_request()


if __name__ == '__main__':
    main()
