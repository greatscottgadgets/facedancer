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
This module defines BaseMonitor - the base (abstract) monitor class
'''

from kitty.core.actor import KittyActorInterface
from kitty.core.threading_utils import LoopFuncThread


class BaseMonitor(KittyActorInterface):
    '''
    Base (abstract) monitor class
    '''

    def __init__(self, name, logger=None, victim_alive_check_delay=0.3):
        '''
        :param name: name of the actor
        :param logger: logger for the actor (default: None)
        :param victim_alive_check_delay: delay between checks if alive (default: 0.3)
        '''
        super(BaseMonitor, self).__init__(name, logger, victim_alive_check_delay)
        self.monitor_thread = None

    def setup(self):
        '''
        Make sure the monitor is ready for fuzzing
        '''
        super(BaseMonitor, self).setup()
        self.monitor_thread = LoopFuncThread(self._monitor_func)
        self.monitor_thread.start()

    def teardown(self):
        '''
        cleanup the monitor data and
        '''
        self.monitor_thread.stop()
        self.monitor_thread = None
        super(BaseMonitor, self).teardown()

    def pre_test(self, test_number):
        '''
        Called when a test is started

        :param test_number: current test number
        '''
        if not self._is_alive():
            self.setup()
        super(BaseMonitor, self).pre_test(test_number)

    def _is_alive(self):
        '''
        Check if the monitor is alive
        '''
        if self.monitor_thread is not None:
            if self.monitor_thread.is_alive():
                return True
        return False

    def _monitor_func(self):
        '''
        Called in a loop in a separate thread (self.monitor_thread).
        '''
        self.not_implemented('_monitor_func')
