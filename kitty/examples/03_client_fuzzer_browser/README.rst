Client Fuzzer - Browser - Single Process
========================================

This fuzzer tests Opera handling of kinda- malformed HTML, unlike example 2, the fuzzer runs on the same process as the HTTP server.

This example uses Opera browser as target. Please install opera in order to run this example.

Note
----

In order to avoid the Opera poping in your screen, you should start a virtual display. In linux, you can do it with xvfb:

::

    Xvfb :2 -screen 2 1280x1024x8

If you don't mind the window poping in your screen, remove the line ``env['DISPLAY'] = ':2'`` from *runner.py*

Usage
-----

::

    python runner.py

