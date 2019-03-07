Server vs. Client Fuzzing
=========================

Kitty is a framework for fuzzing various kinds of entities. It can fuzz
**servers** --- by acting like a web client to initiate requests to the
victim server, or by acting like a USB host to send commands to the
victim USB device; and it can also fuzz **clients**, by responding to
requests made by them --- acting as the web server to respond to requests
from the victim browser, or as the USB device responding to commands
from the victim USB host.

In Kitty's terminology, the **client** is the side initiating the data
exchange, and the **server** is the side reacting to it. By this
defintion, a TCP server would be considered a server, as it reacts to
requests initiated by the fuzzer; but so would a PDF viewer, if it is
started with a given file provided by the fuzzer. Similarly, an IRC
client or a web browser would be considered clients, as they initiate
requests to the fuzzer and then process its responses; but so would a
USB-Host stack, which initiates the data exchange with a fuzzer
disguised as the USB device. And in fact, the same entity could be a
client in some contexts, and a server in others: a web browser would be
considered a client in the context of conversations made to the
fuzzer-server, as seen above; but would be considerd a server in the
context of being run as a process by the fuzzer, with a command-line
argument pointing it at a given (presumably-fuzzed) URL.

There is a big difference between server fuzzing and client fuzzing,
and the need to support both was a main driver for the creation of Kitty. This
section will list the conceptual, flow and implementation differences
between those two modes.

Conceptual Differences
----------------------

:Session initiation:
   Since the nature of a server is to handle and respond to requests, it
   is rather simple to fuzz it on our terms: we need to make sure it is
   up and ready to accept requests, and then start sending those
   requests to it. This means that the fuzzer is **active**, it initiates
   the data exchange and decides what data the server will handle,
   assuming that the server starts in the same state for each data
   exchange session.

   On the other hand, when fuzzing a client, the mutated data is the
   response, not the request. The client is the one to initiate the
   data exchange, the fuzzer acts as a server, and so it is **passive**
   and cannot control the timing or even the occurence of the fuzzing
   session. In order to take control back, the fuzzer needs some way to
   cause the client to start the data exchange.

:Communication Stack:
   When a server is tested,
   it is the fuzzer, as we just saw, that initiates the communication.
   This means that the fuzzer can choose at exactly what layer 
   to begin the communication.
   So, for example, when
   testing a TCP-based protocol, the TCP stack may be used, and when
   testing an HTTP-based protocol, an HTTP stack may be used. Moreover,
   there usually are readily-available Python or C APIs
   for initiating the communication starting at any of these layers.

   When testing a client, on the other hand, the fuzzer is only responding
   to requests from the client. As such, the fuzzer cannot easily choose
   at which layer to handle the communication --- 
   it must handle the request at whichever layer it was received.
   Thus, fuzzing a specific layer will very likely require hooking into the
   stack implementation in order to inject the mutated responses.

Flow Differences
----------------

The flow differences are derived from the conceptual differences, the
flow for each scenario is described below.

[ TBD - flow charts ]

Implementation Differences
--------------------------

The implementation differences are derived from the flow differences and
are listed in the table below.

+--------------+-----------------------------------------------+--------------------------------------------------+
| Component    | Server Mode                                   | Client Mode                                      |
+==============+===============================================+==================================================+
| Stack        | Unmodified in most cases                      | Hooked in most cases, runs as a separate process |
+--------------+-----------------------------------------------+--------------------------------------------------+
| Target       | Responsible for sending and receiving data    | Responsible for triggering the data exchange in  |
|              | from victim, uses the stack                   | the victim (using the controller), data is       |
|              |                                               | handled directly by the stack                    |
+--------------+-----------------------------------------------+--------------------------------------------------+
| Controller   | Brings the victim to initial state, monitors  | Same as in server mode, but additionally         |
|              | victim status                                 | responsible for triggering the data exchange     |
+--------------+-----------------------------------------------+--------------------------------------------------+
| Fuzzer       | Actively polls the data model for more data   | Waits in a separate process for requests from    |
|              | and triggers the data exhange                 | the modified stack over IPC, provides stack with |
|              |                                               | mutated data when needed                         |
+--------------+-----------------------------------------------+--------------------------------------------------+

