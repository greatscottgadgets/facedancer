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

import BaseHTTPServer
from kitty.remote import RpcClient


class MyHttpServer(BaseHTTPServer.HTTPServer):
    '''
    http://docs.python.org/lib/module-BaseHTTPServer.html
    '''

    def __init__(self, server_address, handler, fuzzer):
        BaseHTTPServer.HTTPServer.__init__(self, server_address, handler)
        self.fuzzer = fuzzer


class MyHttpHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, request, client_address, server)

    def do_GET(self):
        resp = None
        if self.path == '/fuzzed':
            resp = self.server.fuzzer.get_mutation(stage="GET fuzzed", data={})
        if resp is None:
            resp = self.default_response()
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
        print('response:')
        print(resp)
        print('<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
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
    #
    # The fuzzer process waits on port 26007
    #
    agent = RpcClient(host='localhost', port=26007)

    #
    # tell the fuzzer to start fuzzing (it will trigger connections to the http server)
    #
    agent.start()

    server = MyHttpServer(('localhost', 8082), MyHttpHandler, agent)
    while True:
        server.handle_request()


if __name__ == '__main__':
    main()
