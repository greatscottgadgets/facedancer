Client Fuzzer - Browser - Using RPC
===================================

This fuzzer tests Opera handling of kinda- malformed HTML, the fuzzer runs in a separate process than the HTTP web server.
Two scripts are involved here:
1. runner - runs the fuzzer, and waits for the http server to be up
2. http_server - starts after the fuzzer, requests mutations from the fuzzer once Opera sends a request.

Note
----

In order to avoid the Opera poping in your screen, you should start a virtual display. In linux, you can do it with xvfb:

    ::

        Xvfb :2 -screen 2 1280x1024x8

If you don't mind the window poping in your screen, remove the line ``env['DISPLAY'] = ':2'`` from *runner.py*

Usage
-----

1. In terminal A:

    ::

        python runner.py
2. In terminal B:

    ::

        python http_server.py

