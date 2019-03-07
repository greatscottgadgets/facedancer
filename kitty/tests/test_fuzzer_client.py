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
import logging

from kitty.model import Template, GraphModel, String, UInt32
from kitty.fuzzers import ClientFuzzer
from kitty.interfaces.base import EmptyInterface
from mocks.mock_target import ClientTargetMock

test_logger = None


def get_test_logger():
    global test_logger
    if test_logger is None:
        logger = logging.getLogger('TestClientFuzzer')
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] -> %(message)s')
        handler = logging.FileHandler('logs/test_client_fuzzer.log', mode='w')
        handler.setFormatter(formatter)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        test_logger = logger
    return test_logger


class TestClientFuzzer(unittest.TestCase):

    def setUp(self):
        self.logger = get_test_logger()
        self.logger.debug('TESTING METHOD: %s', self._testMethodName)
        self._default_stage = 'simple_str_template'

        self.t_str = Template(name=self._default_stage, fields=[String(name='str1', value='kitty')])

        self.t_int = Template(name='simple_int_template', fields=[UInt32(name='int1', value=0x1234)])
        self.fuzzer = None
        self.mutations = {}
        self.prepare()

    def tearDown(self):
        if self.fuzzer:
            self.fuzzer.stop()

    def default_callback(self, test, stage, resp):
        if test not in self.mutations:
            self.mutations[test] = []
        self.mutations[test].append((stage, resp))

    def prepare(self):
        self.start_index = 10
        self.end_index = 20
        self.delay_duration = 0
        self.fuzzer = ClientFuzzer(name="TestServerFuzzer", logger=self.logger)

        self.interface = EmptyInterface()
        self.fuzzer.set_interface(self.interface)

        self.model = GraphModel()
        self.model.logger = self.logger

        self.model.connect(self.t_str)
        self.fuzzer.set_model(self.model)

        self.default_config = {
            'always': {
                'trigger': {
                    'fuzzer': self.fuzzer,
                    'stages': [
                        (self._default_stage, {})
                    ]
                }
            }
        }
        self.target = ClientTargetMock(self.default_config, self.default_callback, logger=self.logger)
        self.fuzzer.set_target(self.target)

        self.fuzzer.set_range(self.start_index, self.end_index)
        self.fuzzer.set_delay_between_tests(self.delay_duration)

    def testRaisesExceptionWhenStartedWithoutModel(self):

        self.fuzzer.set_model(None)
        self.assertRaises(AssertionError, self.fuzzer.start)
        self.fuzzer = None

    def testRaisesExceptionWhenStartedWithoutTarget(self):
        self.fuzzer.set_target(None)
        self.assertRaises(AssertionError, self.fuzzer.start)
        self.fuzzer = None

    def testRaisesExceptionWhenStartedWithoutInterface(self):
        self.fuzzer.set_interface(None)
        self.assertRaises(AssertionError, self.fuzzer.start)
        self.fuzzer = None

    def testVanilla(self):
        self.fuzzer.start()
        self.fuzzer.wait_until_done()
        info = self.fuzzer._get_session_info()
        # reports = self.fuzzer._get_reports_manager()
        # self.assertEqual(len(reports), 0)
        self.assertEqual(info.failure_count, 0)
        self.assertEqual(info.current_index, None)
        # self.assertEqual(info.original_start_index, 10)
        self.assertEqual(info.start_index, self.start_index)
        self.assertEqual(info.end_index, self.end_index)

    def testStartingFromStartIndex(self):
        start_index = self.model.num_mutations() - 2
        self.fuzzer.set_range(start_index)
        self.fuzzer.start()
        self.fuzzer.wait_until_done()

        info = self.fuzzer._get_session_info()
        self.assertEqual(info.current_index, None)
        self.assertEqual(info.end_index, self.model.last_index())

    def testEndingAtEndIndex(self):
        start_index = 0
        end_index = 3
        self.fuzzer.set_range(start_index, end_index)
        self.fuzzer.start()
        self.fuzzer.wait_until_done()

        info = self.fuzzer._get_session_info()
        self.assertEqual(info.start_index, 0)
        self.assertEqual(info.end_index, 3)
        self.assertEqual(info.current_index, None)

    def testFullMutationRange(self):
        self.fuzzer.set_range()
        self.fuzzer.start()
        self.fuzzer.wait_until_done()

        info = self.fuzzer._get_session_info()
        self.assertEqual(info.start_index, 0)
        self.assertEqual(info.end_index, self.model.last_index())
        self.assertEqual(info.current_index, None)

    def testTestFailedWhenReportIsFailed(self):
        config = {
            '13': {
                'report': {
                    'status': 'failed', 'reason': 'failure reason'
                }
            }
        }
        config.update(self.default_config)
        target = ClientTargetMock(config, self.default_callback, logger=self.logger)
        self.fuzzer.set_target(target)
        self.fuzzer.start()
        self.fuzzer.wait_until_done()
        info = self.fuzzer._get_session_info()
        reports = self.fuzzer.dataman.get_report_test_ids()
        self.assertEqual(sorted(reports), sorted([int(x) for x in config.keys() if x != 'always']))
        self.assertEqual(info.failure_count, len(config) - 1)

    def testAllFailedTestsHaveReports(self):
        config = {
            '10': {'report': {'status': 'failed', 'reason': 'failure reason'}},
            '11': {'report': {'status': 'failed', 'reason': 'failure reason'}},
            '12': {'report': {'status': 'failed', 'reason': 'failure reason'}},
            '13': {'report': {'status': 'failed', 'reason': 'failure reason'}}
        }
        config.update(self.default_config)
        target = ClientTargetMock(config, self.default_callback, logger=self.logger)
        self.fuzzer.set_target(target)
        self.fuzzer.start()
        self.fuzzer.wait_until_done()
        info = self.fuzzer._get_session_info()
        reports = self.fuzzer.dataman.get_report_test_ids()
        self.assertEqual(sorted(reports), sorted([int(x) for x in config.keys() if x != 'always']))
        self.assertEqual(info.failure_count, len(config) - 1)

    def testStoringAllReportsWhenStoreAllReportsIsSetToTrue(self):
        config = {}
        config.update(self.default_config)
        target = ClientTargetMock(config, self.default_callback, logger=self.logger)
        self.fuzzer.set_store_all_reports(True)
        self.fuzzer.set_target(target)
        self.fuzzer.start()
        self.fuzzer.wait_until_done()
        info = self.fuzzer._get_session_info()
        reports = self.fuzzer.dataman.get_report_test_ids()
        expected_mutation_count = self.end_index - self.start_index + 1
        expected_failure_count = 0
        self.assertEqual(len(reports), expected_mutation_count)
        self.assertEqual(info.failure_count, expected_failure_count)

    def testOnlyTestsInSetRangeAreExecuted(self):
        start_index = self.model.num_mutations() - 5
        self.model.connect(self.t_str, self.t_int)
        expected_end_index = self.model.last_index()
        self.fuzzer.set_range(start_index)
        self.fuzzer.start()
        self.fuzzer.wait_until_done()
        info = self.fuzzer._get_session_info()
        self.assertEqual(info.failure_count, 0)
        self.assertEqual(info.current_index, None)
        self.assertEqual(info.start_index, start_index)
        self.assertEqual(info.end_index, expected_end_index)

    def testGetMutationForStage(self):
        self.fuzzer.set_range(0, 1)
        config = {
            'always': {
                'trigger': {
                    'fuzzer': self.fuzzer,
                    'stages': [
                        (self._default_stage, {})
                    ]
                }
            }
        }
        target = ClientTargetMock(config, self.default_callback, logger=self.logger)
        self.fuzzer.set_target(target)
        self.fuzzer.start()
        self.fuzzer.wait_until_done()
        self.assertIn(0, self.mutations)
        self.assertEqual(self.mutations[0][0][0], self._default_stage)
        self.assertIsNotNone(self.mutations[0][0][1])

    def testGetMutationForStageTwice(self):
        self.fuzzer.set_range(0, 1)
        config = {
            'always': {
                'trigger': {
                    'fuzzer': self.fuzzer,
                    'stages': [
                        (self._default_stage, {}),
                        (self._default_stage, {})
                    ]
                }
            }
        }
        target = ClientTargetMock(config, self.default_callback, logger=self.logger)
        self.fuzzer.set_target(target)
        self.fuzzer.start()
        self.fuzzer.wait_until_done()
        self.assertIn(0, self.mutations)
        self.assertEqual(self.mutations[0][0][0], self._default_stage)
        self.assertIsNotNone(self.mutations[0][0][1])
        self.assertEqual(self.mutations[0][1][0], self._default_stage)
        self.assertIsNotNone(self.mutations[0][1][1])

    def testGetMutationWrongStage(self):
        self.fuzzer.set_range(0, 1)
        wrong_stage = 'simple_str_template1'
        config = {
            'always': {
                'trigger': {
                    'fuzzer': self.fuzzer,
                    'stages': [
                        (wrong_stage, {}),
                    ]
                }
            }
        }
        target = ClientTargetMock(config, self.default_callback, logger=self.logger)
        self.fuzzer.set_target(target)
        self.fuzzer.start()
        self.fuzzer.wait_until_done()
        self.assertIn(0, self.mutations)
        self.assertEqual(self.mutations[0][0][0], wrong_stage)
        self.assertIsNone(self.mutations[0][0][1])

    def testGetMutationWrongAfterCorrectStage(self):
        self.fuzzer.set_range(0, 1)
        wrong_stage = 'simple_str_template1'
        config = {
            'always': {
                'trigger': {
                    'fuzzer': self.fuzzer,
                    'stages': [
                        (self._default_stage, {}),
                        (wrong_stage, {}),
                    ]
                }
            }
        }
        target = ClientTargetMock(config, self.default_callback, logger=self.logger)
        self.fuzzer.set_target(target)
        self.fuzzer.start()
        self.fuzzer.wait_until_done()
        self.assertIn(0, self.mutations)
        self.assertEqual(self.mutations[0][0][0], self._default_stage)
        self.assertIsNotNone(self.mutations[0][0][1])
        self.assertEqual(self.mutations[0][1][0], wrong_stage)
        self.assertIsNone(self.mutations[0][1][1])

    def testGetMutationCorrectAfterWrongStage(self):
        self.fuzzer.set_range(0, 1)
        wrong_stage = 'simple_str_template1'
        config = {
            'always': {
                'trigger': {
                    'fuzzer': self.fuzzer,
                    'stages': [
                        (wrong_stage, {}),
                        (self._default_stage, {}),
                    ]
                }
            }
        }
        target = ClientTargetMock(config, self.default_callback, logger=self.logger)
        self.fuzzer.set_target(target)
        self.fuzzer.start()
        self.fuzzer.wait_until_done()
        self.assertIn(0, self.mutations)
        self.assertEqual(self.mutations[0][0][0], wrong_stage)
        self.assertIsNone(self.mutations[0][0][1])
        self.assertEqual(self.mutations[0][1][0], self._default_stage)
        self.assertIsNotNone(self.mutations[0][1][1])

    def testGetMutationWithWildcard(self):
        self.fuzzer.set_range(0, 1)
        config = {
            'always': {
                'trigger': {
                    'fuzzer': self.fuzzer,
                    'stages': [
                        (ClientFuzzer.STAGE_ANY, {})
                    ]
                }
            }
        }
        target = ClientTargetMock(config, self.default_callback, logger=self.logger)
        self.fuzzer.set_target(target)
        self.fuzzer.start()
        self.fuzzer.wait_until_done()
        self.assertIn(0, self.mutations)
        self.assertEqual(self.mutations[0][0][0], ClientFuzzer.STAGE_ANY)
        self.assertIsNotNone(self.mutations[0][0][1])
