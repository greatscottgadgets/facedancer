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
Threading Utils
'''
import threading


class FuncThread(threading.Thread):
    '''
    FuncThread is a thread wrapper to create thread from a function
    '''

    def __init__(self, func, *args):
        '''
        :param func: function to be called in this thread
        :param args: arguments for the function
        '''
        super(FuncThread, self).__init__()
        self._func = func
        self._args = args

    def run(self):
        '''
        run the the function in this thread's context
        '''
        self._func(*self._args)


class LoopFuncThread(threading.Thread):
    '''
    FuncThread is a thread wrapper to create thread from a function
    '''

    def __init__(self, func, *args):
        '''
        :param func: function to be call in a loop in this thread
        :param args: arguments for the function
        '''
        super(LoopFuncThread, self).__init__()
        self._func = func
        self._args = args
        self._stop_event = threading.Event()
        self._func_stop_event = None

    def set_func_stop_event(self, func_stop_event):
        '''
        :type func_stop_event: :class:`~threading.Event`
        :param func_stop_event: event to signal stop to the _func
        '''
        self._func_stop_event = func_stop_event

    def run(self):
        '''
        run the the function in a loop until stoped
        '''
        while not self._stop_event.isSet():
            self._func(*self._args)

    def stop(self):
        '''
        stop the thread, return after thread stopped
        '''
        self._stop_event.set()
        if self._func_stop_event is not None:
            self._func_stop_event.set()
        self.join(timeout=1)
        if self.isAlive():
            print('Failed to stop thread')
