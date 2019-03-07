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

import time
import traceback
from binascii import hexlify
from kitty.targets.base import BaseTarget
from kitty.data.report import Report


class ServerTarget(BaseTarget):
    '''
    This class represents a target when fuzzing a server.
    Its main job, beside using the Controller and Monitors, is to send and
    receive data from/to the target.
    '''

    def __init__(self, name, logger=None, expect_response=False):
        '''
        :param name: name of the target
        :param logger: logger for this object (default: None)
        :param expect_response: should wait for response from the victim (default: False)
        '''
        super(ServerTarget, self).__init__(name, logger)
        self.expect_response = expect_response
        self.send_failure = False
        self.receive_failure = False
        self.transmission_count = 0
        self.transmission_report = None

    def set_expect_response(self, expect_response):
        '''
        :param expect_response: should wait for response from the victim (default: False)
        '''
        self.expect_response = expect_response

    def _send_to_target(self, payload):
        self.not_implemented('send_to_target')

    def _receive_from_target(self):
        self.not_implemented('receive_from_target')

    def pre_test(self, test_num):
        '''
        Called before each test

        :param test_num: the test number
        '''
        super(ServerTarget, self).pre_test(test_num)
        self.send_failure = False
        self.receive_failure = False
        self.transmission_count = 0

    def transmit(self, payload):
        '''
        Transmit single payload, and receive response, if expected.
        The actual implementation of the send/receive should be in
        ``_send_to_target`` and ``_receive_from_target``.

        :type payload: str
        :param payload: payload to send
        :rtype: str
        :return: the response (if received)
        '''
        response = None
        trans_report_name = 'transmission_0x%04x' % self.transmission_count
        trans_report = Report(trans_report_name)
        self.transmission_report = trans_report
        self.report.add(trans_report_name, trans_report)
        try:
            trans_report.add('request (hex)', hexlify(payload).decode())
            trans_report.add('request (raw)', '%s' % payload)
            trans_report.add('request length', len(payload))
            trans_report.add('request time', time.time())

            request = hexlify(payload).decode()
            request = request if len(request) < 100 else (request[:100] + ' ...')
            self.logger.info('request(%d): %s' % (len(payload), request))
            self._send_to_target(payload)
            trans_report.success()

            if self.expect_response:
                try:
                    response = self._receive_from_target()
                    trans_report.add('response time', time.time())
                    trans_report.add('response (hex)', hexlify(response).decode())
                    trans_report.add('response (raw)', '%s' % response)
                    trans_report.add('response length', len(response))
                    printed_response = hexlify(response).decode()
                    printed_response = printed_response if len(printed_response) < 100 else (printed_response[:100] + ' ...')
                    self.logger.info('response(%d): %s' % (len(response), printed_response))
                except Exception as ex2:
                    trans_report.failed('failed to receive response: %s' % ex2)
                    trans_report.add('traceback', traceback.format_exc())
                    self.logger.error('target.transmit - failure in receive (exception: %s)' % ex2)
                    self.logger.error(traceback.format_exc())
                    self.receive_failure = True
            else:
                response = ''
        except Exception as ex1:
            trans_report.failed('failed to send payload: %s' % ex1)
            trans_report.add('traceback', traceback.format_exc())
            self.logger.error('target.transmit - failure in send (exception: %s)' % ex1)
            self.logger.error(traceback.format_exc())
            self.send_failure = True
        self.transmission_count += 1
        return response

    def post_test(self, test_num):
        '''
        Called after each test

        :param test_num: the test number
        '''
        super(ServerTarget, self).post_test(test_num)
        if self.send_failure:
            self.report.failed('send failure')
        elif self.expect_response and self.receive_failure:
            self.report.failed('receive failure')
