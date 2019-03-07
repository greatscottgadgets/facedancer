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
This module contains the :class:`~kitty.fuzzer.client.ClientFuzzer` class.
'''
from threading import Event
from binascii import hexlify
from kitty.fuzzers.base import BaseFuzzer
from kitty.core.threading_utils import LoopFuncThread
from kitty.data.report import Report


class ClientFuzzer(BaseFuzzer):
    '''
    ClientFuzzer is designed for fuzzing clients.
    It does not preform an active fuzzing, but rather returns a mutation of a
    response when in the right state.
    It is designed to be a module that is integrated into different stacks.

    You can see its usahe examples in the following places:

        - examples/02_client_fuzzer_browser_remote
        - examples/03_client_fuzzer_browser
    '''

    #  Wild card for matching any stage
    STAGE_ANY = '******************'

    def __init__(self, name='ClientFuzzer', logger=None, option_line=None):
        '''
        :param name: name of the object
        :param logger: logger for the object (default: None)
        :param option_line: cmd line options to the fuzzer
        '''
        super(ClientFuzzer, self).__init__(name, logger, option_line)
        self._target_control_thread = LoopFuncThread(self._do_trigger)
        self._trigger_stop_evt = Event()
        self._target_control_thread.set_func_stop_event(self._trigger_stop_evt)
        self._index_in_path = 0
        self._requested_stages = []
        self._report = None
        self._done_evt = Event()

    def _pre_test(self):
        self._requested_stages = []
        self._report = Report(self.get_name())
        super(ClientFuzzer, self)._pre_test()

    def is_done(self):
        '''
        check if fuzzer is done fuzzing

        :return: True if done
        '''
        return self._done_evt.is_set()

    def wait_until_done(self):
        '''
        wait until fuzzer is done
        '''
        self._done_evt.wait()

    def stop(self):
        '''
        Stop the fuzzing session
        '''
        self.logger.info('Stopping client fuzzer')
        self._target_control_thread.stop()
        self.target.signal_mutated()
        super(ClientFuzzer, self).stop()

    def _do_trigger(self):
        self.logger.debug('_do_trigger called')
        self._check_pause()
        if self._next_mutation():
            self._fuzz_path = self.model.get_sequence()
            self._index_in_path = 0
            self._pre_test()
            self._test_info()
            self.target.trigger()
            self._post_test()
        else:
            self._end_message()
            self._done_evt.set()
            self._trigger_stop_evt.wait()

    def _start(self):
        self._target_control_thread.start()

    def _test_environment(self):
        '''
        .. todo:: can we do that here somehow?
        '''
        pass

    def _should_fuzz_node(self, fuzz_node, stage):
        '''
        The matching stage is either the name of the last node, or ClientFuzzer.STAGE_ANY.

        :return: True if we are in the correct model node
        '''
        if stage == ClientFuzzer.STAGE_ANY:
            return True
        if fuzz_node.name.lower() == stage.lower():
            if self._index_in_path == len(self._fuzz_path) - 1:
                return True
        else:
            return False

    def _update_path_index(self, stage):
        last_index_in_path = len(self._fuzz_path) - 1
        if self._index_in_path < last_index_in_path:
            node = self._fuzz_path[self._index_in_path].dst
            if node.name.lower() == stage.lower():
                self._index_in_path += 1

    def get_mutation(self, stage, data):
        '''
        Get the next mutation, if in the correct stage

        :param stage: current stage of the stack
        :param data: a dictionary of items to pass to the model
        :return: mutated payload if in apropriate stage, None otherwise
        '''
        payload = None
        # Commented out for now: we want to return the same
        # payload - while inside the same test
        # if self._keep_running() and self._do_fuzz.is_set():
        if self._keep_running():
            fuzz_node = self._fuzz_path[self._index_in_path].dst
            if self._should_fuzz_node(fuzz_node, stage):
                fuzz_node.set_session_data(data)
                payload = fuzz_node.render().tobytes()
                self._last_payload = payload
            else:
                self._update_path_index(stage)
        if payload:
            self._notify_mutated()
        self._requested_stages.append((stage, payload))
        return payload

    def _notify_mutated(self):
        self.target.signal_mutated()

    def _get_report(self):
        base_report = super(ClientFuzzer, self)._get_report()
        if self._requested_stages:
            stages, payloads = zip(*self._requested_stages)
        else:
            stages = []
            payloads = []
        self._report.add('stages', stages)
        self._report.add('payloads', [None if payload is None else hexlify(payload) for payload in payloads])
        base_report.add('fuzzer', self._report)
        return base_report
