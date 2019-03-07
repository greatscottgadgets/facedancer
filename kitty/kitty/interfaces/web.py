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

import json
import datetime
import time
import os
import sys

from kitty.interfaces.base import EmptyInterface
from kitty.core.threading_utils import FuncThread

if sys.version_info >= (3,):
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from urllib.parse import urlparse, parse_qs
else:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
    from urlparse import urlparse, parse_qs


class _WebInterfaceServer(HTTPServer):
    '''
    http://docs.python.org/lib/module-BaseHTTPServer.html
    '''

    def __init__(self, server_address, handler, interface):
        '''
        :param server_address: address of the server
        :param handler: handler for requests
        :param interface: reference to the interface object
        '''
        HTTPServer.__init__(self, server_address, handler)
        # kitty.interfaces... interface object
        self.interface = interface
        self.RequestHandlerClass.logger = interface.logger
        self.RequestHandlerClass.dataman = interface.dataman

    @classmethod
    def log_message(cls, dummy1, *dummy2):
        '''
        Used to silence the direct logging to stdout/stderr
        '''
        # self.logger.info(dummy1, *dummy2)
        return


class _WebInterfaceHandler(BaseHTTPRequestHandler):
    '''
    Our HTTP request handler
    '''

    def __init__(self, request, client_address, server):
        '''
        :param request: the request from the client
        :param client_address: client address
        :param server: HTTP server
        '''
        BaseHTTPRequestHandler.__init__(
            self, request, client_address, server)
        self.dataman = None

    @classmethod
    def log_message(cls, dummy1, *dummy2):
        '''
        Used to silence the direct logging to stdout/stderr
        '''
        # self.logger.info(dummy1, *dummy2)
        return

    def _pause_fuzzer(self):
        self.server.interface.pause()

    def _resume_fuzzer(self):
        self.server.interface.resume()

    def _handle_image_request(self, content_type='image/jpeg'):
        path = self.path
        filename = path.split('/')[-1]
        try:
            this_dir = os.path.dirname(os.path.realpath(__file__))
            file_path = os.path.join(this_dir, 'web', 'images', filename)
            imgf = open(file_path, 'rb')
            buff = imgf.read()
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.send_header('Content-Length', '%d' % len(buff))
            self.send_header('Cache-Control', 'public, max-age=999936000')
            self.end_headers()
            return buff
        except Exception:
            self.send_response(401)
            self.end_headers()
            return b''

    def _handle_favicon_request(self):
        return self._handle_image_request(content_type='image/x-icon')

    def do_GET(self):
        '''
        handle GET request
        '''
        self._my_handle()

    def do_POST(self):
        '''
        handle POST request
        '''
        self._my_handle()

    def _handle_text_request(self, filename=None, content_type=None):
        try:
            parsed = urlparse(self.path)
            path = parsed.path.lower()
            if filename is None:
                filename = path.split('/')[-1]
            if content_type is None:
                extension = filename.split('.')[-1]
                if extension == 'js':
                    extension = 'javascript'
                content_type = 'text/' + extension
            this_dir = os.path.dirname(os.path.realpath(__file__))
            file_path = os.path.join(this_dir, 'web', 'static', filename)
            with open(file_path, 'rb') as the_file:
                buff = the_file.read()
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.send_header('Content-Length', '%d' % len(buff))
            self.end_headers()
        except Exception:
            buff = None
        return buff

    def _handle_index(self):
        return self._handle_text_request('index.html', 'text/html')

    def _get_eta(self, info):
        end_index = info.end_index
        current_index = info.current_index
        start_index = info.start_index
        if current_index is None:
            tests_left = 0
            tests_passed = end_index - start_index
        else:
            tests_left = end_index - current_index
            tests_passed = current_index - start_index
        current_time = time.time()
        time_passed = current_time - info.start_time
        if tests_passed == 0:
            return 'unknown'
        average_test_time = time_passed / tests_passed
        eta = average_test_time * tests_left
        return str(datetime.timedelta(seconds=int(eta)))

    def _get_stats(self):
        is_paused = self.server.interface.is_paused()
        session_info = self.dataman.get_session_info()
        eta_s = self._get_eta(session_info)
        stats = session_info.as_dict()
        stats['fuzzer_name'] = self.dataman.get('fuzzer_name')
        stats['session_file_name'] = self.dataman.get('session_file_name')
        stats['log_file_name'] = self.dataman.get('log_file_name')
        report_list = self.dataman.get_report_list()
        resp_dict = {
            'paused': is_paused,
            'eta': eta_s,
            'stats': stats,
            'current_test': self.dataman.get('test_info'),
            'reports_extended': report_list,
        }
        return json.dumps(resp_dict)

    def _handle_api_request(self):
        parsed = urlparse(self.path)
        path = parsed.path.lower()[5:]

        response = None
        data_type = 'text/json'
        if path == 'stats.json':
            response = self._get_stats()
        elif path == 'template_info.json':
            response = json.dumps(self.dataman.get('template_info'))
        elif path == 'stages.json':
            response = json.dumps(self.dataman.get('stages'))
        elif path.startswith('report'):
            response = self._get_report()
        elif path == 'action/pause':
            response = ''
            self._pause_fuzzer()
        elif path == 'action/resume':
            response = ''
            self._resume_fuzzer()
        if response is not None:
            self.send_response(200)
            self.send_header('Content-type', data_type)
            self.end_headers()
        return response.encode()

    def _get_report(self):
        report = None
        encoding = 'base64'

        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if 'report_id' in query:
            try:
                report_id_string = query['report_id'][0]
                key = int(report_id_string)
                report = self.dataman.get_report_by_id(key)
                if report:
                    response = {
                        'encoding': encoding,
                        'report': report.to_dict(encoding)
                    }
                else:
                    raise 'No report with id %d' % key
            except Exception as ex:
                response = {'error': 'Failed to get report %s' % ex}
        else:
            response = {'error': 'No report_id provided'}
        return json.dumps(response)

    def _my_handle(self):

        exact_endpoints = {
            '/': self._handle_index,
            '/index.html': self._handle_index,
            '/favicon.ico': self._handle_favicon_request
        }

        endpoints = {
            '/api/': self._handle_api_request,
            '/static/': self._handle_text_request,
            '/css/': self._handle_text_request,
            '/js/': self._handle_text_request,
            '/images/': self._handle_image_request
        }
        response = None

        for endpoint in exact_endpoints:
            if self.path.lower() == endpoint:
                response = exact_endpoints[endpoint]()
                break

        if response is None:
            for endpoint in endpoints:
                if self.path.lower().startswith(endpoint):
                    response = endpoints[endpoint]()
                    break

        if response is not None:
            self.wfile.write(response)
        else:
            self.send_response(401)
            self.send_header('Content-type', 'text/html')
            self.end_headers()


class WebInterface(EmptyInterface):
    '''
    Web UI for the fuzzer
    '''

    def __init__(self, host='127.0.0.1', port=26000):
        '''
        :param host: listening address
        :param port: listening port
        '''
        super(WebInterface, self).__init__('WebInterface')
        self._host = host
        self._port = port
        self._web_thread = FuncThread(self._server_func)

    def _start(self):
        self._web_thread.start()

    def get_description(self):
        '''
        :return: description string (with listening host:port)
        '''
        return '%(description)s listening on %(host)s:%(port)s' % {
            'description': super(WebInterface, self).get_description(),
            'host': self._host,
            'port': self._port
        }

    def _server_func(self):
        server = _WebInterfaceServer((self._host, self._port), _WebInterfaceHandler, self)
        self._server = server
        server.allow_reuse_address = True
        server.serve_forever()

    def _stop(self, timeout=None):
        self._server.shutdown()
        self._server.server_close()
