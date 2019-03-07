Controllers
===========

The controller is in charge of preparing the victim for the test. It
should make sure that the victim is in an appropriate state before the
target initiates the transfer session. Sometimes it means doing nothing,
other times it means starting or reseting a VM, killing a process or
performing a hard reset to the victim hardware. Since the controller is
reponsible for the state of the victim, it is expected to perform a
basic monitoring as well, and report whether the victim is ready for the
next test.

Core Classes
------------

BaseController
~~~~~~~~~~~~~~

``kitty.controllers.base.BaseController``
(``kitty.core.kitty_object.KittyObject``)

``setup(self)``

Called at the beginning of the fuzzing session, override with victim
setup

``teardown(self)``

Called at the end of the fuzzing session, override with victim teardown

``pre_test(self, test_number)``

Called before a test is started Call super if overriden

``post_test(self)``

Called when test is done Call super if overriden

``get_report(self)``

Returns a report about the victim since last call to pre\_test

ClientController
~~~~~~~~~~~~~~~~

``kitty.controllers.client.ClientController``
(``kitty.controllers.base.BaseController``)

ClientController is a controller for victim in client mode

``trigger(self)``

Trigger a data exchange from the tested client

EmptyController
~~~~~~~~~~~~~~~

``kitty.controllers.empty.EmptyController``
(``kitty.controllers.client.ClientController``) EmptyController does
nothing, implements both client and server controller API

Implementation Classes
----------------------

Implemented controllers for different victim types.

ClientGDBController
~~~~~~~~~~~~~~~~~~~

``kitty.controllers.client_gdb.ClientGDBController``
(``kitty.controllers.client.ClientController``)

ClientGDBController runs a client target in gdb to allow further
monitoring and crash detection.

*Requires pygdb*

``__init__(self, name, gdb_path, process_path, process_args, max_run_time, logger=None)``

ClientUSBController
~~~~~~~~~~~~~~~~~~~

``kitty.controllers.client_usb.ClientUSBController``
(``kitty.controllers.client.ClientController``)

ClientUSBController is a controller that triggers USB device connection
by switching its Vbus signal. It is done by controlling EL7156 from
arduino. The arduino is loaded with
`firmata <https://github.com/firmata/arduino>`__, which allows remote
control over serial from the PC, using
`pyduino <https://github.com/firmata/pyduino>`__.

``__init__(self, name, controller_port, connect_delay, logger=None)``

-  ``controller_port``: tty port of the controller
-  ``connect_delay``: delay between disconnecting and reconnecting the
   USB, in seconds

ClientProcessController
~~~~~~~~~~~~~~~~~~~~~~~

``kitty.controllers.client_process.ClientProcessController``
(``kitty.controllers.client.ClientController``)

Starts the client with ``subprocess.Popen``, collects *stdout* and
*stderr*.

``__init__(self, name, process_path, process_args, logger=None)``

TcpSystemController
~~~~~~~~~~~~~~~~~~~

``kitty.controllers.tcp_system.TcpSystemController``
(``kitty.controllers.base.BaseController``)

this controller controls a process on a remote machine by sending tcp
commands over the network to a local agent on the remote machine to
execute using popen

``__init__(self, name, logger, proc_name, host, port)``

-  ``proc_name``: name of victim process
-  ``host``: hostname of agent
-  ``port``: port of agent

