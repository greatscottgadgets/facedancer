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

from kitty.model.high_level.staged_sequence import StagedSequenceModel, Stage


class RandomSequenceModel(StagedSequenceModel):
    '''
    This class provides random sequences of templates based on the selection strategy.
    It is like :class:`~kitty.model.high_level.staged_sequence.StagedSequenceModel` with a signle stage.
    '''

    def __init__(self, name='RandomSequenceModel', seed=None, callback_generator=None, num_mutations=1000, max_sequence=10):
        '''
        :param name: name of the model object (default: 'RandomSequenceModel')
        :type seed: int
        :param seed: RNG seed (default: None)
        :type callback_generator: func(from_template, to_template) -> func(fuzzer, edge, response) -> None
        :param callback_generator: a function that returns callback functions (default: None)
        :param num_mutations: number of mutations to perform (defualt: 1000)
        :param max_sequence: maximum sequence length (default: 10)
        '''
        super(RandomSequenceModel, self).__init__(name, callback_generator, num_mutations)
        self._max_sequence = max_sequence
        self.seed = seed
        strategy = '1-%d' % max_sequence
        self._stage = Stage(name='internal', selection_strategy=strategy, seed=seed)
        self.add_stage(self._stage)

    def add_template(self, template):
        '''
        Add template that might be used in generated sequences

        :param template: template to add to the model
        '''
        self._stage.add_template(template)
