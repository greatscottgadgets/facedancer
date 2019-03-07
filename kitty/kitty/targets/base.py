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
This module defines BaseTarget - the basic target
'''

from kitty.core.kitty_object import KittyObject
from kitty.data.report import Report


class BaseTarget(KittyObject):
    '''
    BaseTarget contains the common logic and behaviour of all target.
    '''

    def __init__(self, name='BaseTarget', logger=None):
        super(BaseTarget, self).__init__(name, logger)
        self.controller = None
        self.monitors = []
        self.report = Report(name)
        self.test_number = None
        self.fuzzer = None
        self.session_data = {}

    def set_fuzzer(self, fuzzer):
        self.fuzzer = fuzzer

    def set_controller(self, controller):
        '''
        Set a controller
        '''
        self.controller = controller

    def add_monitor(self, monitor):
        '''
        Add a monitor
        '''
        self.monitors.append(monitor)

    def setup(self):
        '''
        Make sure the target is ready for fuzzing, including monitors and
        controllers
        '''
        if self.controller:
            self.controller.setup()
        for monitor in self.monitors:
            monitor.setup()

    def teardown(self):
        '''
        Clean up the target once all tests are completed
        '''
        if self.controller:
            self.controller.teardown()
        for monitor in self.monitors:
            monitor.teardown()

    def pre_test(self, test_num):
        '''
        Called when a test is started
        '''
        self.test_number = test_num
        self.report = Report(self.name)
        if self.controller:
            self.controller.pre_test(test_number=self.test_number)
        for monitor in self.monitors:
            monitor.pre_test(test_number=self.test_number)
        self.report.add('test_number', test_num)
        self.report.add('state', 'STARTED')

    def post_test(self, test_num):
        '''
        Called when test is completed, a report should be prepared now
        '''
        if self.controller:
            self.controller.post_test()
        for monitor in self.monitors:
            monitor.post_test()
        self.report.add('state', 'COMPLETED')
        if self.controller:
            controller_report = self.controller.get_report()
            self.report.add('controller', controller_report)
        for monitor in self.monitors:
            current_report = monitor.get_report()
            self.report.add(current_report.get('name'), current_report)
        status = self.report.get_status()
        reason = self.report.get('reason')
        if status != Report.PASSED:
            self.logger.warning('Test %d status: %s' % (test_num, status))
            self.logger.warning('Reason: %s' % (reason))

    def get_report(self):
        return self.report

    def get_session_data(self):
        '''
        Session related data dictionary to be used by data model.

        :return: dictionary (str, bytes)
        '''
        return self.session_data
