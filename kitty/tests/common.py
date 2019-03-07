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
Tests for low level fields
'''
import unittest
import logging
from binascii import hexlify


test_logger = None


def get_test_logger():
    global test_logger
    if test_logger is None:
        logger = logging.getLogger('unit_test_logs')
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] -> %(message)s'
        )
        handler = logging.FileHandler('logs/test.log', mode='w')
        handler.setFormatter(formatter)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        test_logger = logger
    return test_logger


def metaTest(func):
    def test_wrap(self):
        if self.__class__.__meta__:
            self.skipTest('Test should not run from meta class')
        else:
            return func(self)
    return test_wrap


class BaseTestCase(unittest.TestCase):

    def setUp(self, field_class):
        self.logger = get_test_logger()
        self.logger.debug('TESTING METHOD: %s', self._testMethodName)
        self.todo = []
        self.cls = field_class

    def get_all_mutations(self, field, reset=True):
        res = []
        while field.mutate():
            rendered = field.render()
            res.append(rendered)
            self.logger.debug(hexlify(rendered.tobytes()).decode())
        if reset:
            field.reset()
        return res
