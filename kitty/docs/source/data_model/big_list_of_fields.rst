Data Model Syntax
=================

A big part of generation based fuzzing is the data modeling.
It provides guidance to the fuzzer on how the data is supposed to be structured.
This allows the fuzzer to perform a more precise and faster fuzzing,
and to keep the state of the payload as similar as possible to a valid while performing mutations on very specific fields.

This chapter is composed of three parts.
We start by listing the :ref:`available fields <fields>`,
these fields compose kitty's syntax.
After that, we list the :ref:`available encoders <encoders>`.
The :ref:`last part<examples>` of this chapter provides examples on
how to use the fields, containers and encoders
that are listed in the first two part
to compose a full template.



.. _fields:

Fields
------

A basic overview of the data model can be found in the :doc:`overview`,
and you can also take a look at the :doc:`API reference<../kitty.model.low_level>`.

There are a few types of fields in Kitty's data model, and all of them are derived from :class:`~kitty.model.low_level.field.BaseField`.

- :ref:`atomic-fields`
- :ref:`calculated-fields`
- :ref:`containers`
- :ref:`mutation-fields`

The field type defines the type of value that will be rendered by this field,
as well of the type of mutations that will be performed.
The type of field instructs the fuzzer *what* data to render in the payload,
but not *how* to render it. For that, we have encoders (see :ref:`encoders`).

:example:

    If we want to fuzz an integer, we will use a field like ``UInt16``,
    which is used to represent an unsigned integer number with values
    between 0 and 65535 ``(2 ** 16 - 1)``.

    This number may be rendered as Little endian binary or a string of ASCII values,
    or something else.
    
    The use of ``UInt16`` provides the type of the value,
    but an encoder will encode it in the approriate "encoding" during its generation.

.. _atomic-fields:

Atomic Fields
~~~~~~~~~~~~~

The atomic fields are the very basic building blocks of a data model.
Each of this fields is self-contained and discrete.

The following atomic fields are available in Kitty (some of them are aliases for other fields):

- :func:`~kitty.model.low_level.field.BitField`
    :func:`~kitty.model.low_level.aliases.U8`
    :func:`~kitty.model.low_level.aliases.UInt8`
    :func:`~kitty.model.low_level.aliases.BE8`
    :func:`~kitty.model.low_level.aliases.LE8`
    :func:`~kitty.model.low_level.aliases.Byte`
    :func:`~kitty.model.low_level.aliases.U16`
    :func:`~kitty.model.low_level.aliases.UInt16`
    :func:`~kitty.model.low_level.aliases.Word`
    :func:`~kitty.model.low_level.aliases.BE16`
    :func:`~kitty.model.low_level.aliases.WordBE`
    :func:`~kitty.model.low_level.aliases.LE16`
    :func:`~kitty.model.low_level.aliases.WordLE`
    :func:`~kitty.model.low_level.aliases.S16`
    :func:`~kitty.model.low_level.aliases.SInt16`
    :func:`~kitty.model.low_level.aliases.U32`
    :func:`~kitty.model.low_level.aliases.UInt32`
    :func:`~kitty.model.low_level.aliases.Dword`
    :func:`~kitty.model.low_level.aliases.BE32`
    :func:`~kitty.model.low_level.aliases.DwordBE`
    :func:`~kitty.model.low_level.aliases.LE32`
    :func:`~kitty.model.low_level.aliases.DwordLE`
    :func:`~kitty.model.low_level.aliases.S32`
    :func:`~kitty.model.low_level.aliases.SInt32`
    :func:`~kitty.model.low_level.aliases.U64`
    :func:`~kitty.model.low_level.aliases.UInt64`
    :func:`~kitty.model.low_level.aliases.Qword`
    :func:`~kitty.model.low_level.aliases.BE64`
    :func:`~kitty.model.low_level.aliases.QwordBE`
    :func:`~kitty.model.low_level.aliases.LE64`
    :func:`~kitty.model.low_level.aliases.QwordLE`
    :func:`~kitty.model.low_level.aliases.S64`
    :func:`~kitty.model.low_level.aliases.SInt64`
- :class:`~kitty.model.low_level.field.Delimiter`
- :class:`~kitty.model.low_level.field.Dynamic`
- :class:`~kitty.model.low_level.field.Float`
- :class:`~kitty.model.low_level.field.Group`
- :class:`~kitty.model.low_level.field.RandomBits`
- :class:`~kitty.model.low_level.field.RandomBytes`
- :class:`~kitty.model.low_level.field.Static`
- :class:`~kitty.model.low_level.field.String`

.. _calculated-fields:

Calculated (dependant) Fields
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Calculated fields are fields that their value is calculated
from properties that are outside of their scope by default,
for example, the length or the checksum of another fields.

These fields give Kitty's syntax much of its power.
It allows the user to get into deeper layer of the parsing.

These fields can be fuzzed as well, but when they are not fuzzed,
they will be calculated each time,
to ensure that they render into a valid value.

