Writing a ServerTarget Class
============================

Role
----

A Target object has two roles in a fuzzing session:

- Handle the actual communication with the target (victim).
- Manage and query the Controller and Monitors.

This means that the Target object, in general,
doesn't monitor the behavior of the target,
nor does it start / stop the target.
It only sends the payloads to the target,
and -- if needed -- waits for response from the target.


This Tutorial
-------------

In this tutorial, we will implement a ServerTarget class.
This target will allow the fuzzer to send and receive data
over a serial (UART) data channel.

Hopefully, by the end of the tutorial
you will feel comfortable writing your own controller.


Let's Begin
-----------

Target Flow
~~~~~~~~~~~

The behavior of our target will look like that:

1. Open and configure serial connection
2. For each test
    1. For each payload
        1. Send payloads
        2. Receive response
3. Close serial connection

Overall, not too complicated.

Functions
~~~~~~~~~

Kitty's ``Target`` API provides hooks for performing actions
in different points in time.
We will write implementation for each parts of the flow above.

Part 1 - Open and configure serial connection
+++++++++++++++++++++++++++++++++++++++++++++

There are two functions we need to implement in this part.
``__init__`` - to initialize the Target object,
and ``setup`` - which will be called when starting the session.

::

    import serial
    from kitty.targets import ServerTarget

    class SerialTarget(ServerTarget):
        
        def __init__(self, dev_name, baudrate=115200, name='SerialTarget', logger=None, expect_response=False):
            super(SerialTarget, self).__init__(name, logger, expect_response)
            self.dev_name = dev_name
            self.baudrate = baudrate
            self.serial = None
            # we set this timeout to simplify the reads
            self.timeout = 2

Since each class in the hierarchy of ``Target`` perform some important
initialization in ``setup``, it is important to call the super function.

::

        def setup(self):
            if self.serial:
                self.serial.close()
            self.serial = serial.Serial(self.dev_name, self.baudrate)
            self.serial.timeout = self.timeout
            super(SerialTarget, self).setup()

Part 2.1.1 - Send payload
+++++++++++++++++++++++++

Each test might have multiple payloads that should be sent in sequence,
the function ``_send_to_target``
is expected to send the payload to the target,
but not to perform the mutations on it.
The payloads that are passed to this function are already mutated (if needed).

.. note::

    We don't handle exceptions here
    (and in the next function).
    The function ``transmit``,
    which is implemented in the parent class,
    handles the exceptions.

::

        def _send_to_target(self, payload):
            self.serial.write(payload)

Part 2.1.2 - Receive response
+++++++++++++++++++++++++++++

This function responsible for reading the target's response.
As in ``_send_to_target``,
we usually don't handle exceptions in this function,
but leave ``transmit`` to handle it.

::

        def _receive_from_target(self):
            return self.serial.read(1000)

Part 3 - Close serial connection
++++++++++++++++++++++++++++++++

When we end the fuzzing session (i.e. all the tests),
we need to perform a cleanup.
The cleanup function called ``teardown``.
As with ``setup``,
the super function of ``teardown`` should be called as well.

::

        def teardown(self):
            if self.serial:
                self.serial.close()
                self.serial = None
            super(SerialTarget, self).teardown()

New connection in each test
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes, you don't want to use the same connection in different tests.

This can be acheived by implementing 
``pre_test`` to create the connection,
and ``post_test`` to close it,
instead of implmenting the ``setup`` and ``teardown`` functions.

.. note::

    As with ``setup`` and ``teardown``,
    you should call the super functions from your implementations.

::

        def pre_test(self, test_num):
            if self.serial:
                self.serial.close()
            self.serial = serial.Serial(self.dev_name, self.baudrate)
            self.serial.timeout = self.timeout
            super(SerialTarget, self).pre_test(test_num)

::

        def post_test(self, test_num):
            if self.serial:
                self.serial.close()
                self.serial = None
            super(SerialTarget, self).post_test(test_num)
