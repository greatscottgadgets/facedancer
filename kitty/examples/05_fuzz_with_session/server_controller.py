# Copyright (C) 2016 Cisco Systems, Inc. and/or its affiliates. All rights reserved.
#
# This example was authored and contributed by dark-lbp <jtrkid@gmail.com>
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

import socket
import subprocess
import time
from kitty.controllers.base import BaseController


class SessionServerController(BaseController):
    '''
    This controller controls our SessionServer.
    '''

    def __init__(self, name, host, port, logger=None):
        '''
        :param name: name of the object
        :param host: Listen address for target
        :param port: Listen port for target
        :param logger: logger for the controller (default: None)
        :example:

            ::
                controller = ServerController(name='ServerController', host='target_ip', port=target_port)
        '''
        super(SessionServerController, self).__init__(name, logger)
        self._host = host
        self._port = port
        self._server = None
        self._active = False

    def setup(self):
        super(SessionServerController, self).setup()
        self.logger.info('Trying to start target!!!')
        self._restart_target()
        if not self.is_victim_alive():
            msg = 'Controller cannot start target'
            raise Exception(msg)

    def teardown(self):
        super(SessionServerController, self).teardown()
        if not self.is_victim_alive():
            msg = 'Target is already down'
            self.logger.error(msg)
        else:
            msg = 'Test Finish'
            self.logger.info(msg)

    def post_test(self):
        super(SessionServerController, self).post_test()
        if not self.is_victim_alive():
            if self._server:
                out, err = self._server.communicate()
                self.logger.error(err)
                self.report.failed("Target does not respond")
                self.report.add('Traceback', err)
            else:
                self.logger.error("Target does not respond")
                self.report.failed("Target does not respond")

    def pre_test(self, test_number):
        self._restart_target()
        super(SessionServerController, self).pre_test(test_number)

    def _restart_target(self):
        """
        Restart our Target.
        """
        if self._server:
            if self._server.returncode is None:
                self._server.kill()
                time.sleep(0.2)
        self._server = subprocess.Popen("python session_server.py", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        time.sleep(0.2)

    def is_victim_alive(self):
        self._active = False
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((self._host, self._port))
            s.close()
            self._active = True
        except socket.error:
            return self._active
        return self._active
