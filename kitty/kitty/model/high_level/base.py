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

from kitty.core import KittyObject, khash


class _RootNode(object):
    def get_name(self):
        return 'Start'

    def hash(self):
        return khash(self.get_name())


class Connection(object):
    '''
    A connection between to messages,
    '''

    def __init__(self, src, dst, callback):
        '''
        :param src: the source node
        :param dst: the destination node
        :param callback: the function to call after sending src and before sending dst
        '''
        self.src = src
        self.dst = dst
        self.callback = callback

    def __repr__(self):
        return '%s -> %s' % (self.src, self.dst)


class BaseModel(KittyObject):
    '''
    This class defines the API that is required to be implemented by any top-
    level model

    .. note:: This class should not be instantiated directly.
    '''

    def __init__(self, name='BaseModel'):
        '''
        :param name: name of the model (default: BaseModel)
        '''
        super(BaseModel, self).__init__(name)
        self._num_mutations = 0
        self._sequence = None
        self._current_index = -1
        self._ready = False
        self._notification_handler = None
        self.ROOT_NODE = _RootNode()

    def get_template_info(self):
        '''
        :return: dictionary of information regarding the current template

        .. note::

            by default, we return None, as the current template
            might not be interesting.
            Take a look at GraphModel for actual implementation.
        '''
        return {}

    def current_index(self):
        '''
        :return: current mutation index
        '''
        return self._current_index

    def _get_ready(self):
        '''
        Make sure model is ready for running
        '''
        self.not_implemented('_get_ready')

    def _mutate(self):
        '''
        Perform the actual mutation
        '''
        self.not_implemented('_mutate')

    def skip(self, count):
        '''
        :param count: number of cases to skip
        :return: number of cases skipped
        '''
        self._get_ready()
        skipped = 0
        for i in range(count):
            if self.mutate():
                skipped += 1
            else:
                break
        return skipped

    def mutate(self):
        '''
        Mutate to next state

        :return: True if mutated, False if not
        '''
        self._get_ready()
        if self._is_last_index():
            return False
        self._current_index += 1
        self._mutate()
        return True

    def get_model_info(self):
        '''
        :rtype: dict
        :return: model information
        '''
        self.not_implemented('get_info')

    def get_test_info(self):
        '''
        :rtype: dict
        :return: test information
        '''
        self._get_ready()
        res = {
            'sequence': {
                'current': self.get_sequence_str()
            },
            'mutation': {
                'current_index': self._current_index,
                'total_number': self.num_mutations()
            }
        }
        return res

    def get_sequence(self):
        '''
        :rtype: [Connection]
        :return: Sequence of current case
        '''
        self._get_ready()
        assert self._sequence
        return self._sequence[:]

    def get_sequence_str(self):
        '''
        :return: string representation of the sequence
        '''
        sequence = self.get_sequence()
        return '->'.join(e.dst.name for e in sequence)

    def last_index(self):
        '''
        :return: the last valid mutation index
        '''
        return self.num_mutations() - 1

    def _is_last_index(self):
        '''
        :return: is current index the last index
        '''
        return self._current_index == self.last_index()

    def num_mutations(self):
        '''
        :return: number of mutations in the model
        '''
        self._get_ready()
        return self._num_mutations

    def hash(self):
        '''
        :return: a hash of the model object (used for notifying change in the model)
        '''
        return khash(type(self).__name__)

    def get_stages(self):
        '''
        :return: dictionary of information regarding the stages in the fuzzing session

        .. note::

            structure: { current: ['stage1', 'stage2', 'stage3'], 'stages': {'source1': ['dest1', 'dest2'], 'source2': ['dest1', 'dest3']}}
        '''
        sequence = self.get_sequence()
        return {
            'current': [e.dst.get_name() for e in sequence],
            'stages': {e.src.get_name(): [e.dst.get_name()] for e in sequence}
        }

    def set_notification_handler(self, handler):
        '''
        :param handler: handler for notifications from the data model

        .. note::

            The handler should support the following APIs:

            - handle_stage_changed(data_model)
        '''
        self._notification_handler = handler
