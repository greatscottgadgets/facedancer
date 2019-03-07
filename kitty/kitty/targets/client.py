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

from threading import Event
import time
from kitty.targets.base import BaseTarget


class ClientTarget(BaseTarget):
    '''
    This class represents a target when fuzzing a client.
    '''

    def __init__(self, name, logger=None, mutation_server_timeout=3):
        '''
        :param name: name of the target
        :param logger: logger for this object (default: None)
        :param mutation_server_timeout: timeout for receiving mutation request from the server stack
        '''
        super(ClientTarget, self).__init__(name, logger)
        self.response_sent_event = Event()
        self.mutation_server_timeout = mutation_server_timeout
        self.post_fuzz_delay = 0

    def set_mutation_server_timeout(self, mutation_server_timeout):
        '''
        Set timeout for receiving mutation request from the server stack.

        :param mutation_server_timeout: timeout for receiving mutation request from the server stack
        '''
        self.mutation_server_timeout = mutation_server_timeout

    def set_post_fuzz_delay(self, post_fuzz_delay):
        '''
        Set how long to wait before moving to the next mutation after each test.

        :param post_fuzz_delay: time to wait (in seconds)
        '''
        self.post_fuzz_delay = post_fuzz_delay

    def trigger(self):
        '''
        Trigger the target (e.g. the victim application) to start communication with the fuzzer.
        '''
        assert(self.controller)
        self._trigger()
        self.logger.debug('Waiting for mutation response. (timeout = %d)'
                          % self.mutation_server_timeout)
        res = self.response_sent_event.wait(self.mutation_server_timeout)
        if not res:
            # mark the controller's report as failed since we did not get a response from the stack
            # self.controller.report.add('failed', False) ## so it will not appear in the UI
            # self.controller.report.add('failure_reason', 'trigger timed out')
            # raise Exception('[%s] Error: trigger timed out (%d)'
            #                 % (self.name, self.mutation_server_timeout))
            self.report.error('trigger timed out')
            self.logger.error('Failure: trigger timed out')
        else:
            time.sleep(self.post_fuzz_delay)
        self.response_sent_event.clear()

    def signal_mutated(self):
        '''
        Called once a mutation was provided to the server stack.
        '''
        self.logger.debug('signal_mutated called')
        self.response_sent_event.set()

    def _trigger(self):
        self.controller.trigger()