The following calculated fields are available in Kitty (again, some of them are aliases for other fields):

- :class:`~kitty.model.low_level.calculated.AbsoluteOffset`
- :class:`~kitty.model.low_level.calculated.Checksum`
- :class:`~kitty.model.low_level.calculated.Clone`
- :class:`~kitty.model.low_level.calculated.ElementCount`
- :class:`~kitty.model.low_level.calculated.Hash`
    :class:`~kitty.model.low_level.aliases.Md5`
    :class:`~kitty.model.low_level.aliases.Sha1`
    :class:`~kitty.model.low_level.aliases.Sha224`
    :class:`~kitty.model.low_level.aliases.Sha256`
    :class:`~kitty.model.low_level.aliases.Sha384`
    :class:`~kitty.model.low_level.aliases.Sha512`
- :class:`~kitty.model.low_level.calculated.IndexOf`
- :class:`~kitty.model.low_level.calculated.Offset`
- :class:`~kitty.model.low_level.calculated.Size`
    :class:`~kitty.model.low_level.aliases.SizeInBytes`

.. _containers:

Containers
~~~~~~~~~~

Containers, as is pretty obvious from their name, contain other fields.
There is no limit on how many fields a container can hold,
nor on the nesting level of containers.

Containers can be used to perform encoding on multiple fields at once,
or to use some property of multiple rendered fields to perform some calculation.
But the most important property of containers, IMHO,
is the logical separation and grouping of units in the model.

In general, containers treat the contained field in the order they were added
and in most cases will mutate each of the contained fields when in turn.
However, in addition to the mutations of the internal fields,
some container may add some mutations that are a property
of the container itself
(although they depend on the value of the contained fields)

The following containers are available in Kitty:

- :class:`~kitty.model.low_level.container.Conditional`
    :class:`~kitty.model.low_level.container.If`
    :class:`~kitty.model.low_level.container.IfNot`
- :class:`~kitty.model.low_level.container.Container`
- :class:`~kitty.model.low_level.container.ForEach`
- :class:`~kitty.model.low_level.container_mutator.List`
- :class:`~kitty.model.low_level.container.Meta`
- :class:`~kitty.model.low_level.container.OneOf`
- :class:`~kitty.model.low_level.container.Pad`
- :class:`~kitty.model.low_level.container.Repeat`
- :class:`~kitty.model.low_level.container.Switch`
- :class:`~kitty.model.low_level.container.TakeFrom`
- :class:`~kitty.model.low_level.container.Template`
    :class:`~kitty.model.low_level.container.PseudoTemplate`
- :class:`~kitty.model.low_level.container.Trunc`

.. _mutation-fields:

Mutation Based Fields
~~~~~~~~~~~~~~~~~~~~~

While Kitty uses a data model,
and expects the user to be familiar with the structure of the payload,
in some cases the user might not have this information,
only a sample payload.

In this cases, a mutation fuzzing might come in handy, and the Mutation based fields can be used to perform a tests on the target
without an accurate data model.

some of the fields are wrappers around other fields, specifically,
:class:`~kitty.model.low_level.mutated_field.MutableField`
is a combination of all other mutation based fields.


The following mutation-based fields are available in Kitty:

- :class:`~kitty.model.low_level.mutated_field.BitFlip`
- :class:`~kitty.model.low_level.mutated_field.BitFlips`
- :class:`~kitty.model.low_level.mutated_field.BlockDuplicate`
- :class:`~kitty.model.low_level.mutated_field.BlockDuplicates`
- :class:`~kitty.model.low_level.mutated_field.BlockOperation`
- :class:`~kitty.model.low_level.mutated_field.BlockRemove`
- :class:`~kitty.model.low_level.mutated_field.BlockSet`
- :class:`~kitty.model.low_level.mutated_field.ByteFlip`
- :class:`~kitty.model.low_level.mutated_field.ByteFlips`
- :class:`~kitty.model.low_level.mutated_field.MutableField`

.. _encoders:

Encoders
--------

The encoders receive data from the field they are assigned to,
and return a sequence of bits, which is the rendered data.

There are 4 types of encoders:

