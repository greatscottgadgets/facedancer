# Copyright (C) 2016 Cisco Systems, Inc. and/or its affiliates. All rights reserved.
#
# This example was authored and contributed by dark-lbp <jtrkid@gmail.com>
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
from binascii import hexlify
from katnip.targets.tcp import TcpTarget
from kitty.model import GraphModel, Template
from kitty.interfaces import WebInterface
from kitty.fuzzers import ServerFuzzer
from kitty.model.low_level.aliases import *
from kitty.model.low_level.field import *
from server_controller import SessionServerController

target_ip = '127.0.0.1'
target_port = 9999
web_port = 26001


get_session = Template(name='get_session', fields=[
    UInt8(value=1, name='op_code', fuzzable=False),
    UInt16(value=0, name='session_id', fuzzable=False)
])

send_data = Template(name='send_data', fields=[
    UInt8(value=2, name='op_code', fuzzable=False),
    Dynamic(key='session_id', default_value='\x00\x00'),
    String(name='data', value='some data')
])


def new_session_callback(fuzzer, edge, resp):
    '''
    :param fuzzer: the fuzzer object
    :param edge: the edge in the graph we currently at.
                 edge.src is the get_session template
                 edge.dst is the send_data template
    :param resp: the response from the target
    '''
    fuzzer.logger.info('session is: %s' % hexlify(resp[1:3]).decode())
    fuzzer.target.session_data['session_id'] = resp[1:3]


# Define session target
target = TcpTarget(
    name='session_test_target', host=target_ip, port=target_port, timeout=2)
# Make target expect response
target.set_expect_response(True)


# Define controller
controller = SessionServerController(name='ServerController', host=target_ip, port=target_port)
target.set_controller(controller)

# Define model
model = GraphModel()
model.connect(get_session)
model.connect(get_session, send_data, new_session_callback)

# Define fuzzer
fuzzer = ServerFuzzer()
fuzzer.set_interface(WebInterface(port=web_port))
fuzzer.set_model(model)
fuzzer.set_target(target)
fuzzer.set_delay_between_tests(0.2)
fuzzer.start()
