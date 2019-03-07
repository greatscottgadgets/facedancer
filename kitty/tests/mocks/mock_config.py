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

import json


class Config(object):

    def __init__(self, config_name, config):
        self.INVALID = object()
        if config is not None:
            self.config = config
        else:
            self.config = {}
            # no try-except here - I want to crash on failure to load config
            fconf = open('mocks/mock.cfg', 'rb')
            full_config = json.load(fconf)
            fconf.close()
            if 'global' in full_config:
                self.config = full_config['global']
            if config_name in full_config:
                for k, v in full_config[config_name].items():
                    self.config[k] = v
        self.func = None
        self.test_conf = {}

    def get_config_dict(self):
        return self.config

    def set_test(self, test_num):
        self.test_conf = {}
        if 'always' in self.config:
            self.test_conf.update(self.config['always'])
        if str(test_num) in self.config:
            self.test_conf.update(self.config[str(test_num)])

    def set_func(self, func):
        self.func = func

    def get_val(self, key):
        if self.func in self.test_conf:
            if key in self.test_conf[self.func]:
                return self.test_conf[self.func][key]
        return self.INVALID

    def get_vals(self):
        if self.func in self.test_conf:
            return self.test_conf[self.func]
        return None
