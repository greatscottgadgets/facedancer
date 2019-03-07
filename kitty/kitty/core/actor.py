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
This module contains :class:`~kitty.core.actor.KittyActorInterface`
which is the base class for both monitors and controllers.
'''
import time
from kitty.core.kitty_object import KittyObject
from kitty.data.report import Report


class KittyActorInterface(KittyObject):
    '''
    Base class for monitors and controllers,
    its defines (and partially implements) the Kitty Actor API:

    - :func:`~kitty.core.actor.KittyActorInterface.setup`
    - :func:`~kitty.core.actor.KittyActorInterface.teardown`
    - :func:`~kitty.core.actor.KittyActorInterface.pre_test`
    - :func:`~kitty.core.actor.KittyActorInterface.post_test`
    - :func:`~kitty.core.actor.KittyActorInterface.is_victim_alive`
    - :func:`~kitty.core.actor.KittyActorInterface.get_report`
    '''

    def __init__(self, name, logger=None, victim_alive_check_delay=0.3):
        '''
        :param name: name of the actor
        :param logger: logger for the actor (default: None)
        :param victim_alive_check_delay: delay between checks if alive (default: 0.3)
        '''
        super(KittyActorInterface, self).__init__(name, logger)
        self.victim_alive_check_delay = victim_alive_check_delay
        self.report = None
        self.test_number = 0

    def setup(self):
        '''
        Called at the beginning of the fuzzing session.
        You should override it with the actual implementation of victim setup.
        '''
        pass

    def teardown(self):
        '''
        Called at the end of the fuzzing session.
        You should override it with the actual implementation of victim teardown.
        '''
        pass

    def pre_test(self, test_number):
        '''
        Called before a test is started. Call super if overriden.

        :param test_number: current test number
        '''
        self.test_number = test_number
        self.report = Report(self.name)
        self.report.add('start_time', time.time())
        self.report.add('test_number', self.test_number)
        self.report.add('state', 'pre_test')
        last_log = 0
        while not self.is_victim_alive():
            if time.time() - last_log >= 10:
                last_log = time.time()
                self.logger.warn('waiting for target to be alive')
            time.sleep(self.victim_alive_check_delay)
        if last_log > 0:  # only if we logged that we're waiting, should we log that we're now alive
            self.logger.warn('target is now alive')

    def post_test(self):
        '''
        Called when test is done. Call super if overriden.
        '''
        self.report.add('state', 'post_test')
        self.report.add('stop_time', time.time())

    def get_report(self):
        '''
        :rtype: :class:`~kitty.data.report.Report`
        :return: a report about the victim since last call to pre_test
        '''
        return self.report

    def is_victim_alive(self):
        '''
        Called during pre_test in loop until the target becomes alive

        :return: whether target is alive (ready for test) or not

        .. note::

            by default, it returns true,
            override if you have a way to check in your actor
        '''
        return True
