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
Tests for the report class
'''

import unittest
from common import get_test_logger
from kitty.data.report import Report


class ReportTests(unittest.TestCase):

    def setUp(self):
        self.logger = get_test_logger()
        self.report_name = 'uut'
        self.failure_reason = 'failure reason'
        self.error_reason = 'error reason'

    def testReportName(self):
        report = Report(self.report_name)
        self.assertEqual(report.get_name(), self.report_name)

    def testDefaultStatusIsPassed(self):
        report = Report(self.report_name)
        self.assertEqual(report.get_status(), Report.PASSED)

    def testStatusIsFailedByConstructor(self):
        report = Report(self.report_name, default_failed=True)
        self.assertEqual(report.get_status(), Report.FAILED)

    def testFailedWithReason(self):
        report = Report(self.report_name)
        self.assertEqual(report.get_status(), Report.PASSED)
        report.failed(self.failure_reason)
        self.assertEqual(report.get_status(), Report.FAILED)
        self.assertEqual(report.get('reason'), self.failure_reason)

    def testFailedWithoutReason(self):
        report = Report(self.report_name)
        self.assertEqual(report.get_status(), Report.PASSED)
        report.failed()
        self.assertEqual(report.get_status(), Report.FAILED)
        self.assertEqual(report.get('reason'), None)

    def testErrorWithReason(self):
        report = Report(self.report_name)
        self.assertEqual(report.get_status(), Report.PASSED)
        report.error(self.error_reason)
        self.assertEqual(report.get_status(), Report.ERROR)
        self.assertEqual(report.get('reason'), self.error_reason)

    def testErrorWithoutReason(self):
        report = Report(self.report_name)
        self.assertEqual(report.get_status(), Report.PASSED)
        report.error()
        self.assertEqual(report.get_status(), Report.ERROR)
        self.assertEqual(report.get('reason'), None)

    def testPassed(self):
        report = Report(self.report_name)
        report.failed(self.failure_reason)
        self.assertEqual(report.get_status(), Report.FAILED)
        report.passed()
        self.assertEqual(report.get_status(), Report.PASSED)

    def testSuccess(self):
        '''
        .. note:: success was deprecated, and it only calls passed()
        '''
        report = Report(self.report_name)
        report.failed(self.failure_reason)
        self.assertEqual(report.get_status(), Report.FAILED)
        report.success()
        self.assertEqual(report.get_status(), Report.PASSED)

    def testClearKeepsName(self):
        report = Report(self.report_name)
        self.assertEqual(report.get_name(), self.report_name)
        report.clear()
        self.assertEqual(report.get_name(), self.report_name)

    def testClearRestoresStatusToDefaultPassed(self):
        report = Report(self.report_name)
        self.assertEqual(report.get_status(), Report.PASSED)
        report.failed('mock failure')
        report.clear()
        self.assertEqual(report.get_status(), Report.PASSED)

    def testClearRestoresStatusToDefaultFailed(self):
        report = Report(self.report_name, default_failed=True)
        self.assertEqual(report.get_status(), Report.FAILED)
        report.passed()
        report.clear()
        self.assertEqual(report.get_status(), Report.FAILED)

    def testAddReservedKeywordRaisesException_status(self):
        report = Report(self.report_name)
        with self.assertRaises(Exception):
            report.add('status', 'some status')

    def testAddReservedKeywordRaisesException_failed(self):
        report = Report(self.report_name)
        with self.assertRaises(Exception):
            report.add('failed', 'some status')

    def testInvalidStatusRaisesException(self):
        report = Report(self.report_name)
        with self.assertRaises(Exception):
            report.set_status('custom status')

    def testDataEntry(self):
        report = Report(self.report_name)
        entry_name = 'my entry'
        entry_data = 'some data'
        report.add(entry_name, entry_data)
        self.assertEqual(report.get(entry_name), entry_data)
        self.assertEqual(report.get(entry_name), entry_data)

    def testDataEntryReplaced(self):
        report = Report(self.report_name)
        entry_name = 'my entry'
        entry_data = 'some data'
        report.add(entry_name, entry_data)
        self.assertEqual(report.get(entry_name), entry_data)
        new_data = 'some other data'
        report.add(entry_name, new_data)
        self.assertEqual(report.get(entry_name), new_data)

    def testClearDataEntry(self):
        report = Report(self.report_name)
        entry_name = 'my entry'
        entry_data = 'some data'
        report.add(entry_name, entry_data)
        self.assertEqual(report.get(entry_name), entry_data)
        report.clear()
        self.assertEqual(report.get(entry_name), None)

    def testSubReportEntry(self):
        entry_name = 'sub report'
        report = Report(self.report_name)
        subreport = Report(entry_name)
        report.add(entry_name, subreport)
        self.assertEqual(report.get(entry_name), subreport)

    def testFailureInSubReportEntry(self):
        entry_name = 'sub report'
        report = Report(self.report_name)
        subreport = Report(entry_name)
        report.add(entry_name, subreport)
        subreport.failed(self.failure_reason)
        self.assertEqual(report.get_status(), Report.FAILED)
        self.assertEqual(report.get('reason'), self.failure_reason)

    def testErrorInSubReportEntry(self):
        entry_name = 'sub report'
        report = Report(self.report_name)
        subreport = Report(entry_name)
        report.add(entry_name, subreport)
        subreport.error(self.error_reason)
        self.assertEqual(report.get_status(), Report.ERROR)
        self.assertEqual(report.get('reason'), self.error_reason)

    def testErrorInOneOfSubReportEntries(self):
        entry_name1 = 'sub report 1'
        entry_name2 = 'sub report 2'
        entry_name3 = 'sub report 3'
        report = Report(self.report_name)
        subreport1 = Report(entry_name1)
        subreport2 = Report(entry_name2)
        subreport3 = Report(entry_name3)
        report.add(entry_name1, subreport1)
        report.add(entry_name2, subreport2)
        report.add(entry_name3, subreport3)
        subreport2.error(self.error_reason)
        self.assertEqual(report.get_status(), Report.ERROR)
        self.assertEqual(report.get('reason'), self.error_reason)

    def testClearSubReportEntry(self):
        entry_name = 'sub report'
        report = Report(self.report_name)
        subreport = Report(entry_name)
        report.add(entry_name, subreport)
        self.assertEqual(report.get(entry_name), subreport)
        report.clear()
        self.assertEqual(report.get(entry_name), None)

    def testDeprecatedApi_is_failed(self):
        report = Report(self.report_name)
        with self.assertRaises(NotImplementedError):
            report.is_failed()
