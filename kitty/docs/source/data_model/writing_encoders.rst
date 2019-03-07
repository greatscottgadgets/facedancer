Writing Encoders
================

A Little Bit About Encoders
---------------------------

Each field in the data model has two main properties:

1. The **value** of the field - for example, a number may have the value 1, 2 or -1532 and so on.
2. The **representation** of the field - for example, a number with the value 123 may be represented as decimal (``123``), hexadecimal (``7B``) or a 32 bit little endian (``'\x7b\x00\x00\x00'``) and so on.

The **value** of the field is decided by the field itself, using the default value or one of the field's mutations.
The **representation** of the field is decided by it's encoder.

Kitty has a few encoder classes, used to encode integer values, floats, strings and ``Bits`` objects.
You can see a list of available encoder classes in the `Data Model Syntax <big_list_of_fields.html#encoders>`__ documentation.

Kitty also provides many encoder objects that may be used directly in your model,
such as ``ENC_INT_BE`` to encode an integer as a big endian,
or ``ENC_STR_BASE64`` to encoder a string in base64.
Since most encoders have no state, the same object may be used by many fields without issue,
thus the use of a global encoder object makes sense.

However, Kitty doesn't have any possible encoding,
and so you might be required to implement your own encoder from time to time.

Implementing Your Own Encoder
-----------------------------

Example 1 - Aligned String
^^^^^^^^^^^^^^^^^^^^^^^^^^

Let's say that you have a :class:`~kitty.model.low_level.field.String` field that must be 4 bytes aligned,
and you decide that it makes no sense to have mutations of this field that are not aligned.

Since the alignment is only related to the representation of the string,
you should probably just encode it as a 4 byte aligned string,
meaning, implement an encoder that encodes the string with padding when needed.

There are several ways to implement such an encoder. Here are two of them.

Straight Forward Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We'll start with a simple one, which might be just enough in some cases,
and will make it more robust.
Since we encode a string, we need to inherit from :class:`~kitty.model.low_level.encoder.StrEncoder`
and override its :func:`~kitty.model.low_level.encoder.StrEncoder.encode` method.
This method receive a string as argument, and returns an encoded string as a ``Bits`` object.

::

    class AlignedStrEncoder(StrEncoder):

        def encode(self, value):
            pad_len = (4 - len(value) % 4) % 4
            new_value = value + '\x00' * pad_len
            return Bits(bytes=new_value)

Then, we can instantiate it:

::

    ENC_STR_ALIGN = AlignedStrEncoder()

And use it multiple times:

::

    Template(name='two aligned strings', fields=[
        String('foo', encoder=ENC_STR_ALIGN),
        String('bar', encoder=ENC_STR_ALIGN),
    ])


Using :class:`~kitty.model.low_level.encoder.StrFuncEncoder`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can also implement it by passing the encoding function
to the constructor of ``StrFuncEncoder``

::

    def align_string(value):
        pad_len = (4 - len(value) % 4) % 4
        new_value = value + '\x00' * pad_len
        return Bits(bytes=new_value)

    ENC_STR_ALIGN = StrFuncEncoder(align_string)


Generic Implementation
~~~~~~~~~~~~~~~~~~~~~~

We might want to create a generic aligned string encoder class
and pass the alignment size as a parameter.
In this case, we need to override the ``__init__`` function:

::

    class AlignedStrEncoder(StrEncoder):

        def __init__(self, pad_size, pad_char='\x00'):
            self._pad_size = pad_size
            self._pad_char = pad_char

        def encode(self, value):
            pad_len = (self._pad_size - len(value) % self._pad_size) % self._pad_size
            new_value = value + self._pad_char * pad_len
            return Bits(bytes=new_value)

Then, we can instantiate it with different values:

::

    ENC_STR_ALIGN4 = AlignedStrEncoder(4)
    ENC_STR_ALIGN8 = AlignedStrEncoder(8)


Example 2 - Reversed Bits
^^^^^^^^^^^^^^^^^^^^^^^^^

The ``encode()`` method returns a ``Bits`` object (from the ``bitstring`` package).
The main difference between the big encoder types is the (type of) value that their
``encode()`` method accepts.
In the first example, the it accepted a string,
in the case of ``BitsEncoder``, it accepts a ``Bits`` object.

The encoder below encodes the bits in a reversed order,
e.g. if it receives the bits ``10101100`` it will return ``00110101``.

There two main ways to implement such an encoder.

Using :class:`~kitty.model.low_level.encoder.BitsFuncEncoder`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As with :class:`~kitty.model.low_level.encoder.StrFuncEncoder` in the previous example,
``BitsFuncEncoder`` allows you to just pass an ``encode()`` function to the constructor,
so you don't need to create a new class and implement its ``encode`` method.
This comes handy from time to time.

::

    def reverse_bits(value):
        return value[::-1]

    ENC_BITS_REVERSED = BitsFuncEncoder(reverse_bits)

Subclassing :class:`~kitty.model.low_level.encoder.BitsEncoder`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

However, you may subclass ``BitsEncoder`` directly.

::

    class ReversedBitsEncoder(BitsEncoder):

        def encoder(value):
            return value[::-1]

And instantiate it

::

    ENC_BITS_REVERSED = ReversedBitsEncoder()

