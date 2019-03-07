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

from kitty.core.kitty_object import KittyObject


class BaseInterface(KittyObject):
    '''
    User interface API
    '''

    def __init__(self, name='BaseInterface', logger=None):
        '''
        :param name: name of the object
        :param logger: logger for the object (default: None)
        '''
        super(BaseInterface, self).__init__(name, logger)
        self._continue_event = None
        # the data provider
        self.dataman = None

    def set_data_provider(self, data):
        '''
        :param data: the data provider
        '''
        self.dataman = data

    def failure_detected(self):
        '''
        handle failure detection
        '''
        raise NotImplementedError()

    def progress(self):
        '''
        handle progress
        '''
        raise NotImplementedError()

    def finished(self):
        '''
        handle finished
        '''
        raise NotImplementedError()

    def set_continue_event(self, event):
        '''
        :param event: used to control pause/continue
        '''
        self._continue_event = event

    def pause(self):
        '''
        pause the fuzzer
        '''
        assert(self._continue_event)
        self._continue_event.clear()

    def is_paused(self):
        '''
        :return: whether current state is paused
        '''
        assert(self._continue_event)
        return not self._continue_event.isSet()

    def resume(self):
        '''
        resume the fuzzer
        '''
        assert(self._continue_event)
        self._continue_event.set()

    def start(self):
        '''
        start the monitor
        '''
        assert(self.dataman)
        self._start()

    def _start(self):
        raise NotImplementedError()

    def stop(self):
        '''
        stop the monitor
        '''
        self._stop()

    def _stop(self):
        raise NotImplementedError()


class EmptyInterface(BaseInterface):
    '''
    This interface may be used when there is no need for user interface
    '''

    def __init__(self, name='EmptyInterface', logger=None):
        '''
        :param name: name of the object
        :param logger: logger for the object (default: None)
        '''
        super(EmptyInterface, self).__init__(name, logger)

    def failure_detected(self):
        '''
        handle failure detection
        '''
        pass

    def progress(self):
        '''
        handle progress
        '''
        pass

    def finished(self):
        '''
        handle finished
        '''
        pass

    def _start(self):
        pass

    def _stop(self):
        pass
