Server Fuzzing Tutorial
=======================

This tutorial will guide you through the steps that are taken to build a
fuzzer for your target, we will build such a fuzzer for a tiny HTTP
server. It will be a minimal implementation, just to show the basics.

-  First, we need to define our `data model <#data-model>`__ to let
   Kitty know how our protocol looks like.
-  Then, we need to define how will we communicate with our
   `target <#target>`__.
-  After that, we need to find a way to `control <#controller>`__ our
   target and how to `monitor <#monitor>`__ it (TBD).
-  And finally, we need to connect all those pieces together.

Data Model
----------

We start with a simple example, of fuzzing a simple HTTP GET request.
For simplicity, we will not look at the spec to see the format of each
message.

A simple "GET" request may look like this:

.. code:: http

    GET /index.html HTTP/1.1

There are some obvious fields in this request:

1. Method - a string with the value "GET"
2. Path - a string with the value "/index.html"
3. Protocol - a string with the value "HTTP/1.1"

However, there are some other things in this message, which we ignored:

-  (1.a) The space between Method and Path
-  (2.a) The space between Path and Protocol
-  

   (3) The double "new lines" ("") at the end of the request

Those are the delimiters, and we should not forget them.

Here's the translation of this structure to a Kitty model:

Data model, version 1

.. code:: python

    from kitty.model import *

    http_get_v1 = Template(name='HTTP_GET_V1', fields=[
        String('GET', name='method'),           # 1. Method - a string with the value "GET"
        Delimiter(' ', name='space1'),          # 1.a The space between Method and Path
        String('/index.html', name='path'),     # 2. Path - a string with the value "/index.html"
        Delimiter(' ', name='space2'),          # 2.a. The space between Path and Protocol
        String('HTTP/1.1', name='protocol'),    # 3. Protocol - a string with the value "HTTP/1.1"
        Delimiter('\r\n\r\n', name='eom'),      # 4. The double "new lines" ("\r\n\r\n") at the end of the http request
    ])

We used three new objects here, all declared in
**kitty/model/__init__.py**:

1. ``Template``, which is the top most container of the low level data
   model, it encloses a full message. It received all of its enclosed
   fields as an array.
2. ``String('GET', name='method')`` creates a new ``String`` object with
   the default value 'GET', and names it 'method'.
3. ``Delimiter(' ', name='space1')`` creates a new ``Delimiter`` object
   with the default value ' ', and names it 'space1'.

Based on this model, Kitty will generate various mutations of the
template, each mutation is constructed from a mutation of one of the
fields, and the default values of the rest of them. When a field has no
more mutations, it will return it to its default value, and move to the
next field.

Even in this simple example, we refine our model even more. We can see
that the **Protocol** field can be divided even more. We can split it to
the following fields:

-  (3.a) Protocol Name - a string with the value "HTTP"
-  (3.b) The '/' after "HTTP"
-  (3.c) Major Version - a number with the value 1
-  (3.d) The '.' between 1 and 1
-  (3.e) Minor Version - a number with the value 1

Now we can replace the ``protocol`` string field with 5 fields.

Data model, version 2

.. code:: python

    from kitty.model import *

    http_get_v2 = Template(name='HTTP_GET_V2', fields=[
        String('GET', name='method'),               # 1. Method - a string with the value "GET"
        Delimiter(' ', name='space1'),              # 1.a The space between Method and Path
        String('/index.html', name='path'),         # 2. Path - a string with the value "/index.html"
        Delimiter(' ', name='space2'),              # 2.a. The space between Path and Protocol
        String('HTTP', name='protocol name'),       # 3.a Protocol Name - a string with the value "HTTP"
        Delimiter('/', name='fws1'),                # 3.b The '/' after "HTTP"
        Dword(1, name='major version',              # 3.c Major Version - a number with the value 1
              encoder=ENC_INT_DEC),                 # encode the major version as decimal number
        Delimiter('.', name='dot1'),                # 3.d The '.' between 1 and 1
        Dword(1, name='minor version',              # 3.e Minor Version - a number with the value 1
              encoder=ENC_INT_DEC),                 # encode the minor version as decimal number
        Delimiter('\r\n\r\n', name='eom')           # 4. The double "new lines" ("\r\n\r\n") at the end of the request
    ])

