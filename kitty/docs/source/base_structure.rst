Framework Structure
===================

This document goes over the main modules that form a fuzzer and explains
the relation between them.
It also discusses the differences between client and server fuzzing.

Relation Between Modules
------------------------

.. note::

   Need to generate UML, look here... https://build-me-the-docs-please.readthedocs.io/en/latest/Using_Sphinx/UsingGraphicsAndDiagramsInSphinx.html

::

    Fuzzer  +--- Model *--- Template *--- Field
            |
            +--- Target  +--- Controller
            |            |
            |            *--- Monitor
            |
            +--- Interface

Modules
-------

Data Model
~~~~~~~~~~

The first part of Kitty is the data model. It defines the structure of
the messages that will be sent by the fuzzer. This includes a separation
of the message into fields (such as header, length and payload), types of those
fields (such as string, checksum and hex-encoded 32bit integer) and the
relation between them (such as length, checksum and count). The data model
also describes the order in which different messages are chained together
to form a fuzzing session.
This can be useful when trying to fuzz deeper parts of the system
(for example, getting past an authentication stage
in order to fuzz the parts of the system only reachable by authenticated users).
The data model can also specify
that the order in which messages are sent itself be fuzzed.

The data model is constructed using the classes defined in the
`model <https://github.com/cisco-sas/kitty/tree/master/kitty/model>`_ source folder.

For more information, visit the data model :doc:`documentation </data_model/overview>`,
:doc:`reference </kitty.model>` and :doc:`tutorials </tutorials/index>`.

Target
~~~~~~

:Base Classes:

   1. ``kitty.targets.client.ClientTarget`` when fuzzing a client
      application
   2. ``kitty.targets.server.ServerTarget`` when fuzzing a server
      application


:API Reference: :doc:`kitty.targets`

The target module is in charge of everything that is related to the
victim. Its responsibilities are:

1. When fuzzing a server --- initiating the fuzzing session by sending a
   request to the server, and handling the response, when such response
   exists.
2. When fuzzing a client --- triggering a fuzzing session by causing the
   client to initiate a request to the server.
   The server, with the help of the stack (see the :doc:`client fuzzing tutorial </tutorials/client_fuzzing>`),
   will send a fuzzed response to the client.
   Note that in this case
   the target itself is not involved the client-server-fuzzer communication!
3. Managing the monitors and controllers (see below).

The sources for the target classes are located in the **targets** source folder.
There are two target base classes, ``ClientTarget`` (in ``targets/client.py``) and
``ServerTarget`` (in ``targets/server.py``). These classes define the target APIs
and should be subclassed when implementing a new target class.

A class should be written for every new type of target. For example, if you
want to test a server application that communicates over a serial UART
connection, you will need to create a new class that inherits from
``ServerTarget`` and is able to send data over the UART. However, many times it will
only require the implementation of the send/receive functions and not much more.
Some targets are already available in the Katnip_ repository,
so you don't need to implement them yourself: for example,
``TcpTarget`` may be used to test HTTP servers and ``SslTarget`` may be used to
test HTTPS servers.

The controller and the monitors (described below) are managed by the
target, which queries and uses them as needed.

For each test the target generates a report which contains the reports
of the controller and all monitors. This report is passed back to the
fuzzer (described below) upon request.

Controller
~~~~~~~~~~

:Base Class: ``kitty.controllers.base.BaseController``

:API Reference: :doc:`kitty.controllers`

The controller is in charge of preparing the victim for the test. It
should make sure that the victim is in an appropriate state before the
target initiates the transfer session. Sometimes it means doing nothing,
other times it means starting or reseting a VM, killing a process or
performing a hard reset to the victim hardware.

Since the controller is reponsible for the state of the victim, it is
expected to perform basic monitoring as well, and report whether the
victim is ready for the next test.

Monitor
~~~~~~~

:Base Class: ``kitty.monitors.base.BaseMonitor``

:API Reference: :doc:`kitty.monitors`

A monitor object monitors the behavior of the victim. It may monitor the
network traffic, memory consumption, serial output or anything else.

Since there might be more than a single behavior to monitor, multiple
monitors can be used when fuzzing a victim.

Fuzzer
~~~~~~

:Classes:
   
   1. ``kitty.fuzzers.client.ClientFuzzer`` when fuzzing a client target.
   2. ``kitty.fuzzers.server.ServerFuzzer`` when fuzzing a server target.

:API Reference: :doc:`kitty.fuzzers`

A fuzzer drives the whole fuzzing process. Its job is to obtain mutated
payloads from the model, initiate the data transaction, receive the
report from the target, and perform further processing, if needed. A
fuzzer is the top level entity in our test runner, and should not be
subclassed in most cases.

Interface
~~~~~~~~~

:Base Class: ``kitty.interfaces.base.BaseInterface``

:API Reference: :doc:`kitty.interfaces`

Interface is a user interface, which allows the user to monitor and
check the fuzzer as it goes. The web interface should suffice in most
cases.

.. _Katnip: https://github.com/cisco-sas/katnip
