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
KittyObject is subclassed by most of Kitty's objects.

It provides logging, naming, and description of the object.
'''
import logging
import os
import time


class KittyObject(object):
    '''
    Basic class to ease logging and description of objects.
    '''

    _logger = None
    log_file_name = './kittylogs/kitty_%s.log' % (time.strftime("%Y%m%d-%H%M%S"),)

    @classmethod
    def get_logger(cls):
        '''
        :return: the class logger
        '''
        if KittyObject._logger is None:
            logger = logging.getLogger('kitty')
            logger.setLevel(logging.INFO)
            consolehandler = logging.StreamHandler()
            console_format = logging.Formatter('[%(levelname)-8s][%(module)s.%(funcName)s] %(message)s')
            consolehandler.setFormatter(console_format)
            logger.addHandler(consolehandler)
            if not os.path.exists('./kittylogs'):
                os.mkdir('./kittylogs')
            filehandler = logging.FileHandler(KittyObject.log_file_name)
            file_format = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(module)s.%(funcName)s] -> %(message)s')
            filehandler.setFormatter(file_format)
            logger.addHandler(filehandler)
            KittyObject._logger = logger
        return KittyObject._logger

    @classmethod
    def get_log_file_name(cls):
        '''
        :return: log file name
        '''
        return KittyObject.log_file_name

    @classmethod
    def set_verbosity(cls, verbosity):
        '''
        Set verbosity of logger

        :param verbosity: verbosity level. currently, we only support 1 (logging.DEBUG)
        '''
        if verbosity > 0:
            # currently, we only toggle between INFO, DEBUG
            logger = KittyObject.get_logger()
            levels = [logging.DEBUG]
            verbosity = min(verbosity, len(levels)) - 1
            logger.setLevel(levels[verbosity])

    def __init__(self, name, logger=None):
        '''
        :param name: name of the object
        '''
        self.name = name
        if logger:
            self.logger = logger
        else:
            self.logger = KittyObject.get_logger()

    def not_implemented(self, func_name):
        '''
        log access to unimplemented method and raise error

        :param func_name: name of unimplemented function.
        :raise: NotImplementedError detailing the function the is not implemented.
        '''
        msg = '%s is not overridden by %s' % (func_name, type(self).__name__)
        self.logger.error(msg)
        raise NotImplementedError(msg)

    def get_description(self):
        '''
        :rtype: str
        :return: the description of the object. by default only prints the object type.
        '''
        return type(self).__name__

    def get_name(self):
        '''
        :rtype: str
        :return: object's name
        '''
        return self.name