- Encoders of strings (python2.7's str), receiving a string and returning Bits.
- Encoders of Bits, receiving Bits object and returning Bits.
- Encoders of numbers, receiving int value, length in bits and sign and returning Bits.
- Encoders of floating point numbers, receiving float and returning Bits.

Encoders are objects, but since most common encoders are stateless,
and don't change state, the same instance can be used in multple fields,
kitty provides many default instances of encoders that can be used directly.

These instances are listed in the :doc:`API reference<../kitty.model.low_level.encoder>`.

- :class:`~kitty.model.low_level.encoder.BitFieldEncoder`

    - :class:`~kitty.model.low_level.encoder.BitFieldAsciiEncoder`
    - :class:`~kitty.model.low_level.encoder.BitFieldBinEncoder`
    - :class:`~kitty.model.low_level.encoder.BitFieldMultiByteEncoder`

- :class:`~kitty.model.low_level.encoder.BitsEncoder`

    - :class:`~kitty.model.low_level.encoder.ByteAlignedBitsEncoder`
    - :class:`~kitty.model.low_level.encoder.ReverseBitsEncoder`
    - :class:`~kitty.model.low_level.encoder.BitsFuncEncoder`

- :class:`~kitty.model.low_level.encoder.StrEncoder`

    - :class:`~kitty.model.low_level.encoder.StrBase64NoNewLineEncoder`
    - :class:`~kitty.model.low_level.encoder.StrEncodeEncoder`
    - :class:`~kitty.model.low_level.encoder.StrEncoderWrapper`
    - :class:`~kitty.model.low_level.encoder.StrFuncEncoder`
    - :class:`~kitty.model.low_level.encoder.StrNullTerminatedEncoder`

- :class:`~kitty.model.low_level.encoder.FloatEncoder`

    - :class:`~kitty.model.low_level.encoder.FloatAsciiEncoder`
    - :class:`~kitty.model.low_level.encoder.FloatBinEncoder`

.. _examples:

Using the syntax
----------------

In this part, we'll take a look at a few examples on how to use
Kitty's data modeling syntax to model some data or protocol.

It's important to note that Kitty has no capability of modeling
the data automatically.
This is really out-of-scope, although,
if you developed a tool that can infer the structure of a message
from some (or many) samples, or if you know of such a tool,
we'd really like to know about that.

Anyway... Kitty's data model syntax is inspired by the syntax of
`Construct <https://construct.readthedocs.io/en/latest/>`_.
In the sense that the entire model of a payload (e.g. template)
can be constructed in a single -- nested -- constructur.
Using the standard alignment of python,
this results in a very readable data model,
although it is 100% python code.

Unlike Construct,
the resulted data model is not designed to pacrse payloads
or be modified from outside (although it is possible to a certain level),
instead, it is designed to generate mutations internally,
(when ``mutate()`` is called)
and provide the resulted payloads (when ``render()`` is called).

Example 1 - Sized String
~~~~~~~~~~~~~~~~~~~~~~~~

The following template describes an ascii string (not null terminated),
prepended by a 16bit int that holds its size (in bytes):

    ::

        sized_string = Template(name='sized string', fields=[
            SizeInBytes(name='size', sized_field='the string', length=16),
            String(name='the string', value='')
        ])

Example 2 - Count Elements in a List
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following template describe a List
of 32bit little endian encoded integers,
preprended by the number of element in the list
(field of 16bit, little endian encoded).

    ::

        counted_list = Template(name='counted list', fields=[
            ElementCount(name='element count', depends_on='the list', length=16, encoder=ENC_INT_LE),
            List(name='the list', fields=[
                LE32(name='element 1', value=0x00010203),
                LE32(name='element 2', value=0x0a050607),
                LE32(name='element 3', value=0x08090a0b),
                LE32(name='element 4', value=0x0c0d0e0f),
                LE32(name='element 5', value=0x10111213),
                LE32(name='element 6', value=0x1a151617),
                LE32(name='element 7', value=0x18191a1b),
                LE32(name='element 8', value=0x1c1d1e1f),
            ])
        ])

Here's the default rendered payload (hex encoded),
see how it matchs the description

    ::

        0800030201000706050a0b0a09080f0e0d0c131211101716151a1b1a19181f1e1d1c

        0800 -> element count: 8 (16 bits, little endian encoded)
        03020100 -> element 1: 0x00010203 (32 bits, little endian encoded)
        0706050a -> element 2: 0x0a050607 (32 bits, little endian encoded)
        0b0a0908 -> element 3: 0x08090a0b (32 bits, little endian encoded)
        0f0e0d0c -> element 4: 0x0c0d0e0f (32 bits, little endian encoded)
        13121110 -> element 5: 0x10111213 (32 bits, little endian encoded)
        1716151a -> element 6: 0x1a151617 (32 bits, little endian encoded)
        1b1a1918 -> element 7: 0x18191a1b (32 bits, little endian encoded)
        1f1e1d1c -> element 8: 0x1c1d1e1f (32 bits, little endian encoded)

        
Example 3 - Base64 Encoded Container
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As mentioned, a container may be encoded as a whole,
this comes quite handy in HTTP authorization,
where the clients sends the username and password as:
``base64encode(USERNAME:PASSWORD)``.
Of course, encoding each string (``USERNAME``, ``:`` and ``PASSWORD``)
separately will result in a different base64 string
then if they were encoded together.

    ::

        http_user_pass = Container(
            name='userpass header',
            fields=[
                String(name='username', value='some user'),
                String(name='delimiter', value=':'),
                String(name='password', value='some password')
            ],
            encoder=ENC_BITS_BASE64_NO_NL
        )

The default result of such a container is

    ::

        'c29tZSB1c2VyOnNvbWUgcGFzc3dvcmQ='

Which is the base64 encoded version of

    ::

        'some user:some password'
