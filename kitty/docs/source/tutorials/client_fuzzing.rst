Client Fuzzing Tutorial
=======================

One of the advanteges of kitty is its ability to fuzz client targets.
Client targets are targets that we cannot fuzz by sending malformed
requests, but by sending malformed responses.

As explained in the
:doc:`/tutorials/server_vs_client`, this is a big difference, for two main reasons.
The first reason is that unlike server fuzzing, the communication is started
by the target, and not by the fuzzer.
The second reason is that in order to fuzz a client we usually need to hook
some functions in the server stack.

First we will explain how to fuzz a client target with Kitty. After
that, we will explain how to separate the code so the fuzzer will run in
a `separate process than the stack <#remote-fuzzer>`__.

How Does It Work
----------------

Since in our case the communication is triggered by the target and
handled by the stack, the fuzzer is passive. It triggers the client to
start the communication from its own context (thread / process) and then
does nothing until it is called by the stack to provide a response to
the target request.

The stack needs to get a mutation of a response from the fuzzer. The
fuzzer exposes the ``get_mutation(name, data)`` method to the stack to
provide those mutations. The responsibility of the stack is to call
``get_mutation`` in request handlers. If ``get_mutation`` returns
``None``, the stack handles the request aproprietly, otherwise, it
returns the result of ``get_mutation`` to the target.

Here's an example of (pseudo) client hook:

.. code:: python

    class StackImplementation:
        # ...
        def build_get_response(self, request_id):
            resp = self.fuzzer.get_mutation(stage='get_response', data={ 'request_id' : request_id })
            if resp:
                return resp
            # build valid response
            resp = ...
            return resp

``self.fuzzer`` in the example above is the instance of ``ClientFuzzer``
that we passed to the stack. We call ``get_mutation`` with two
arguments. The first, ``get_response`` is the name of the name of the
scheme (request) that is used for this request, that we create in our
data model. In ``get_mutation`` the fuzzer checks if it currently
fuzzing this scheme, and if so, it will return a mutated response,
otherwise it will return None. The second argument is a dictionary of
data that should be inserted into the ``DynamicField``\ s in the scheme,
it is usually a data that is transaction dependant and is not known when
building the scheme, for example, transaction or request id, such as in
the example above.

Building the Fuzzer
-------------------

We will list the different parts of the client fuzzer, in the last
section we will give a `simple example <#fuzzer-building-example>`__ of
such a fuzzer.

Target
~~~~~~

The target for client fuzzing inherits from
``kitty.target.client.ClientTarget`` unlike in server fuzzing, it's
major work is managing the controller and monitors, so you can often
just instantiate ``kitty.target.client.ClientTarget`` directly.

Controller
~~~~~~~~~~

The controller of the client target inherits from
``kitty.controllers.client.ClientController``. The most important method
in it is ``trigger``. This method triggers the client to start the
communication with the server stack. Since this method differ from
target to target, it is not implemented in ``ClientController`` and must
be implemented in a new class.

The other methods are inherited from
``kitty.controllers.base.BaseController`` and may or may not be
implemented in the new class, based on your needs.

Monitor
~~~~~~~

The monitors of the client target inherit from
``kitty.monitors.base.BaseMonitor`` there is nothing special in client
monitors.

User Interface
~~~~~~~~~~~~~~

The user interface of the client fuzzer inherit from
``kitty.interfaces.base.BaseInterface`` there is nothing special about
client fuzzer user interface.

Fuzzer
~~~~~~

When fuzzing a client, you should create a
``kitty.fuzzers.client.ClientFuzzer`` object, pass it to the stack, and
then start it.

Fuzzer Building Example
~~~~~~~~~~~~~~~~~~~~~~~

