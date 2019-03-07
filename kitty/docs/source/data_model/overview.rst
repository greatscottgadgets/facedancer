Data Model Overview
===================

As described in the overview, Kitty is by default a generation-based
fuzzer. This means that a model should be created to represent the data
exchanged in the fuzzed protocol.

On the high level, we describe and fuzz different sequences of messages,
this allows building fuzzing scenarios that are valid until a specific
stage but also to fuzz the order of messages as well.

Low Level Model
---------------

At the low level, there is a single payload, constructed from multiple
fields. Those fields can be encoded, dependant on other fields, be
renderened conditionaly and combined with other fields into larger
logical units. The top unit of the logical units is Template, and
Template is the only low-level interface to the high-level of the data
model.

A full documentation of the low level data model can be found in the API
:doc:`reference <../kitty.model.low_level>`.

A full list of the fields in the Kitty data model syntax can be found in the :doc:`big_list_of_fields`.

High Level Model
----------------

The high level model describe how a sequence of messages (Templates)
looks like to the fuzzer. There are two main models for this part,
:class:`~kitty.model.high_level.graph.GraphModel` and :class:`~kitty.model.high_level.staged_sequence.StagedSequenceModel`. An additional model -
:class:`~kitty.model.high_level.random_sequence.RandomSequenceModel` is a naive case of :class:`~kitty.model.high_level.staged_sequence.StagedSequenceModel` and is
more convenient, when the order of messages really doesn't matter.

During the fuzzing session, the fuzzer queries the data model for a
sequence to transmit. The data model chooses the next sequence according
to its strategy and perform internal mutations if needed.