We just met two new objects:

1. ``Dword(1, name='major version')`` create a 32-bit integer field with
   default value 1 and name it 'major version'
2. ``ENC_INT_DEC`` is an *encoder* that encodes this int as a decimal
   number. An encoder only affects the representation of the number, not
   its data nor its mutations

``Dword`` is part of a family of fields (``Byte``, ``Word`` and
``Qword``) that provides convenient initialization to the basic field on
``BitField``.

    The last example shows how we can treat a payload in different ways,
    and how it affects our data model. It is not always good to give too
    much details in the model. Sometimes too much details will make the
    fuzzer miss some weird cases, because it will always be "almost
    correct" and most of the times it will cause the fuzzing session to
    be very long. There is a balance that should be reached, and each
    implementor should find his own (this is a spiritual guide as well).

*HTTP\_GET\_V2* is pretty detailed data model, but while all parts of
the template that we want Kitty to send should be represented by fields,
there are fields that we don't want Kitty to mutate. For Instance, the
two new lines at the end of the request signals the server that the
message has ended, and if they are not sent, the request will probably
not be processed at all. Or, if we know there is a "GET" handler
function in the target, we might want to always have "GET " at the start
of our template.

The next example achieves both goals, but in two different ways:

Data model, version 3

.. code:: python

    from kitty.model import *

    http_get_v3 = Template(name='HTTP_GET_V3', fields=[
        String('GET', name='method', fuzzable=False),   # 1. Method - a string with the value "GET"
        Delimiter(' ', name='space1', fuzzable=False),  # 1.a The space between Method and Path
        String('/index.html', name='path'),             # 2. Path - a string with the value "/index.html"
        Delimiter(' ', name='space2'),                  # 2.a. The space between Path and Protocol
        String('HTTP', name='protocol name'),           # 3.a Protocol Name - a string with the value "HTTP"
        Delimiter('/', name='fws1'),                    # 3.b The '/' after "HTTP"
        Dword(1, name='major version',                  # 3.c Major Version - a number with the value 1
              encoder=ENC_INT_DEC),                     # encode the major version as decimal number
        Delimiter('.', name='dot1'),                    # 3.d The '.' between 1 and 1
        Dword(1, name='minor version',                  # 3.e Minor Version - a number with the value 1
              encoder=ENC_INT_DEC),                     # encode the minor version as decimal number
        Static('\r\n\r\n', name='eom')                  # 4. The double "new lines" ("\r\n\r\n") at the end of the request
    ])

The first method we used is setting the ``fuzzable`` parameter of a
field to ``False``, as we did for the first two fields, this method lets
us preserve the structure of the model, and change it easily when we do
want to mutate those fields:

.. code:: python

        String('GET', name='method', fuzzable=False),   # 1. Method - a string with the value "GET"
        Delimiter(' ', name='space1', fuzzable=False),  # 1.a The space between Method and Path

The second method is by using a ``Static`` object, which is immutable,
as we did with the last field, this method improves the readability if
we have a long chunk of data in our template that will never change:

.. code:: python

        # 4. The double "new lines" ("\r\n\r\n") at the end of the request
        Static('\r\n\r\n', name='eom')

Target
------

Now that we have a data model, we need to somehow pass it to our target.
Since we are fuzzing an HTTP server implementation, we need to send our
requests over TCP. There is already a target class to take care of TCP
communication with the server - ``kitty.targets.tcp.TcpTarget``, but we
will build it here again, step by step, to learn from it.

When fuzzing a server, our target should inherit from ``ServerTarget``.
Except of two methods - ``_send_to_target`` and
``_receive_from_target``, each method that you override should call its
super.

Each fuzzing session goes through the following stages:

::

    1. set up the environment
    2. for each mutation:
        1. preform pre-test actions
        2. do transmition
        3. cleanup after the test
        4. provide a test report
    3. tear down the environment

Each of those steps is reflected in the ``ServerTarget`` API:

