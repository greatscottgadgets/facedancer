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
Tests for High-Level models:
GraphModel
RandomSequenceModel
StagedSequenceModel & Stage
'''
import os
import unittest
import logging
from kitty.model import GraphModel
from kitty.model import RandomSequenceModel
from kitty.model import StagedSequenceModel, Stage
from kitty.model import Template
from kitty.model import String, UInt32
from kitty.core import KittyException


def not_absolute(func):
    def testNotAbsolute(self):
        self.logger.warning('This test is not absolute')
        func(self)
    return testNotAbsolute


test_logger = None


def get_test_logger():
    global test_logger
    if test_logger is None:
        logger = logging.getLogger('HighLevelDataModels')
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] -> %(message)s'
        )
        handler = logging.FileHandler('logs/test_high_level_model.log', mode='w')
        handler.setFormatter(formatter)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        test_logger = logger
    return test_logger


class GraphModelTests(unittest.TestCase):

    def setUp(self):
        self.logger = get_test_logger()
        self.logger.debug('TESTING METHOD: %s', self._testMethodName)
        self.model = GraphModel()
        self.templates = self.get_templates()
        self.todo = []

    def get_templates(self):
        res = []
        res.append(Template(name='t1', fields=[String('data1')]))
        res.append(Template(name='t2', fields=[String('data2'), UInt32(300)]))
        res.append(Template(name='t3', fields=[UInt32(400)]))
        return res

    def _check_sequences(self, expected_sequences):
        self.logger.debug('check num_mutations()')
        t_num_mutations = sum(s[-1].num_mutations() for s in expected_sequences)
        m_num_mutations = self.model.num_mutations()
        self.assertEqual(t_num_mutations, m_num_mutations)
        sequences = {}
        while self.model.mutate():
            sequence = tuple(self.model.get_sequence())
            if sequence not in sequences:
                sequences[sequence] = 1
            else:
                sequences[sequence] += 1
        self.assertEqual(len(sequences), len(expected_sequences))
        self.logger.debug('check that each sequence appears the appropriate number of times')
        for sequence, count in sequences.items():
            seq_templates = [e.dst for e in sequence]
            self.assertIn(seq_templates, expected_sequences)
            last = seq_templates[-1]
            last_num_mutations = last.num_mutations()
            self.assertEqual(count, last_num_mutations)

    def testSequenceSingleTemplate(self):
        t = self.templates[0]
        self.model.connect(t)
        expected_sequences = [[t]]
        self._check_sequences(expected_sequences)

    def testSequenceDirectPath(self):
        '''
        root -> t1
        '''
        self.model.connect(self.templates[0])
        for i in range(len(self.templates) - 1):
            self.model.connect(self.templates[i], self.templates[i + 1])
        expected_sequences = list(self.templates[:i + 1] for i in range(len(self.templates)))
        self._check_sequences(expected_sequences)

    def testSequenceComplexPath(self):
        '''
        root -> t1
        root -> t1 -> t2
        root -> t1 -> t3
        root -> t1 -> t2 -> t3
        '''
        self.model.connect(self.templates[0])
        self.model.connect(self.templates[0], self.templates[1])
        self.model.connect(self.templates[0], self.templates[2])
        self.model.connect(self.templates[1], self.templates[2])
        expected_sequences = [
            [self.templates[0]],
            [self.templates[0], self.templates[1]],
            [self.templates[0], self.templates[2]],
            [self.templates[0], self.templates[1], self.templates[2]]
        ]
        self._check_sequences(expected_sequences)

    def testMultiHeadPath(self):
        '''
        root -> t1
        root -> t2
        root -> t3
        '''
        expected_sequences = []
        for t in self.templates:
            expected_sequences.append([t])
            self.model.connect(t)
        self._check_sequences(expected_sequences)

    def _check_skip(self, to_skip, expected_skipped, expected_mutated):
        skipped = self.model.skip(to_skip)
        self.assertEqual(expected_skipped, skipped)
        mutated = 0
        while self.model.mutate():
            mutated += 1
        self.assertEqual(expected_mutated, mutated)

    def testSkipZeroSingleTemplate(self):
        self.model.connect(self.templates[0])
        m_num_mutations = self.model.num_mutations()
        to_skip = 0
        expected_skipped = to_skip
        expected_mutated = m_num_mutations
        self._check_skip(to_skip, expected_skipped, expected_mutated)

    def testSkipHalfSingleTemplate(self):
        self.model.connect(self.templates[0])
        m_num_mutations = self.model.num_mutations()
        to_skip = m_num_mutations // 2
        expected_skipped = to_skip
        expected_mutated = m_num_mutations - expected_skipped
        self._check_skip(to_skip, expected_skipped, expected_mutated)

    def testSkipExactSingleTemplate(self):
        self.model.connect(self.templates[0])
        m_num_mutations = self.model.num_mutations()
        to_skip = m_num_mutations
        expected_skipped = to_skip
        expected_mutated = m_num_mutations - expected_skipped
        self._check_skip(to_skip, expected_skipped, expected_mutated)

    def testSkipTooMuchSingleTemplate(self):
        self.model.connect(self.templates[0])
        m_num_mutations = self.model.num_mutations()
        to_skip = m_num_mutations + 10
        expected_skipped = m_num_mutations
        expected_mutated = m_num_mutations - expected_skipped
        self._check_skip(to_skip, expected_skipped, expected_mutated)

    def testSkipZeroMultiTemplate(self):
        self.model.connect(self.templates[0])
        self.model.connect(self.templates[0], self.templates[1])
        m_num_mutations = self.model.num_mutations()
        to_skip = 0
        expected_skipped = to_skip
        expected_mutated = m_num_mutations
        self._check_skip(to_skip, expected_skipped, expected_mutated)

    def testSkipHalfMultiTemplate(self):
        self.model.connect(self.templates[0])
        self.model.connect(self.templates[0], self.templates[1])
        m_num_mutations = self.model.num_mutations()
        to_skip = m_num_mutations // 2
        expected_skipped = to_skip
        expected_mutated = m_num_mutations - expected_skipped
        self._check_skip(to_skip, expected_skipped, expected_mutated)

    def testSkipExactMultiTemplate(self):
        self.model.connect(self.templates[0])
        self.model.connect(self.templates[0], self.templates[1])
        m_num_mutations = self.model.num_mutations()
        to_skip = m_num_mutations
        expected_skipped = to_skip
        expected_mutated = m_num_mutations - expected_skipped
        self._check_skip(to_skip, expected_skipped, expected_mutated)

    def testSkipTooMuchMultiTemplate(self):
        self.model.connect(self.templates[0])
        self.model.connect(self.templates[0], self.templates[1])
        m_num_mutations = self.model.num_mutations()
        to_skip = m_num_mutations + 10
        expected_skipped = m_num_mutations
        expected_mutated = m_num_mutations - expected_skipped
        self._check_skip(to_skip, expected_skipped, expected_mutated)

    def testFailureToTo(self):
        self.assertEqual(len(self.todo), 0)

    def testExceptionIfLoop(self):
        self.model.connect(self.templates[0])
        self.model.connect(self.templates[0], self.templates[1])
        self.model.connect(self.templates[1], self.templates[0])
        with self.assertRaises(KittyException):
            self.model.num_mutations()


class StagedSequenceModelTests(unittest.TestCase):

    def setUp(self):
        self.logger = get_test_logger()
        self.logger.debug('TESTING METHOD: %s', self._testMethodName)
        self.stage_lengths = self.get_stage_map()
        self.stages = list(self.stage_lengths.keys())
        self.todo = []

    def get_stage_map(self):
        stages = {}
        for i in range(1, 4):
            s = Stage(str(i), str(i), 1234)
            for n in range(i):
                name = 't%d_%d' % (i, n)
                value = 'd%d_%d' % (i, n)
                s.add_template(Template(name=name, fields=[String(value)]))
            stages[s] = i
        return stages

    def testNumMutationsSingleStage(self):
        num_mutation_list = [0, 1, 500, 1000, 10000]
        for expected_num_mutations in num_mutation_list:
            model = StagedSequenceModel(num_mutations=expected_num_mutations)
            model.add_stage(self.stages[0])
            m_num_mutations = model.num_mutations()
            self.assertEqual(expected_num_mutations, m_num_mutations)
            actual_mutations = 0
            while model.mutate():
                actual_mutations += 1
            self.assertEqual(expected_num_mutations, actual_mutations)

    def testNumMutationsMultiStage(self):
        num_mutation_list = [0, 1, 500, 1000, 10000]
        for expected_num_mutations in num_mutation_list:
            model = StagedSequenceModel(num_mutations=expected_num_mutations)
            for stage in self.stages:
                model.add_stage(stage)
            m_num_mutations = model.num_mutations()
            self.assertEqual(expected_num_mutations, m_num_mutations)
            actual_mutations = 0
            while model.mutate():
                actual_mutations += 1
            self.assertEqual(expected_num_mutations, actual_mutations)

    def _check_skip(self, model, to_skip, expected_skipped, expected_mutated):
        skipped = model.skip(to_skip)
        self.assertEqual(expected_skipped, skipped)
        mutated = 0
        while model.mutate():
            mutated += 1
        self.assertEqual(expected_mutated, mutated)

    def testSkipZero(self):
        model = StagedSequenceModel(num_mutations=120)
        model.add_stage(self.stages[0])
        model.add_stage(self.stages[1])
        m_num_mutations = model.num_mutations()
        to_skip = 0
        expected_skipped = to_skip
        expected_mutated = m_num_mutations - expected_skipped
        self._check_skip(model, to_skip, expected_skipped, expected_mutated)

    def testSkipHalf(self):
        model = StagedSequenceModel(num_mutations=120)
        model.add_stage(self.stages[0])
        model.add_stage(self.stages[1])
        m_num_mutations = model.num_mutations()
        to_skip = m_num_mutations // 2
        expected_skipped = to_skip
        expected_mutated = m_num_mutations - expected_skipped
        self._check_skip(model, to_skip, expected_skipped, expected_mutated)

    def testSkipExact(self):
        model = StagedSequenceModel(num_mutations=120)
        model.add_stage(self.stages[0])
        model.add_stage(self.stages[1])
        m_num_mutations = model.num_mutations()
        to_skip = m_num_mutations
        expected_skipped = to_skip
        expected_mutated = m_num_mutations - expected_skipped
        self._check_skip(model, to_skip, expected_skipped, expected_mutated)

    def testSkipTooMuch(self):
        model = StagedSequenceModel(num_mutations=120)
        model.add_stage(self.stages[0])
        model.add_stage(self.stages[1])
        m_num_mutations = model.num_mutations()
        to_skip = m_num_mutations + 10
        expected_skipped = m_num_mutations
        expected_mutated = m_num_mutations - expected_skipped
        self._check_skip(model, to_skip, expected_skipped, expected_mutated)

    def testSequenceLengthSingleStage(self):
        for stage in self.stages:
            expected_length = self.stage_lengths[stage]
            model = StagedSequenceModel(num_mutations=100)
            model.add_stage(stage)
            while model.mutate():
                sequence = model.get_sequence()
                sequence_length = len(sequence)
                self.assertEqual(expected_length, sequence_length)

    def testSequenceLengthMultiStage(self):
        model = StagedSequenceModel(num_mutations=100)
        expected_length = 0
        for stage in self.stages:
            expected_length += self.stage_lengths[stage]
            model.add_stage(stage)
        while model.mutate():
            sequence = model.get_sequence()
            sequence_length = len(sequence)
            self.assertEqual(expected_length, sequence_length)

    def testCallbackGenerator(self):
        self.src_templates = []
        self.dst_templates = []
        self.cb_call_count = 0

        def cb_gen(src, dst):
            self.src_templates.append(src)
            self.dst_templates.append(dst)
            self.cb_call_count += 1
            return self.cb_call_count
        first_time = True

        model = StagedSequenceModel(name='uut', callback_generator=cb_gen, num_mutations=100)
        for stage in self.stages:
            model.add_stage(stage)
        while model.mutate():
            sequence = model.get_sequence()
            # this ugly piece of code is needed because we want to ignore the
            # default sequence generation
            delta = 0
            def_len = len(model._default_sequence)
            if first_time:
                self.src_templates = self.src_templates[def_len:]
                self.dst_templates = self.dst_templates[def_len:]
                self.cb_call_count -= def_len
                delta = def_len
                first_time = False
            self.assertEqual(len(sequence), self.cb_call_count)
            for i in range(len(sequence)):
                self.assertEqual(self.src_templates[i], sequence[i].src)
                self.assertEqual(self.dst_templates[i], sequence[i].dst)
                self.assertEqual(delta + i + 1, sequence[i].callback)
            self.src_templates = []
            self.dst_templates = []
            self.cb_call_count = 0

    def testFailureToTo(self):
        self.assertEqual(len(self.todo), 0)


class StageTests(unittest.TestCase):

    def setUp(self):
        self.logger = get_test_logger()
        self.logger.debug('TESTING METHOD: %s', self._testMethodName)
        self.templates = self.get_templates()
        self.todo = []

    def get_templates(self):
        res = []
        for i in range(100):
            name = 't%d' % i
            value = 'data%d' % i
            res.append(Template(name=name, fields=[String(value)]))
        return res

    def _check_strategy_length(self, selection_strategy, minl, maxl):
        stage = Stage(name='uut', selection_strategy=selection_strategy)
        templates = self.templates
        for template in templates:
            stage.add_template(template)
        for _ in range(100):
            sequence = stage.mutate()
            sequence2 = stage.get_sequence_templates()
            self.assertEqual(sequence, sequence2)
            seql = len(sequence)
            self.assertGreaterEqual(seql, minl)
            self.assertLessEqual(seql, maxl)
            for template in sequence:
                self.assertIn(template, templates)

    def testStrategyLengthRandom(self):
        minl = 1
        maxl = len(self.templates)
        selection_strategy = 'random'
        self._check_strategy_length(selection_strategy, minl, maxl)

    def testStrategyLengthRange13(self):
        minl = 1
        maxl = 3
        selection_strategy = '%d-%d' % (minl, maxl)
        self._check_strategy_length(selection_strategy, minl, maxl)

    def testStrategyLengthRange10100(self):
        minl = 10
        maxl = 100
        selection_strategy = '%d-%d' % (minl, maxl)
        self._check_strategy_length(selection_strategy, minl, maxl)

    def testStrategyLengthRangeSameMin(self):
        minl = 1
        maxl = minl
        selection_strategy = '%d-%d' % (minl, maxl)
        self._check_strategy_length(selection_strategy, minl, maxl)

    def testStrategyLengthRangeSameMax(self):
        minl = len(self.templates)
        maxl = minl
        selection_strategy = '%d-%d' % (minl, maxl)
        self._check_strategy_length(selection_strategy, minl, maxl)

    def testStrategyLengthConstant0(self):
        val = 0
        minl = val
        maxl = val
        selection_strategy = '%d' % (val)
        self._check_strategy_length(selection_strategy, minl, maxl)

    def testStrategyLengthConstant1(self):
        val = 1
        minl = val
        maxl = val
        selection_strategy = '%d' % (val)
        self._check_strategy_length(selection_strategy, minl, maxl)

    def testStrategyLengthConstantHalf(self):
        val = len(self.templates) // 2
        minl = val
        maxl = val
        selection_strategy = '%d' % (val)
        self._check_strategy_length(selection_strategy, minl, maxl)

    def testStrategyLengthConstantMax(self):
        val = len(self.templates)
        minl = val
        maxl = val
        selection_strategy = '%d' % (val)
        self._check_strategy_length(selection_strategy, minl, maxl)

    def testStrategyLengthAll(self):
        val = len(self.templates)
        minl = val
        maxl = val
        selection_strategy = 'all'
        self._check_strategy_length(selection_strategy, minl, maxl)

    def _check_exception_at_construction(self, selection_strategy, seed):
        with self.assertRaises(KittyException):
            Stage(name='uut', selection_strategy=selection_strategy, seed=seed)

    def _check_exception_at_mutate(self, templates, selection_strategy, seed):
        s = Stage(name='uut', selection_strategy=selection_strategy)
        for t in templates:
            s.add_template(t)
        with self.assertRaises(KittyException):
            s.mutate()

    def testStrategyErrorRangeMaxTooHigh(self):
        minl = 1
        maxl = len(self.templates) + 1
        selection_strategy = '%d-%d' % (minl, maxl)
        seed = 1234
        self._check_exception_at_mutate(self.templates, selection_strategy, seed)

    def testStrategyErrorRangeMinNegative(self):
        minl = -1
        maxl = 5
        selection_strategy = '%d-%d' % (minl, maxl)
        seed = 1234
        self._check_exception_at_construction(selection_strategy, seed)

    def testStrategyErrorRangeMaxNegative(self):
        minl = 1
        maxl = -5
        selection_strategy = '%d-%d' % (minl, maxl)
        seed = 1234
        self._check_exception_at_construction(selection_strategy, seed)

    def testStrategyErrorRangeMaxLowerThanMin(self):
        minl = 5
        maxl = 1
        selection_strategy = '%d-%d' % (minl, maxl)
        seed = 1234
        self._check_exception_at_construction(selection_strategy, seed)

    def testStrategyErrorUnknown(self):
        unknown_strategies = ['single', 'true', 'rand', '++', '0x13']
        for strategy in unknown_strategies:
            self.logger.info('testing unknown strategy: %s' % strategy)
            self._check_exception_at_construction(strategy, 1234)

    def _check_randomness(self, templates, strategy):
        '''Check that different sequences are generated'''
        stage = Stage(name='uut', selection_strategy=strategy, seed=1111)
        for template in templates:
            stage.add_template(template)
        sequences = set()
        iterations = 100
        for _ in range(iterations):
            sequence = tuple(stage.mutate())
            sequences.add(sequence)
        self.assertGreater(len(sequences), iterations // 2)

    @not_absolute
    def testRandomSelectionRandom(self):
        self._check_randomness(self.templates, 'random')

    @not_absolute
    def testRandomSelectionRange510(self):
        self._check_randomness(self.templates, '5-10')

    @not_absolute
    def testRandomSelectionRange17(self):
        self._check_randomness(self.templates, '1-7')

    @not_absolute
    def testRandomStrategyRandomLength(self):
        stage = Stage(name='uut', selection_strategy='random', seed=1111)
        for template in self.templates:
            stage.add_template(template)
        sequences = set()
        iterations = 100
        for _ in range(iterations):
            sequence = stage.mutate()
            sequences.add(len(sequence))
        self.assertGreater(len(sequences), iterations // 8)

    def _check_same_seed(self, strategy):
        seed = 1111
        stage1 = Stage(name='uut1', selection_strategy=strategy, seed=seed)
        stage2 = Stage(name='uut2', selection_strategy=strategy, seed=seed)
        for template in self.templates:
            stage1.add_template(template)
            stage2.add_template(template)
        for _ in range(1000):
            self.assertEqual(stage1.mutate(), stage2.mutate())

    def _check_different_seed(self, strategy):
        seed1 = 1111
        seed2 = 1112
        stage1 = Stage(name='uut1', selection_strategy=strategy, seed=seed1)
        stage2 = Stage(name='uut2', selection_strategy=strategy, seed=seed2)
        for template in self.templates:
            stage1.add_template(template)
            stage2.add_template(template)
        seqs1 = [stage1.mutate() for i in range(10)]
        seqs2 = [stage2.mutate() for i in range(10)]
        self.assertNotEqual(seqs1, seqs2)

    def testSameSeedRandom(self):
        self._check_same_seed('random')

    def testSameSeedAll(self):
        self._check_same_seed('all')

    def testSameSeedRange17(self):
        self._check_same_seed('1-7')

    def testSameSeedRange1050(self):
        self._check_same_seed('10-50')

    def testSameSeedConst5(self):
        self._check_same_seed('5')

    def testSameSeedConst20(self):
        self._check_same_seed('20')

    def testDifferentSeedRandom(self):
        self._check_different_seed('random')

    def testDifferentSeedAll(self):
        self._check_different_seed('all')

    def testDifferentSeedRange17(self):
        self._check_different_seed('1-7')

    def testDifferentSeedRange1050(self):
        self._check_different_seed('10-50')

    def testDifferentSeedConst5(self):
        self._check_different_seed('5')

    def testDifferentSeedConst20(self):
        self._check_different_seed('20')

    def testFailureToTo(self):
        self.assertEqual(len(self.todo), 0)


class RandomSequenceModelTests(unittest.TestCase):

    def setUp(self):
        self.logger = get_test_logger()
        self.logger.debug('TESTING METHOD: %s', self._testMethodName)
        self.model = RandomSequenceModel()
        self.templates = self.get_templates()
        self.todo = []

    def get_templates(self):
        res = []
        for i in range(20):
            name = 't%d' % i
            value = 'd%d' % i
            res.append(Template(name=name, fields=[String(value)]))
        return res

    def testNumMutations(self):
        num_mutation_list = [0, 1, 500, 1000, 10000]
        for expected_num_mutations in num_mutation_list:
            model = RandomSequenceModel(num_mutations=expected_num_mutations)
            for template in self.templates:
                model.add_template(template)
            m_num_mutations = model.num_mutations()
            self.assertEqual(expected_num_mutations, m_num_mutations)
            actual_mutations = 0
            while model.mutate():
                actual_mutations += 1
            self.assertEqual(expected_num_mutations, actual_mutations)

    def _check_skip(self, model, to_skip, expected_skipped, expected_mutated):
        skipped = model.skip(to_skip)
        self.assertEqual(expected_skipped, skipped)
        mutated = 0
        while model.mutate():
            mutated += 1
        self.assertEqual(expected_mutated, mutated)

    def testSkipZero(self):
        model = RandomSequenceModel(num_mutations=120)
        for template in self.templates:
            model.add_template(template)
        m_num_mutations = model.num_mutations()
        to_skip = 0
        expected_skipped = to_skip
        expected_mutated = m_num_mutations - expected_skipped
        self._check_skip(model, to_skip, expected_skipped, expected_mutated)

    def testSkipHalf(self):
        model = RandomSequenceModel(num_mutations=120)
        for template in self.templates:
            model.add_template(template)
        m_num_mutations = model.num_mutations()
        to_skip = m_num_mutations // 2
        expected_skipped = to_skip
        expected_mutated = m_num_mutations - expected_skipped
        self._check_skip(model, to_skip, expected_skipped, expected_mutated)

    def testSkipExact(self):
        model = RandomSequenceModel(num_mutations=120)
        for template in self.templates:
            model.add_template(template)
        m_num_mutations = model.num_mutations()
        to_skip = m_num_mutations
        expected_skipped = to_skip
        expected_mutated = m_num_mutations - expected_skipped
        self._check_skip(model, to_skip, expected_skipped, expected_mutated)

    def testSkipTooMuch(self):
        model = RandomSequenceModel(num_mutations=120)
        for template in self.templates:
            model.add_template(template)
        m_num_mutations = model.num_mutations()
        to_skip = m_num_mutations + 10
        expected_skipped = m_num_mutations
        expected_mutated = m_num_mutations - expected_skipped
        self._check_skip(model, to_skip, expected_skipped, expected_mutated)

    def testSameSeed(self):
        seed = 1111
        model1 = RandomSequenceModel(seed=seed, max_sequence=20)
        model2 = RandomSequenceModel(seed=seed, max_sequence=20)
        for template in self.templates:
            model1.add_template(template)
            model2.add_template(template)
        for _ in range(1000):
            self.assertEqual(model1.mutate(), model2.mutate())

    def testDifferentSeed(self):
        seed1 = 1111
        seed2 = 1112
        model1 = RandomSequenceModel(seed=seed1, max_sequence=20)
        model2 = RandomSequenceModel(seed=seed2, max_sequence=20)
        for template in self.templates:
            model1.add_template(template)
            model2.add_template(template)
        seqs1 = []
        seqs2 = []
        while model1.mutate() and model2.mutate():
            seqs1.append(model1.get_sequence())
            seqs2.append(model2.get_sequence())
        self.assertNotEqual(seqs1, seqs2)

    @not_absolute
    def testRandomLength(self):
        model = RandomSequenceModel(name='uut', seed=1111, max_sequence=20)
        for template in self.templates:
            model.add_template(template)
        sequences = set()
        iterations = 100
        for _ in range(iterations):
            model.mutate()
            sequence = model.get_sequence()
            sequences.add(len(sequence))
        self.assertGreater(len(sequences), iterations // 8)

    def testLengthNotOverflow(self):
        max_sequence = 5
        model = RandomSequenceModel(name='uut', seed=1111, max_sequence=5)
        for template in self.templates:
            model.add_template(template)
        while model.mutate():
            sequence = model.get_sequence()
            self.assertLessEqual(len(sequence), max_sequence)

    def testCallbackGenerator(self):
        self.src_templates = []
        self.dst_templates = []
        self.cb_call_count = 0

        def cb_gen(src, dst):
            self.src_templates.append(src)
            self.dst_templates.append(dst)
            self.cb_call_count += 1
            return self.cb_call_count
        first_time = True

        model = RandomSequenceModel(name='uut', callback_generator=cb_gen, num_mutations=100, max_sequence=13)
        for template in self.templates:
            model.add_template(template)
        while model.mutate():
            # this ugly piece of code is needed because we want to ignore the
            # default sequence generation
            delta = 0
            def_len = len(model._default_sequence)
            if first_time:
                self.src_templates = self.src_templates[def_len:]
                self.dst_templates = self.dst_templates[def_len:]
                self.cb_call_count -= def_len
                delta = def_len
                first_time = False
            sequence = model.get_sequence()
            self.assertEqual(len(sequence), self.cb_call_count)
            for i in range(len(sequence)):
                self.assertEqual(self.src_templates[i], sequence[i].src)
                self.assertEqual(self.dst_templates[i], sequence[i].dst)
                self.assertEqual(delta + i + 1, sequence[i].callback)
            self.src_templates = []
            self.dst_templates = []
            self.cb_call_count = 0

    def testFailureToTo(self):
        self.assertEqual(len(self.todo), 0)


if __name__ == '__main__':
    if not os.path.exists('logs'):
        os.mkdir('logs')
    unittest.main(verbosity=2)
