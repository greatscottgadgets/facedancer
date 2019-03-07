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
Generate random sequences of messages for a session.
Currently, perform no special operation for mutations on the nodes.
'''

import random
import re
from kitty.model.high_level.base import Connection, BaseModel
from kitty.core import KittyObject, KittyException, khash


class Stage(KittyObject):
    '''
    Stage supports 4 different sequence length strategy.
    For all of them, the order of templates will be random.
    The available strategies are:

    - for random length - 'random'
    - for exact length - '12'
    - for length in range - '1-3'
    - for all - 'all'
    '''

    _const_pattern = r'^\d{1,10}$'
    _random_pattern = r'^random$'
    _all_pattern = r'^all$'
    _range_pattern = r'^\d{1,10}-\d{1,10}$'

    def __init__(self, name, selection_strategy='1', seed=None):
        '''
        :param name: name of the Stage
        :param selection_strategy: strategy for selecting amount of template in each mutation
        :param seed: RNG seed (default: None)
        '''
        super(Stage, self).__init__('Stage[%s]' % name)
        self._templates = []
        self._strategy = selection_strategy
        self._min_sequence = None
        self._max_sequence = None
        self._r = random.Random()
        self._seed = seed
        if seed:
            self._r.seed(seed)
        self._current_sequence_templates = None
        self._default_sequence_templates = None
        self._ready = False
        self._validate_strategy(selection_strategy)

    def _validate_strategy(self, strategy):
        valid = False
        if re.match(Stage._all_pattern, strategy):
            valid = True
        elif re.match(Stage._random_pattern, strategy):
            valid = True
        elif re.match(Stage._const_pattern, strategy):
            valid = True
        elif re.match(Stage._range_pattern, strategy):
            ts = strategy.split('-')
            min_sequence = int(ts[0])
            max_sequence = int(ts[1])
            if max_sequence < min_sequence:
                raise KittyException('bad range strategy %s, max < min' % strategy)
            valid = True
        if not valid:
            raise KittyException('strategy %s is not valid' % strategy)

    def add_template(self, template):
        '''
        :param template: template to add to the stage
        '''
        self._templates.append(template)
        return template

    def get_templates(self):
        '''
        :return: list of the stage's templates
        '''
        return self._templates[:]

    def _get_ready(self):
        if not self._ready:
            if re.match(Stage._random_pattern, self._strategy):
                self._min_sequence = 1
                self._max_sequence = len(self._templates)
            elif re.match(Stage._all_pattern, self._strategy):
                self._min_sequence = len(self._templates)
                self._max_sequence = len(self._templates)
            elif re.match(Stage._const_pattern, self._strategy):
                self._min_sequence = int(self._strategy)
                self._max_sequence = int(self._strategy)
                if self._max_sequence > len(self._templates):
                    raise KittyException('bad const strategy %s > template count(%s)' % (self._max_sequence, len(self._templates)))
            elif re.match(Stage._range_pattern, self._strategy):
                ts = self._strategy.split('-')
                self._min_sequence = int(ts[0])
                self._max_sequence = int(ts[1])
                if self._max_sequence < self._min_sequence:
                    raise KittyException('bad range strategy %s, max < min' % self._strategy)
                if self._max_sequence > len(self._templates):
                    raise KittyException('bad range strategy %s, max > template count(%s)' % (self._max_sequence, len(self._templates)))
            self._default_sequence_templates = tuple(self._templates[:self._min_sequence])
            self._current_sequence_templates = self._default_sequence_templates
            self._ready = True

    def mutate(self):
        self._get_ready()
        sequence_size = self._r.randint(self._min_sequence, self._max_sequence)
        self._current_sequence_templates = tuple(self._r.sample(self._templates, sequence_size))
        return self._current_sequence_templates

    def get_sequence_templates(self):
        '''
        :return: templates of current sequence mutation
        '''
        self._get_ready()
        return self._current_sequence_templates

    def __repr__(self):
        return '%s(%s from %s)' % (self.name, self._strategy, len(self._templates))

    def hash(self):
        hashed = khash(self._strategy, self._seed)
        for t in self._templates:
            hashed = khash(hashed, t.hash())
        return hashed


class StagedSequenceModel(BaseModel):
    '''
    The StagedSequenceModel provides sequences that are constructed from multiple stages of sequences.
    Each such stage provides its part of the sequence based on its strategy.
    The main goal of the Staged sequence mode is to find flaws in the state handling of a stateful target.

    :example:

        Assuming we have the templates [CreateA .. CreateZ, UseA .. UseZ and DeleteA .. DeleteZ].
        A valid sequence is **CreateA -> UseA -> DeleteA**, so we want to test cases like
        **CreateA -> UseB -> UseA -> DeleteC**, or **CreateA -> DeleteA -> UseA**.
        And let's say the common thing to all sequences is that we always want to start by sending one or more of the Create messages.

        We can do that with StagedSequenceModel:

            ::

                stage1 = Stage('create', selection_strategy='1-5')
                stage1.add_Template(CreateA)
                # ...
                stage1.add_Template(CreateZ)
                stage2 = Stage('use and delete', selection_strategy='3-20')
                stage2.add_Template(UseA)
                stage2.add_Template(DeleteA)
                # ...
                stage2.add_Template(UseZ)
                stage2.add_Template(DeleteZ)

                model = StagedSequenceModel('use and delete mess', num_mutations=10000)
                model.add_stage(stage1)
                model.add_stage(stage2)

        Each time it is asked, it will provide a sequence that starts with 1-5 random "Create" templates,
        followed by 3-20 random Use and Delete messages.
        None of those templates will be mutated, as we try to fuzz the sequence itself, not the message structure.

    Since we don't know the what will be the order of templates in the sequences,
    we can't just provide a callback as we do in GraphModel.
    The solution in our case is to provide the model with a callback generator,
    which receives the from_template and to_template and returns a callback function as described in GraphModel in runtime.
    '''

    def __init__(self, name='StagedSequenceModel', callback_generator=None, num_mutations=1000):
        '''
        :param name: name of the model object (default: 'StagedSequenceModel')
        :type callback_generator: func(from_template, to_template) -> func(fuzzer, edge, response) -> None
        :param callback_generator: a function that returns callback functions
        :param num_mutations: number of mutations to perform
        '''
        super(StagedSequenceModel, self).__init__(name)
        self._stages = []
        if not callback_generator:
            def null_generator(src, dst):
                src = dst
                dst = src
                return None
            self.callback_generator = null_generator
        else:
            self.callback_generator = callback_generator
        self._num_mutations = num_mutations

    def add_stage(self, stage):
        '''
        add a stage. the order of stage is preserved

        :type stage: Stage
        :param stage: the stage to add
        '''
        self._stages.append(stage)

    def _get_ready(self):
        if not self._ready:
            templates = []
            for stage in self._stages:
                templates.extend(stage.get_sequence_templates())
            self._default_sequence = self._sequence_from_templates(templates)
            self._sequence = self._default_sequence
            self._ready = True

    def _mutate(self):
        templates = []
        for stage in self._stages:
            stage.mutate()
            templates.extend(stage.get_sequence_templates())
        self._sequence = self._sequence_from_templates(templates)
        if self._notification_handler:
            self._notification_handler.handle_stage_changed(self)

    def _sequence_from_templates(self, templates):
        sequence = []
        prev = self.ROOT_NODE
        for t in templates:
            cb = self.callback_generator(prev, t)
            sequence.append(Connection(prev, t, cb))
            prev = t
        return sequence

    def get_model_info(self):
        '''
        :return: dictionary of information about this model
        '''
        info = {}
        info['model_name'] = self.name
        info['stages'] = '->'.join([repr(s) for s in self._stages])
        info['sequence'] = {
            'index': self._current_index
        }
        return info

    def get_test_info(self):
        '''
        :return: dictionary of information about the current test
        '''
        info = super(StagedSequenceModel, self).get_test_info()
        seq = self._sequence
        info['sequence']['length'] = len(seq)
        return info

    def hash(self):
        hashed = None
        for stage in self._stages:
            hashed = khash(hashed, stage.hash())
        return hashed