+-----------------------------+---------------------------------------------------------------------------------------------+
| Step                        | Corresponding API                                                                           |
+=============================+=============================================================================================+
| set up the environment      | ``setup()``                                                                                 |
+-----------------------------+---------------------------------------------------------------------------------------------+
| perform pre-test actions    | ``pre_test(test_num)``                                                                      |
+-----------------------------+---------------------------------------------------------------------------------------------+
| do transmission             | ``transmit(payload)`` (calls ``_send_to_target(payload)`` and ``_receive_from_target()``)   |
+-----------------------------+---------------------------------------------------------------------------------------------+
| cleanup after test          | ``post_test(test_num)``                                                                     |
+-----------------------------+---------------------------------------------------------------------------------------------+
| provide a test report       | ``get_report()``                                                                            |
+-----------------------------+---------------------------------------------------------------------------------------------+
| tear down the environment   | ``teardown()``                                                                              |
+-----------------------------+---------------------------------------------------------------------------------------------+

Now let's implement those methods (the part we need):

class definition and constructor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    '''
    TcpTarget is an implementation of a TCP target
    '''
    import socket
    from kitty.targets.server import ServerTarget


    class TcpTarget(ServerTarget):
        '''
        TcpTarget is implementation of a TCP target for the ServerFuzzer
        '''

        def __init__(self, name, host, port, timeout=None, logger=None):
            '''
            :param name: name of the object
            :param host: hostname of the target (the TCP server)
            :param port: port of the target
            :param timeout: socket timeout (default: None)
            :param logger: logger for this object (default: None)
            '''
            ## Call ServerTarget constructor
            super(TcpTarget, self).__init__(name, logger)
            ## hostname of the target (the TCP server)
            self.host = host
            ## port of the target
            self.port = port
            if (host is None) or (port is None):
                raise ValueError('host and port may not be None')
            ## socket timeout (default: None)
            self.timeout = timeout
            ## the TCP socket
            self.socket = None

We create a socket at the beginning of each test, and close it at the
end

pre\_test and post\_test
^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

        def pre_test(self, test_num):
            '''
            prepare to the test, create a socket
            '''
            ## call the super (report preparation etc.)
            super(TcpTarget, self).pre_test(test_num)
            ## only create a socket if we don't have one
            if self.socket is None:
                sock = self._get_socket()
                ## set the timeout
                if self.timeout is not None:
                    sock.settimeout(self.timeout)
                ## connect to socket
                sock.connect((self.host, self.port))
                ## our TCP socket
                self.socket = sock

        def _get_socket(self):
            '''get a socket object'''
            ## Create a TCP socket
            return socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        def post_test(self, test_num):
            '''
            Called after a test is completed, perform cleanup etc.
            '''
            ## Call super, as it prepares the report
            super(TcpTarget, self).post_test(test_num)
            ## close socket
            if self.socket is not None:
                self.socket.close()
                ## set socket to none
                self.socket = None

Notice that we called the super in each overriden method. This is
important, as the super class perform many tasks that are not
target-specific.

The next step is to implement the sending and receiving. It's pretty
straight forward, we call socket's ``send`` and ``receive`` methods. We
don't call super in those methods, as the super is not implemented.

send\_to\_target + receive\_from\_target
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

        def _send_to_target(self, data):
            self.socket.send(data)

        def _receive_from_target(self):
            return self.socket.recv(10000)

That's it. We have a target that is able to perform TCP transmissions.

As the final stage of each test is providing a report, you can add
fields to the report in your target at each of the methods above.

A basic fuzzer can already created with what we've seen so far. Dummy
controller can supply supply the requirement of the base target class,
and we don't have to use any monitor at all, but if we want to be able
to not only crash the client, but to be able to detect the crash and
restart it once it crashes, we need to implement a ``Controller``

Controller
----------

As described in the `overview <docs/overview>`__, and in the `Controller
Documentation <doc/controller>`__, the controller makes sure that our
victim is ready to be fuzzed, and if it can't it reports failure.

In our example, we have an HTTP server that we want to fuzz, for
simplicity, we will run the server locally. We will do it by
implementing ``LocalProcessController`` a class that inherits from
``kitty.controllers.base.BaseController``.

The controller is controller by the ``Target`` and it follows pretty
much the same stages as the target (excluding the transmission) Each
fuzzing session goes through the following stages:

