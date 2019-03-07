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
Model with a graph structure, all paths in the graph will be fuzzed.
The last node in each path will be mutated until exhaustion.
'''
from kitty.model.high_level.base import BaseModel
from kitty.model.high_level.base import Connection
from kitty.core import KittyException, khash


class GraphModel(BaseModel):
    '''
    The GraphModel is built of a simple digraph, where the nodes are templates, and on each edge there's a callback function.
    It will provide sequences of edges from this graph, always starting from the root (dummy) node,
    where the last template in the sequence (the destination of the last edge) is mutated.
    As such the main target of the GraphModel is to fuzz the handling of the fields in a message.

    Assuming we have the templates A, B, C and D and we want to fuzz all templates, but we know that in order to make
    an impact in fuzzing template D, we first need to send A, then B or C, and only then D, e.g. we have the following
    template graph:

    ::

          /==> B
         /      \\
        A        +==> D
         \\      /
          \\==> C

    Which translate to the following sequences (`*` - mutated template):

    ::

        A*
        A -> B*
        A -> B -> D*
        A -> C*
        A -> C -> D*

    Such a model will be written in Kitty like this:

    :example:

        ::

            model = GraphModel('MyGraphModel')
            model.connect(A)
            model.connect(A, B)
            model.connect(B, D)
            model.connect(A, C)
            model.connect(C, D)

    .. note:: Make sure there are no loops in your model!!

    The callback argument of connect allows monitoring and maintainance during a fuzzing test.

    :example:

        ::

            def log_if_empty_response(fuzzer, edge, response):
                if not response:
                    logger.error('Got an empty response for request %s' % edge.src.get_name())

            model.connect(A, B, log_if_empty_response)
    '''

    def __init__(self, name='GraphModel'):
        '''
        :param name: name for this model
        '''
        super(GraphModel, self).__init__(name)
        self._root = self.ROOT_NODE
        self._root_id = self._root.hash()
        self._graph = {}
        self._graph[self._root_id] = []
        self._sequence_idx = -1
        self._current_node = None

    def _get_ready(self):
        if not self._ready:
            self.check_loops_in_grpah()
            num = 0
            self._sequences = self._get_sequences()
            assert len(self._sequences)
            for sequence in self._sequences:
                num += sequence[-1].dst.num_mutations()
            self._num_mutations = num
            self._ready = True
            self._update_state(0)

    def _get_node(self):
        return self._current_node

    def _update_state(self, idx):
        if self._sequence_idx != idx:
            self._sequence_idx = idx
            self._sequence = self._sequences[self._sequence_idx]
            self._current_node = self._sequence[-1].dst
            if self._notification_handler:
                self._notification_handler.handle_stage_changed(self)

    def skip(self, count):
        self._get_ready()
        skipped = 0
        for i in range(self._sequence_idx, len(self._sequences)):
            if skipped == count:
                break
            self._update_state(i)
            node = self._get_node()
            skipped += node.skip(count - skipped)
            if skipped > count:
                raise KittyException('Internal error in skip. skipped (%#x) > count (%#x)' % (skipped, count))
            elif skipped < count:
                node.reset()
        self._current_index += skipped
        return skipped

    def _mutate(self):
        for i in range(self._sequence_idx, len(self._sequences)):
            self._update_state(i)
            node = self._get_node()
            if node.mutate():
                return
            node.reset()

    def connect(self, src, dst=None, callback=None):
        '''
        :param src: source node, if dst is None it will be destination node and the root (dummy) node will be source
        :param dst: destination node (default: None)
        :type callback: func(fuzzer, edge, response) -> None
        :param callback: a function to be called after the response for src received and before dst is sent
        '''
        assert src
        if dst is None:
            dst = src
            src = self._root
        src_id = src.hash()
        dst_id = dst.hash()
        if src_id not in self._graph:
            raise KittyException('source node id (%#x) (%s) is not in the node list ' % (src_id, src))
        self._graph[src_id].append(Connection(src, dst, callback))
        if dst_id not in self._graph:
            self._graph[dst_id] = []

    def _get_sequences(self, sequence=[]):
        sequences = []
        node = self._root if len(sequence) == 0 else sequence[-1].dst
        for conn in self._graph[node.hash()]:
            new_sequence = sequence + [conn]
            sequences.append(new_sequence)
            sequences.extend(self._get_sequences(new_sequence))
        return sequences

    def hash(self):
        hashed = super(GraphModel, self).hash()
        skeys = sorted(self._graph.keys())
        for key in skeys:
            for conn in self._graph[key]:
                t_hashed = conn.dst.hash()
                self.logger.debug('hash of template %s is %s' % (conn.dst.get_name(), t_hashed))
                hashed = khash(hashed, t_hashed)
        self.logger.debug('hash of model is %s' % hashed)
        return hashed

    def get_model_info(self):
        info = {}
        info['model_name'] = self.name
        info['sequence_count'] = len(self._sequences)
        return info

    def get_test_info(self):
        info = super(GraphModel, self).get_test_info()
        node_info = self._get_node().get_info()
        info['node'] = node_info
        info['sequence']['index'] = self._sequence_idx
        return info

    def get_template_info(self):
        '''
        :return: dictionary of information regarding the current template
        '''
        node = self._get_node()
        return node.get_structure()

    def check_loops_in_grpah(self, current=None, visited=[]):
        '''
        :param current: current node to check if visited
        :param visited: list of visited fields
        :raise: KittyException if loop found
        '''
        if current in visited:
            path = ' -> '.join(v.get_name() for v in (visited + [current]))
            raise KittyException('loop detected in model: %s' % path)
        current = current if current else self._root
        for conn in self._graph[current.hash()]:
            self.check_loops_in_grpah(conn.dst, visited + [conn.src])

    def get_stages(self):
        '''
        :return: dictionary of information regarding the stages in the fuzzing session

        .. note::

            structure: { current: ['stage1', 'stage2', 'stage3'], 'stages': {'source1': ['dest1', 'dest2'], 'source2': ['dest1', 'dest3']}}
        '''
        sequence = self.get_sequence()
        stages = {}
        for seq in self._sequences:
            for e in seq:
                if e.src.get_name() not in stages:
                    stages[e.src.get_name()] = []
                if e.dst.get_name() not in stages[e.src.get_name()]:
                    stages[e.src.get_name()].append(e.dst.get_name())
        return {
            'current': [e.dst.get_name() for e in sequence],
            'stages': stages
        }
