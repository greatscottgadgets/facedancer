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
import unittest
from threading import Thread
import time
from common import get_test_logger
from kitty.remote.rpc import RpcClient, RpcServer


class RemoteServerImpl(object):

    def __init__(self, testcase):
        self.testcase = testcase

    def func_without_args(self):
        self.testcase.mark_called('func_without_args')
        return 1

    def func_with_args(self, **kwargs):
        self.testcase.mark_called('func_with_args', **kwargs)
        return 1

    def func_with_no_retval(self):
        self.testcase.mark_called('func_with_no_retval')

    def raises_exception(self):
        self.testcase.mark_called('raises_exception')
        raise Exception('Boom')


class RpcServerTestCase(unittest.TestCase):

    def setUp(self):
        self.logger = get_test_logger()
        self.our_class = RemoteServerImpl(self)
        self.host = '127.0.0.1'
        self.port = 7001
        self.rpc_server = RpcServer(self.host, self.port, self.our_class)
        self.rpc_server_th = Thread(target=self.rpc_server.start)
        self.rpc_client = RpcClient(self.host, self.port)
        self.called_functions = []

    def mark_called(self, func_name, **kwargs):
        self.called_functions.append((func_name, kwargs))

    def tearDown(self):
        if self.rpc_server.is_running():
            self.rpc_client.stop_remote_server()

    def start_server(self):
        self.rpc_server_th.start()
        time.sleep(0.001)

    def stop_server(self):
        self.rpc_client.stop_remote_server()
        time.sleep(0.001)

    def testStartStopServer(self):
        self.start_server()
        self.assertTrue(self.rpc_server.is_running())
        self.stop_server()
        self.assertFalse(self.rpc_server.is_running())

    def testCallFuncNoArgs(self):
        self.start_server()
        retval = self.rpc_client.func_without_args()
        self.assertEqual(retval, 1)
        self.stop_server()
        self.assertEqual(self.called_functions, [('func_without_args', {})])

    def testCallFuncWithArgs(self):
        self.start_server()
        retval = self.rpc_client.func_with_args(arg1=1, arg2=2)
        self.assertEqual(retval, 1)
        self.stop_server()
        self.assertEqual(self.called_functions, [('func_with_args', {u'arg1': 1, u'arg2': 2})])

    def testCallMultipleTimes(self):
        self.start_server()
        retval = self.rpc_client.func_with_args(arg1=1, arg2=2)
        self.assertEqual(retval, 1)
        retval = self.rpc_client.func_with_args(arg1=11, arg2=22)
        self.assertEqual(retval, 1)
        retval = self.rpc_client.func_with_args(arg1=111, arg2=222)
        self.assertEqual(retval, 1)
        retval = self.rpc_client.func_with_args(arg1=1111, arg2=2222)
        self.assertEqual(retval, 1)
        self.stop_server()
        self.assertEqual(self.called_functions, [
            ('func_with_args', {u'arg1': 1, u'arg2': 2}),
            ('func_with_args', {u'arg1': 11, u'arg2': 22}),
            ('func_with_args', {u'arg1': 111, u'arg2': 222}),
            ('func_with_args', {u'arg1': 1111, u'arg2': 2222}),
        ])

    def testCallWithString(self):
        self.start_server()
        retval = self.rpc_client.func_with_args(arg1='hello', arg2='world')
        self.assertEqual(retval, 1)
        self.stop_server()
        self.assertEqual(self.called_functions, [('func_with_args', {u'arg1': b'hello', u'arg2': b'world'})])

    def testCallWithDict(self):
        arg = {'k1': b'hello', 'k2': 1}
        self.start_server()
        retval = self.rpc_client.func_with_args(arg=arg)
        self.assertEqual(retval, 1)
        self.stop_server()
        self.assertEqual(self.called_functions, [('func_with_args', {u'arg': arg})])

    def testCallWithArr(self):
        arg = [b'a string', 123]
        self.start_server()
        retval = self.rpc_client.func_with_args(arg=arg)
        self.assertEqual(retval, 1)
        self.stop_server()
        self.assertEqual(self.called_functions, [('func_with_args', {u'arg': arg})])

    def testCallWithNone(self):
        arg = None
        self.start_server()
        retval = self.rpc_client.func_with_args(arg=arg)
        self.assertEqual(retval, 1)
        self.stop_server()
        self.assertEqual(self.called_functions, [('func_with_args', {u'arg': arg})])

    def testCallNoRetVal(self):
        self.start_server()
        retval = self.rpc_client.func_with_no_retval()
        self.assertIsNone(retval)
        self.stop_server()
        self.assertEqual(self.called_functions, [('func_with_no_retval', {})])

    def testExceptionRaised(self):
        self.start_server()
        with self.assertRaises(Exception):
            self.rpc_client.raises_exception()
        self.stop_server()
        self.assertEqual(self.called_functions, [('raises_exception', {})])

    def testCallFunctionAfterException(self):
        self.start_server()
        with self.assertRaises(Exception):
            self.rpc_client.raises_exception()
        retval = self.rpc_client.func_with_args(arg1=1, arg2=2)
        self.assertEqual(retval, 1)
        self.stop_server()
        self.assertEqual(self.called_functions, [
            ('raises_exception', {}),
            ('func_with_args', {u'arg1': 1, u'arg2': 2}),
        ])