::

    1. set up the environment
    2. for each mutation:
        1. preform pre-test actions
        2. cleanup after the test
        3. provide a test report
    3. tear down the environment

Each of those steps is reflected in the ``ServerTarget`` API:

+-----------------------------+---------------------------+----------------------------------------------------------+
| Step                        | Corresponding API         | Controllers role                                         |
+=============================+===========================+==========================================================+
| set up the environment      | ``setup()``               | preparations                                             |
+-----------------------------+---------------------------+----------------------------------------------------------+
| perform pre-test actions    | ``pre_test(test_number)`` | prepare the victim to the test (make sure its up)        |
+-----------------------------+---------------------------+----------------------------------------------------------+
| cleanup after test          | ``post_test()``           | check the status of the victim, shut it down if needed   |
+-----------------------------+---------------------------+----------------------------------------------------------+
| provide a test report       | ``get_report()``          | provide a report                                         |
+-----------------------------+---------------------------+----------------------------------------------------------+
| tear down the environment   | ``teardown()``            | perform a cleanup                                        |
+-----------------------------+---------------------------+----------------------------------------------------------+

class definition and constructor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    from kitty.controllers.base import BaseController

    class LocalProcessController(BaseController):
        '''
        LocalProcessController a process that was opened using subprocess.Popen.
        The process will be created for each test and killed at the end of the test
        '''

        def __init__(self, name, process_path, process_args, logger=None):
            '''
            :param name: name of the object
            :param process_path: path to the target executable
            :param process_args: arguments to pass to the process
            :param logger: logger for this object (default: None)
            '''
            super(LocalProcessController, self).__init__(name, logger)
            assert(process_path)
            assert(os.path.exists(process_path))
            self._process_path = process_path
            self._process_name = os.path.basename(process_path)
            self._process_args = process_args
            self._process = None

Our controller has nothing to do at the setup stage, so we don't
override this method

Before a test starts, we need to make sure that the victim is up

pre\_test
^^^^^^^^^

.. code:: python

        def pre_test(self, test_number):
            '''start the victim'''
            ## call the super
            super(LocalProcessController, self).pre_test(test_num)
            ## stop the process if it still runs for some reason
            if self._process:
                self._stop_process()
            cmd = [self._process_path] + self._process_args
            ## start the process
            self._process = Popen(cmd, stdout=PIPE, stderr=PIPE)
            ## add process information to the report
            self.report.add('process_name', self._process_name)
            self.report.add('process_path', self._process_path)
            self.report.add('process_args', self._process_args)
            self.report.add('process_id', self._process.pid)

When the test is over, we want to store the output of the process, as
well as its exit code (if crashed):

post\_test
^^^^^^^^^^

.. code:: python

        def post_test(self):
            '''Called when test is done'''
            self._stop_process()
            ## Make sure process started by us
            assert(self._process)
            ## add process information to the report
            self.report.add('stdout', self._process.stdout.read())
            self.report.add('stderr', self._process.stderr.read())
            self.logger.debug('return code: %d', self._process.returncode)
            self.report.add('return_code', self._process.returncode)
            ## if the process crashed, we will have a different return code
            if self._process.returncode != 0:
                self.report.failed('return code is not zero: %s' % self._process.returncode)
            self._process = None
            ## call the super
            super(LocalProcessController, self).post_test()

When all fuzzing is over, we perform the ``teardown``:

teardown
^^^^^^^^

.. code:: python

        def teardown(self):
            '''
            Called at the end of the fuzzing session, override with victim teardown
            '''
            self._stop_process()
            self._process = None
            super(LocalProcessController, self).teardown()

Finally, here is the implementation of the ``_stop_process`` method

\_stop\_process
^^^^^^^^^^^^^^^

.. code:: python

        def _stop_process(self):
            if self._is_victim_alive():
                self._process.terminate()
                time.sleep(0.5)
                if self._is_victim_alive():
                    self._process.kill()
                    time.sleep(0.5)
                    if self._is_victim_alive():
                        raise Exception('Failed to kill client process')

        def _is_victim_alive(self):
            return self._process and (self._process.poll() is None)
