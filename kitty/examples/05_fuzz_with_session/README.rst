Server Fuzzer - Fuzz With Session
=================================

This fuzzer performs server fuzzing with session enabled.


Note
----

**server_controller.py** is used to control **session server**(our target).

**session server** is a TCP server which listen on port 9999, our goal is to make **session server** 'crash'.

communicate with session server
-------------------------------

To communicate with **session server** you need request a specific session for each connection.

You must use correct session with op_code(2) to send data to **session_server**. If your session
is correct, server will return a same packet which you just send, otherwise server will return 'session is incorrect'.

Remember **Session server** only support two kind of packet 'get_session' and 'send_data'. If you send other packet to server, server will return 'packet format is incorrect' and close your current connection.

**Session server** will **crash** when you send a packet with length greater than 255 using 'send_data' format.

For more details, please check the docs in **session_server.py** and class ``SessionHandler``


controller of session server
----------------------------

``SessionServerController`` will restart **session server** before each test and check **session server** is alive or not when each test is done. If ``SessionServerController`` detected **session server** is crash, it will add a failed to report.





Usage
-----

::

    python runner.py

