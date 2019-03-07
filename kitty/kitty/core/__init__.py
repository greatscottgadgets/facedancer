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
The classes in this module has very little to do with the fuzzing process,
however, those classes and functions are used all over kitty.
'''
from kitty.core.kitty_object import KittyObject
from kitty.core.threading_utils import FuncThread, LoopFuncThread


class KittyException(Exception):
    '''
    Simple exception, used mainly to make tests better, and identify
    exceptions that were thrown by kitty directly.
    '''
    pass


def khash(*args):
    '''
    hash arguments. khash handles None in the same way accross runs (which is good :))
    '''
    ksum = sum([hash(arg if arg is not None else -13371337) for arg in args])
    return hash(str(ksum))
