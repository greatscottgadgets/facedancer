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
Tests for the web interface (server side)
'''
import os
import requests
from kitty.model import GraphModel, Template, String, UInt32
from kitty.fuzzers import ServerFuzzer
from kitty.interfaces import WebInterface
from mocks.mock_target import ServerTargetMock
from common import BaseTestCase


class WebInterfaceTest(BaseTestCase):

    def setUp(self):
        super(WebInterfaceTest, self).setUp(None)
        self.t_str = Template(name='simple_str_template', fields=[String(name='str1', value='kitty')])
        self.t_int = Template(name='simple_int_template', fields=[UInt32(name='int1', value=0x1234)])
        self.fuzzer = None
        self.host = '127.0.0.1'
        self.port = 11223
        self.url = 'http://%(host)s:%(port)s' % {'host': self.host, 'port': self.port}
        self.prepare()

    def tearDown(self):
        if self.fuzzer:
            self.logger.info('still have fuzzer, stop it')
            self.fuzzer.stop()

    def prepare(self):
        self.start_index = 0
        self.end_index = 20
        self.delay_duration = 0
        self.fuzzer = ServerFuzzer(name="TestServerFuzzer", logger=self.logger)

        self.model = GraphModel()
        self.model.logger = self.logger

        self.model.connect(self.t_str)
        self.fuzzer.set_model(self.model)

    def _webValidRequest(self, request):
        resp = requests.get(request)
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status_code, 200)
        as_json = resp.json()
        self.assertIsNotNone(as_json)
        return as_json

    def _webGetStats(self):
        return self._webValidRequest('%s/api/stats.json' % self.url)

    def _webGetReport(self, report_id):
        return self._webValidRequest('%s/api/report?report_id=%s' % (self.url, report_id))

    def _webGetTemplateInfo(self):
        return self._webValidRequest('%s/api/template_info.json' % self.url)

    def _webGetStages(self):
        return self._webValidRequest('%s/api/stages.json' % self.url)

    def _webGetFavicon(self):
        resp = requests.get('%s/favicon.ico' % self.url)
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status_code, 200)
        return resp

    def _webGetReportList(self):
        resp = self._webGetStats()
        self.assertIn('reports_extended', resp)
        reports = resp['reports_extended']
        return reports

    def _runFuzzerWithReportList(self, uut, report_list):
        config = {}
        for report_id in report_list:
            config[str(report_id)] = {'report': {'status': 'failed', 'reason': 'failure reason'}}

        self.fuzzer.set_interface(uut)

        target = ServerTargetMock(config, logger=self.logger)
        self.fuzzer.set_target(target)

        self.fuzzer.start()

    def _testStatsApiReportList(self, report_list):
        uut = WebInterface(host=self.host, port=self.port)
        report_list.sort()
        self._runFuzzerWithReportList(uut, report_list)
        actual_report_list = [x[0] for x in self._webGetReportList()]
        self.assertListEqual(actual_report_list, report_list)

    def testStatsApiReportListEmpty(self):
        self._testStatsApiReportList([])

    def testStatsApiReportListSingle(self):
        self._testStatsApiReportList([5])

    def testStatsApiReportListMultiple(self):
        self._testStatsApiReportList([1, 2, 3, 4, 5])

    def testStatsApiReportListAll(self):
        self._testStatsApiReportList([x for x in range(self.end_index)])

    def testTemplateInfoApi(self):
        #
        # This is based on the usage in index.html
        #
        uut = WebInterface(host=self.host, port=self.port)
        self._runFuzzerWithReportList(uut, [])
        template_info = self._webGetTemplateInfo()
        self.assertIn('name', template_info)
        self.assertIn('field_type', template_info)
        self.assertIn('fields', template_info)
        self.assertIn('mutation', template_info)
        self.assertIn('total_number', template_info['mutation'])
        self.assertIn('current_index', template_info['mutation'])

    def testGetStagesApi(self):
        uut = WebInterface(host=self.host, port=self.port)
        self._runFuzzerWithReportList(uut, [])
        resp = self._webGetStages()
        self.assertIn('current', resp)
        self.assertIn('stages', resp)

    def _testReportApiReportExists(self, report_list):
        for report_id in report_list:
            response = self._webGetReport(report_id)
            self.assertIn('report', response)
            self.assertIn('encoding', response)

    def _testReportApiValid(self, report_list):
        self._testStatsApiReportList(report_list)
        self._testReportApiReportExists(report_list)

    def testReportApiSingle(self):
        self._testReportApiValid([1])

    def testReportApiMultiple(self):
        self._testReportApiValid([1, 2, 3])

    def testReportApiAll(self):
        self._testReportApiValid([x for x in range(self.end_index)])

    def _testReportApiError(self, request):
        self._testReportApiValid([x for x in range(self.end_index)])
        resp = self._webValidRequest(request)
        self.assertIn('error', resp)
        self.assertNotIn('report', resp)

    def testReportApiErrorWhenNoReportId(self):
        self._testReportApiError('%s/api/report' % (self.url))

    def testReportApiErrorWhenReportIdNotInt(self):
        self._testReportApiError('%s/api/report?report_id=%s' % (self.url, '%%'))

    def testReportApiErrorWhenNoSuchReport(self):
        self._testReportApiError('%s/api/report?report_id=%s' % (self.url, self.end_index + 1))

    def _testPauseApi(self):
        '''
        .. todo:: pause/resume api tests
        '''
        pass

    def get_static_content(self, filename):
        (dir_path, _) = os.path.split(__file__)
        index_path = os.path.join(dir_path, '..', 'kitty', 'interfaces', 'web', 'static', filename)
        data = None
        with open(index_path, 'rb') as f:
            data = f.read()
        return data.decode()

    def testGetIndexHtml(self):
        url = self.url + '/index.html'
        uut = WebInterface(host=self.host, port=self.port)
        self._runFuzzerWithReportList(uut, [])
        resp = requests.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers['content-type'], 'text/html')
        index_content = self.get_static_content('index.html')
        self.assertEqual(resp.text, index_content)

    def testReturnIndexForRoot(self):
        root_url = self.url + '/'
        index_url = self.url + '/index.html'
        uut = WebInterface(host=self.host, port=self.port)
        self._runFuzzerWithReportList(uut, [])
        root_resp = requests.get(root_url)
        index_url = requests.get(index_url)
        self.assertEqual(root_resp.status_code, 200)
        self.assertEqual(root_resp.headers['content-type'], 'text/html')
        self.assertEqual(root_resp.text, index_url.text)

    def testGetOtherFilesReturns401(self):
        url = self.url + '/../../../../../../../etc/passwd'
        uut = WebInterface(host=self.host, port=self.port)
        self._runFuzzerWithReportList(uut, [])
        resp = requests.get(url)
        self.assertEqual(resp.status_code, 401)

    def testPost(self):
        url = self.url + '/index.html'
        uut = WebInterface(host=self.host, port=self.port)
        self._runFuzzerWithReportList(uut, [])
        resp = requests.post(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers['content-type'], 'text/html')
        index_content = self.get_static_content('index.html')
        self.assertEqual(resp.text, index_content)
