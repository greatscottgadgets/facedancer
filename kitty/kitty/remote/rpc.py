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
RPC implementation, based on jsonrpc
https://json-rpc.readthedocs.io/
'''
import requests
import json
import six
import traceback
from six.moves.BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
if six.PY3:
    import codecs


JSONRPC_NO_RESULT_STR = u'No result from JSON-RPC method.'

JSONRPC_PARSE_ERROR = -32700
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INTERNAL_ERROR = -32603
JSONRPC_NO_RESULT = -32000


def encode_string(data, encoding='hex'):
    '''
    Encode string

    :param data: string to encode
    :param encoding: encoding to use (default: 'hex')
    :return: encoded string
    '''
    if six.PY2:
        return data.encode(encoding)
    else:
        if isinstance(data, str):
            data = bytes(data, 'utf-8')
        return codecs.encode(data, encoding).decode('ascii')


def decode_string(data, encoding='hex'):
    '''
    Decode string

    :param data: string to decode
    :param encoding: encoding to use (default: 'hex')
    :return: decoded string
    '''
    if six.PY2:
        return data.decode(encoding)
    else:
        return codecs.decode(data.encode('ascii'), encoding)


def encode_data(data):
    '''
    Encode data - list, dict, string, bool or int (and nested)

    :param data: data to encode
    :return: encoded object of the same type
    '''
    if isinstance(data, (six.string_types, bytes)):
        return encode_string(data)
    elif isinstance(data, (six.integer_types, bool, float)):
        return data
    elif data is None:
        return data
    elif isinstance(data, list):
        return [encode_data(x) for x in data]
    elif isinstance(data, dict):
        return {k: encode_data(v) for k, v in data.items()}
    else:
        raise ValueError('Cannot encode data of type %s' % type(data))


def decode_data(data):
    '''
    Decode data - list, dict, string, bool or int (and nested)

    :param data: data to decode
    :return: decoded object of the same type
    '''
    if isinstance(data, (six.string_types, bytes)):
        return decode_string(data)
    elif isinstance(data, (six.integer_types, bool, float)):
        return data
    elif data is None:
        return data
    elif isinstance(data, list):
        return [decode_data(x) for x in data]
    elif isinstance(data, dict):
        return {k: decode_data(v) for k, v in data.items()}
    else:
        raise ValueError('Cannot decode data of type %s' % type(data))


class RpcClient(object):

    def __init__(self, host, port):
        '''
        :param url: URL of the RPC server
        '''
        self.cache = {}
        self.url = 'http://%s:%d' % (host, port)
        self.headers = {'content-type': 'application/json'}
        self.uid = 0

    def __getattr__(self, key):
        '''
        Return a function with that name, which performs json rpc request

        :param key: name of the function
        :return: function with that name
        '''
        if key in self.cache:
            func = self.cache[key]
        else:
            func = self._generate_rpc_method(key)
            self.cache[key] = func
        return func

    def get_unique_msg_id(self):
        '''
        :return: a unique message id
        '''
        uid = self.uid
        self.uid += 1
        return uid

    def _generate_rpc_method(self, method):
        '''
        Generate a function that performs rpc call

        :param method: method name
        :return: rpc function
        '''
        def _(**kwargs):
            '''
            always use named arguments
            '''
            msg_id = self.get_unique_msg_id()
            params = encode_data(kwargs)
            payload = {
                'method': method,
                'params': params,
                'jsonrpc': '2.0',
                'id': msg_id
            }
            response = requests.post(self.url, data=json.dumps(payload), headers=self.headers).json()
            if ('error' in response):
                if response['error']['code'] == JSONRPC_NO_RESULT:
                    return None
                raise Exception('Got error from RPC server when called "%s" error: %s' % (method, response['error']))
            if 'result' in response:
                result = decode_data(response['result'])
                return result
        return _

    def stop_remote_server(self):
        '''
        Stop the remote server (after responding to this message)
        '''
        self._meta_stop_server()


class RpcHttpServer(HTTPServer):

    def __init__(self, server_address, handler, impl, meta):
        '''
        :param server_address: address of the server
        :param handler: handler for requests
        :param impl: reference to the implementation object
        '''
        HTTPServer.__init__(self, server_address, handler)
        self.impl = impl
        self.meta = meta

    def log_message(self, fmt, *args):
        '''
        Override default log and do nothing
        '''
        return


class RpcHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        '''
        Override default log and do nothing
        '''
        return

    def _parse_request(self):
        '''
        Parse the request
        '''
        self.req_method = 'unknown'
        self.req_params = {}
        self.req_rpc_version = '2.0'
        self.req_id = 0
        self.data = self.rfile.read(int(self.headers.get('content-length')))
        data_dict = json.loads(self.data)
        self.req_method = data_dict['method']
        self.req_params = decode_data(data_dict['params'])
        self.req_rpc_version = data_dict['jsonrpc']
        self.req_id = data_dict['id']

    def do_POST(self):
        '''
        Handle POST requests
        '''
        try:
            self._parse_request()
        except Exception as ex1:
            print(traceback.format_exc())
            self.error_response(JSONRPC_PARSE_ERROR, 'exception when parsing jsonrpc request [%s]' % (ex1))
            return
        try:
            if self.req_method.startswith('_meta_'):
                self.req_method = self.req_method.replace('_meta_', '')
                instance = self.server.meta
            else:
                instance = self.server.impl
            method = getattr(instance, self.req_method)
        except AttributeError:
            self.error_response(JSONRPC_METHOD_NOT_FOUND, 'no method named "%s"' % self.req_method)
            return
        try:
            res = method(**self.req_params)
        except Exception as ex1:
            self.error_response(JSONRPC_INTERNAL_ERROR, 'exception in call "%s(%s)" -> %s' % (self.req_method, self.req_params, ex1))
            return
        if res is None:
            self.error_response(JSONRPC_NO_RESULT, JSONRPC_NO_RESULT_STR)
        else:
            self.valid_response(res)

    def error_response(self, code, msg):
        '''
        Send an error response

        :param code: error code
        :param msg: error message
        '''
        self.send_result({
            'error': {
                'code': code,
                'message': msg
            }
        })

    def valid_response(self, result):
        '''
        Send a valid response with the result

        :param result: the result of the call
        '''
        self.send_result({
            'result': encode_data(result)
        })

    def send_result(self, additional_dict):
        '''
        Send a result to the RPC client

        :param additional_dict: the dictionary with the response
        '''
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        response = {
            'jsonrpc': self.req_rpc_version,
            'id': self.req_id,
        }
        response.update(additional_dict)
        jresponse = json.dumps(response)
        self.send_header("Content-length", len(jresponse))
        self.end_headers()
        self.wfile.write(jresponse.encode())


class RpcServer(object):

    _STATE_IDLE = 1
    _STATE_RUN = 2
    _STATE_SHOULD_STOP = 3

    def __init__(self, host, port, impl):
        '''
        :param host: listening address
        :param port: listening port
        :param impl: implementation class
        '''
        self.host = host
        self.port = port
        self.server = RpcHttpServer((host, port), RpcHandler, impl, self)
        self.impl = impl
        self.running = True
        self.state = RpcServer._STATE_IDLE

    def start(self):
        '''
        Serving loop
        '''
        print('Waiting for a client to connect to url http://%s:%d/' % (self.host, self.port))
        self.state = RpcServer._STATE_RUN
        while self.state == RpcServer._STATE_RUN:
            self.server.handle_request()
        self.server.server_close()
        self.state = RpcServer._STATE_IDLE

    def stop_server(self):
        '''
        Mark the server state to be stopped.
        No further action needed when called from remote RPC client (stop_remote_server),
        but requires another request if called directly
        '''
        self.state = RpcServer._STATE_SHOULD_STOP

    def is_running(self):
        '''
        Check if the server is currently running

        :return: whether the server is currently running
        '''
        return self.state != RpcServer._STATE_IDLE
