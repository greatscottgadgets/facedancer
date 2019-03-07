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
import os
import unittest
from test_data_report import *
from test_fuzzer_client import *
from test_fuzzer_server import *
from test_interface_web import *
from test_model_high_level import *
from test_model_low_level_calculated import *
from test_model_low_level_condition import *
from test_model_low_level_container import *
from test_model_low_level_container_mutator import *
from test_model_low_level_encoders import *
from test_model_low_level_fields import *
from test_model_low_level_full import *
from test_model_low_level_mutated import *
from test_remote_rpc import *
from test_target import *
from test_test_list import *


if __name__ == '__main__':
    if not os.path.exists('logs'):
        os.mkdir('logs')
    unittest.main()