fuzz\_special\_stack.py
^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    import struct
    from kitty.targets import ClientTarget
    from kitty.controllers import ClientController
    from kitty.interfaces import WebInterface
    from kitty.fuzzers import ClientFuzzer
    from kitty.model import GraphModel
    from kitty.model import Template, Dynamic, String


    ################# Modified Stack #################
    class MySpecialStack(object):
        # We only show the relevant methods
        def __init__(self):
            self.fuzzer = None
            self.names = {1: 'Lumpy', 2: 'Cuddles', 3: 'Flaky', 4: 'Petunya'}

        def set_fuzzer(self, fuzzer):
            self.fuzzer = fuzzer

        def handle_GetName(self, name_id):
            resp = self.fuzzer.get_mutation(stage='GetName response', data={'name_id': struct.pack('I', name_id)})
            if resp:
                return resp
            name = '' if name_id not in self.names else self.names[name_id]
            return struct.pack('I', name_id) + name

    ################# Data Model #################

    get_name_response_template = Template(
        name='GetName response',
        fields=[
            Dynamic(key='name_id', default_value='\x00', name='name id'),
            String(value='admin', nane='name')
        ]
    )


    ################# Controller Implementation #################
    class MyClientController(ClientController):
        def __init__(self):
            super(MyClientController, self).__init__('MyClientController')

        def trigger(self):
            # trigger transaction start at the client
            pass


    ################# Actual fuzzer code #################
    target = ClientTarget('Example Target')

    controller = MyClientController()
    target.set_controller(controller)

    model = GraphModel()
    model.connect(get_name_response_template)
    fuzzer = ClientFuzzer()
    fuzzer.set_model(model)
    fuzzer.set_target(target)
    fuzzer.set_interface(WebInterface())

    my_stack = MySpecialStack()
    my_stack.set_fuzzer(fuzzer)
    fuzzer.start()
    my_stack.start()

Remote Fuzzer
-------------

The are two big problems with the client fuzzer that we've shown in the
previous section. The first problem is that it ties us to python2
implementations of the stack. This means that even if you have a stack
that you can modify, if it's not written in python2 you will need to
perform major changes to your code, or not use it at all. The second
problem is that even when using python2, different threading models and
signal handling may cause big issues with kitty, as it uses python
threads and uses signal handlers.

To overcome those issue, we have created the ``kitty.remote`` package.
It allows you to separate the stack process from the fuzzer process.

    Currently, we only support python2 and python3, using the same
    python modules (with ``six``) support for other languages will be
    provided in the future.

The idea is pretty simple - on the stack side, we only add
``RpcClient``. No data models, monitors, target or anything like that.
On the fuzzer side, we create the fuzzer as before, with all its
classes, and than wrap it with a ``RpcServer``, which waits for requests
from the agent.

The next example shows how we convert the `previous
example <#fuzz_special_stack.py>`__ to use the remote package.

Python2/3 Remote Fuzzer
~~~~~~~~~~~~~~~~~~~~~~~

my\_stack.py (python3)
^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    from kitty.remote import RpcClient

    ################# Modified Stack #################
    class MySpecialStack(object):
        # We only show the relevant methods
        def __init__(self):
            self.fuzzer = None
            self.names = {1: 'Lumpy', 2: 'Cuddles', 3: 'Flaky', 4: 'Petunya'}

        def set_fuzzer(self, fuzzer):
            self.fuzzer = fuzzer

        def handle_GetName(self, name_id):
            resp = self.fuzzer.get_mutation(stage='GetName response', data={'name_id': struct.pack('I', name_id)})
            if resp:
                return resp
            name = '' if name_id not in self.names else self.names[name_id]
            return struct.pack('I', name_id) + name

    fuzzer = RpcClient(host='127.0.0.1', port=26010)

    my_stack = MySpecialStack()
    my_stack.set_fuzzer(fuzzer)

    fuzzer.start()
    my_stack.start()

my\_stack\_fuzzer.py (python2)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    from kitty.targets import ClientTarget
    from kitty.controllers import ClientController
    from kitty.interfaces import WebInterface
    from kitty.fuzzers import ClientFuzzer
    from kitty.model import GraphModel
    from kitty.model import Template, Dynamic, String
    from kitty.remote import RpcServer


    ################# Data Model #################
    get_name_response_template = Template(
        name='GetName response',
        fields=[
            Dynamic(key='name_id', default_value='\x00', name='name id'),
            String(value='admin', nane='name')
        ]
    )


    ################# Controller Implementation #################
    class MyClientController(ClientController):
        def __init__(self):
            super(MyClientController, self).__init__('MyClientController')

        def trigger(self):
            # trigger transaction start at the client
            pass

    ################# Actual fuzzer code #################
    target = ClientTarget('Example Target')

    controller = MyClientController()
    target.set_controller(controller)

    model = GraphModel()
    model.connect(get_name_response_template)
    fuzzer = ClientFuzzer()
    fuzzer.set_model(model)
    fuzzer.set_target(target)
    fuzzer.set_interface(WebInterface())

    remote = RpcServer(host='127.0.0.1', port=26010, impl=fuzzer)
    remote.start()

