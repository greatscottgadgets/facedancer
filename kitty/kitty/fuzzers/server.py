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

import traceback
from kitty.fuzzers.base import BaseFuzzer


class ServerFuzzer(BaseFuzzer):
    '''
    ServerFuzzer is a class that is designed to fuzz servers.
    It does not create the mutations, as those are created by the Session object.
    The idea is to go through every path in the model, execute all requsets in
    the path, and mutating the last request.
    '''

    def __init__(self, name='ServerFuzzer', logger=None, option_line=None):
        '''
        :param name: name of the object
        :param logger: logger for the object (default: None)
        :param option_line: cmd line options to the fuzzer
        '''
        super(ServerFuzzer, self).__init__(name, logger, option_line)

    def _start(self):
        self.logger.info('should keep running? %s' % self._keep_running())
        while self._next_mutation():
            sequence = self.model.get_sequence()
            try:
                self._run_sequence(sequence)
            except Exception as e:
                self.logger.error('Error occurred while fuzzing: %s', repr(e))
                self.logger.error(traceback.format_exc())
                break
        self._end_message()

    def _test_environment(self):
        sequence = self.model.get_sequence()
        try:
            if self._run_sequence(sequence):
                raise Exception('Environment test failed')
        except:
            self.logger.info('Environment test failed')
            raise

    def _run_sequence(self, sequence):
        '''
        Run a single sequence
        '''
        self._check_pause()
        self._pre_test()
        session_data = self.target.get_session_data()
        self._test_info()
        resp = None
        for edge in sequence:
            if edge.callback:
                edge.callback(self, edge, resp)
            session_data = self.target.get_session_data()
            node = edge.dst
            node.set_session_data(session_data)
            resp = self._transmit(node)
        return self._post_test()

    def _transmit(self, node):
        '''
        Transmit node data to target.

        :type node:  Template
        :param node: node to transmit
        :return: response if there is any
        '''
        payload = node.render().tobytes()
        self._last_payload = payload
        try:
            return self.target.transmit(payload)
        except Exception as e:
            self.logger.error('Error in transmit: %s', e)
            raise
