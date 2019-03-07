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
Tests for the target classes
'''
import logging
from kitty.targets import BaseTarget, ServerTarget, ClientTarget
from kitty.core.actor import KittyActorInterface
from mocks.mock_config import Config
from common import BaseTestCase


test_logger = None


def get_test_logger():
    global test_logger
    if test_logger is None:
        logger = logging.getLogger('TestClientFuzzer')
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] -> %(message)s')
        handler = logging.FileHandler('logs/test_target.log', mode='w')
        handler.setFormatter(formatter)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        test_logger = logger
    return test_logger


def count_calls(fn_name):
    def decorator(func):
        def wrap(self, *args, **kwargs):
            if fn_name not in self.call_count:
                self.call_count[fn_name] = 0
            self.call_count[fn_name] += 1
            return func(self, *args, **kwargs)
        return wrap
    return decorator


class TestActor(KittyActorInterface):

    def __init__(self, name, logger=None, victim_alive_check_delay=0.3, config=None):
        super(TestActor, self).__init__(name, logger, victim_alive_check_delay)
        self.call_count = {}
        if config is None:
            config = {}
        self.config = Config(name, config)

    def get_call_count(self, func):
        if func in self.call_count:
            return self.call_count[func]
        return 0

    @count_calls('setup')
    def setup(self):
        super(TestActor, self).setup()

    @count_calls('teardown')
    def teardown(self):
        super(TestActor, self).teardown()

    @count_calls('pre_test')
    def pre_test(self, test_number):
        self.config.set_test(test_number)
        super(TestActor, self).pre_test(test_number)

    @count_calls('post_test')
    def post_test(self):
        super(TestActor, self).post_test()

    @count_calls('get_report')
    def get_report(self):
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

    @count_calls('is_victim_alive')
    def is_victim_alive(self):
        return super(TestActor, self).is_victim_alive()

    @count_calls('trigger')
    def trigger(self):
        pass


class BaseTargetTests(BaseTestCase):

    def setUp(self, cls=BaseTarget):
        super(BaseTargetTests, self).setUp(cls)
        self.uut = self.get_uut()
        self.controller = TestActor('controller', logger=self.logger)
        self.monitor1 = TestActor('Monitor1', logger=self.logger)
        self.monitor2 = TestActor('Monitor2', logger=self.logger)

    def get_uut(self):
        return self.cls(name='uut', logger=self.logger)

    def add_actors(self):
        self.uut.set_controller(self.controller)
        self.uut.add_monitor(self.monitor1)
        self.uut.add_monitor(self.monitor2)

    def check_calls(self, func, count):
        self.assertEqual(self.controller.get_call_count(func), 1)
        self.assertEqual(self.monitor1.get_call_count(func), 1)
        self.assertEqual(self.monitor2.get_call_count(func), 1)

    def testCallSetupOfEnclosedActors(self):
        '''
        target.setup() ==> target.[controller, monitors].setup()
        '''
        self.add_actors()
        self.uut.setup()
        self.check_calls('setup', 1)

    def testCallTeardownOfEnclosedActors(self):
        self.add_actors()
        self.uut.setup()
        self.uut.teardown()
        self.check_calls('teardown', 1)

    def testCallPreTestOfEnclosedActors(self):
        self.add_actors()
        self.uut.setup()
        self.uut.pre_test(1)
        self.check_calls('pre_test', 1)

    def testCallPostTestOfEnclosedActors(self):
        self.add_actors()
        self.uut.setup()
        self.uut.pre_test(1)
        self.uut.post_test(1)
        self.check_calls('post_test', 1)

    def testCallGetReportOfEnclosedActors(self):
        self.add_actors()
        self.uut.setup()
        self.uut.pre_test(1)
        self.uut.post_test(1)
        self.uut.get_report()
        self.check_calls('get_report', 1)

    def testReportFailedIfMonitor1Failed(self):
        conf = {'1': {'report': {'status': 'failed', 'reason': 'failure reason'}}}
        self.monitor1 = TestActor('Monitor1', logger=self.logger, config=conf)
        self.add_actors()
        self.uut.setup()
        self.uut.pre_test(1)
        self.uut.post_test(1)
        report = self.uut.get_report()
        self.check_calls('get_report', 1)
        self.assertEqual(report.get_status(), report.FAILED)

    def testReportErroIfMonitor1Error(self):
        conf = {'1': {'report': {'status': 'error', 'reason': 'error reason'}}}
        self.monitor1 = TestActor('Monitor1', logger=self.logger, config=conf)
        self.add_actors()
        self.uut.setup()
        self.uut.pre_test(1)
        self.uut.post_test(1)
        report = self.uut.get_report()
        self.check_calls('get_report', 1)
        self.assertEqual(report.get_status(), report.ERROR)

    def testReportFailedIfMonitor2Failed(self):
        conf = {'1': {'report': {'status': 'failed', 'reason': 'failure reason'}}}
        self.monitor2 = TestActor('Monitor2', logger=self.logger, config=conf)
        self.add_actors()
        self.uut.setup()
        self.uut.pre_test(1)
        self.uut.post_test(1)
        report = self.uut.get_report()
        self.check_calls('get_report', 1)
        self.assertEqual(report.get_status(), report.FAILED)

    def testReportErroIfMonitor2Error(self):
        conf = {'1': {'report': {'status': 'error', 'reason': 'error reason'}}}
        self.monitor2 = TestActor('Monitor2', logger=self.logger, config=conf)
        self.add_actors()
        self.uut.setup()
        self.uut.pre_test(1)
        self.uut.post_test(1)
        report = self.uut.get_report()
        self.check_calls('get_report', 1)
        self.assertEqual(report.get_status(), report.ERROR)

    def testReportFailedIfControllerFailed(self):
        conf = {'1': {'report': {'status': 'failed', 'reason': 'failure reason'}}}
        self.controller = TestActor('Controller', logger=self.logger, config=conf)
        self.add_actors()
        self.uut.setup()
        self.uut.pre_test(1)
        self.uut.post_test(1)
        report = self.uut.get_report()
        self.check_calls('get_report', 1)
        self.assertEqual(report.get_status(), report.FAILED)

    def testReportErroIfControllerError(self):
        conf = {'1': {'report': {'status': 'error', 'reason': 'error reason'}}}
        self.controller = TestActor('Controller', logger=self.logger, config=conf)
        self.add_actors()
        self.uut.setup()
        self.uut.pre_test(1)
        self.uut.post_test(1)
        report = self.uut.get_report()
        self.check_calls('get_report', 1)
        self.assertEqual(report.get_status(), report.ERROR)


class ServerTargetTest(BaseTargetTests):

    def setUp(self):
        super(ServerTargetTest, self).setUp(ServerTarget)


class ClientTargetTest(BaseTargetTests):

    def setUp(self):
        super(ClientTargetTest, self).setUp(ClientTarget)

    def get_uut(self):
        return self.cls(name='uut', logger=self.logger, mutation_server_timeout=0)

    def testCallTriggerOfEnclosedActors(self):
        self.add_actors()
        self.uut.setup()
        self.uut.pre_test(1)
        self.uut.trigger()
        self.assertEqual(self.controller.get_call_count('trigger'), 1)
        self.assertEqual(self.monitor1.get_call_count('trigger'), 0)
        self.assertEqual(self.monitor2.get_call_count('trigger'), 0)
