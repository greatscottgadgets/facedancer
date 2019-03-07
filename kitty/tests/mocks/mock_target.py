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

from .mock_config import Config
from .mock_instruments import MockInstrumentation
from kitty.targets.server import ServerTarget
from kitty.targets.client import ClientTarget
from kitty.data.report import Report


class ServerTargetMock(ServerTarget):

    def __init__(self, config=None, logger=None):
        super(ServerTargetMock, self).__init__('MockTarget', logger=logger)
        self.config = Config('target', config)
        self.instrument = MockInstrumentation()

    def _restart(self):
        pass

    def _send_to_target(self, data):
        self.instrument.count_increment('_send_to_target')
        self.config.set_func('send')
        if self.config.get_val('raise exception') is True:
            raise Exception('Mock exception from send')

    def _receive_from_target(self):
        self.instrument.count_increment('_receive_from_target')
        res = ''
        self.config.set_func('receive')
        if self.config.get_val('raise exception') is True:
            raise Exception('Mock exception from receive')
        if self.config.get_val('response') != self.config.INVALID:
            res = self.config.get_val('response')
        return res

    def get_report(self):
        self.instrument.count_increment('get_report')
        self.config.set_func('report')
        report = self.report
        config_report = self.config.get_vals()
        if config_report:
            self.logger.debug('found matching config: %s', repr(config_report))
            for k, v in config_report.items():
                if k.lower() == 'status':
                    report.set_status(v)
                else:
                    report.add(k, v)
        return report

    def setup(self):
        self.instrument.count_increment('setup')
        self.config.set_func('setup')

    def teardown(self):
        self.instrument.count_increment('teardown')
        self.config.set_func('teardown')

    def pre_test(self, test_num):
        self.instrument.count_increment('pre_test')
        self.instrument.list_add('pre_test', test_num)
        self.config.set_func('pre_test')
        self.config.set_test(test_num)
        self.test_number = test_num
        self.report = Report(self.name)

    def post_test(self, test_num):
        self.instrument.count_increment('post_test')
        self.instrument.list_add('post_test', test_num)
        self.config.set_func('post_test')

    def failure_detected(self):
        self.config.set_func('failure_detected')
        return False


class ClientTargetMock(ClientTarget):

    def __init__(self, config, response_callback, logger=None):
        super(ClientTargetMock, self).__init__('MockTarget', logger=logger)
        self.config = Config('target', config)
        self.instrument = MockInstrumentation()
        self.response_callback = response_callback

    def _restart(self):
        pass

    def get_report(self):
        self.instrument.count_increment('get_report')
        self.config.set_func('report')
        report = self.report
        config_report = self.config.get_vals()
        if config_report:
            self.logger.debug('found matching config: %s', repr(config_report))
            for k, v in config_report.items():
                if k.lower() == 'status':
                    report.set_status(v)
                else:
                    report.add(k, v)
        return report

    def setup(self):
        self.instrument.count_increment('setup')
        self.config.set_func('setup')

    def teardown(self):
        self.instrument.count_increment('teardown')
        self.config.set_func('teardown')

    def pre_test(self, test_num):
        self.instrument.count_increment('pre_test')
        self.instrument.list_add('pre_test', test_num)
        self.config.set_func('pre_test')
        self.config.set_test(test_num)
        self.test_number = test_num
        self.report = Report(self.name)

    def post_test(self, test_num):
        self.instrument.count_increment('post_test')
        self.instrument.list_add('post_test', test_num)
        self.config.set_func('post_test')

    def failure_detected(self):
        self.config.set_func('failure_detected')
        return False

    def trigger(self):
        self.instrument.count_increment('trigger')
        self.config.set_func('trigger')
        fuzzer = self.config.get_val('fuzzer')
        stages = self.config.get_val('stages')
        for (stage, data) in stages:
            resp = fuzzer.get_mutation(stage=stage, data=data)
            self.response_callback(self.test_number, stage, resp)

    def signal_mutated(self):
        self.instrument.count_increment('signal_mutated')
        pass
