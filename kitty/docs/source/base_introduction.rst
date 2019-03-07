Introduction
============

   | *Sulley: Boo?*
   | *Boo: Kitty!*

What is Kitty?
--------------

Kitty is an open-source modular and extensible fuzzing framework
written in python,
inspired by OpenRCE's `Sulley <https://github.com/OpenRCE/sulley>`_
and Michael Eddington's (and now Deja Vu Security's) `Peach Fuzzer
<http://community.peachfuzzer.com/>`_.

Goal
~~~~

When we started writing Kitty, our goal was to help us fuzz unusual targets
--- meaning proprietary and esoteric protocols over non-TCP/IP communication
channels --- without writing everything from scratch each time. A generic and
abstract framework that would include the common functionallity of every
fuzzing process we could think of, and would allow the user to easily extend
and use it to test their specific target.

Features
~~~~~~~~

With this goal in mind, the following features were very important to us:

:Modularity:
   Each part of the fuzzer stands on its own. This means
   that you can use the same monitoring code for different applications,
   or the same payload generator (aka *Data Model*) for testing parsing
   of the same data that is received over different channels.

:Extensibility:
   If you need to test something "new", you will not need
   to change Kitty's core code. Most, if not all, features can be implemented
   in the user code. This includes monitoring, controlling and communicating
   with the fuzzed target.

:Rich data modeling: 
   The data model core is rich and allows describing advanced data structures,
   including strings, hashes, lengths, conditions and many more. And,
   like most of the framework,
   it is designed to be extended even further as necessary.

:Stateful:
   Support for multi-stage fuzzing tests. Not only you can describe
   what the payload of an individual message will look like,
   you can also describe the order of messages, and even perform 
   fuzzing on the sequence's order.

:Client and Server fuzzing:
   You can fuzz both servers and clients, assuming
   you have a matching stack. Sounds like a big requirement, but it isn't:
   it just means that you should have the means to communicate with the target,
   which you should have in most cases anyway.

:Cross platform:
   Runs on Linux, OS X and Windows. We don't judge ;-)


What it's not?
--------------

Well, Kitty is not a fuzzer. It also contains no implementation of specific
protocol or communication channel. You can write your own fuzzer with it, and
you can use Kitty-based code of others, but it's not an out-of-the-box fuzzer.

A good place to get (and add) implementations of Kitty models is Katnip.

Katnip
~~~~~~

Kitty, as a framework, implements the fuzzer main loop, and provides
syntax for modeling data and base classes for each of the elements
that are used to create a full fuzzing session. However, specific
implementations of classes are **not** part of the Kitty framework.
This means that Kitty defines the interface and base class to perform
data transactions with a target, but it doesn't provide implementations
for data transmition over HTTP, TCP or UART.

Implementations of all sorts of classes can be found in the complimentary
repository Katnip_, which has the sole porpuse of providing specific
*implementaions*. As such, Katnip contains different implementations for
targets (such as ``TcpTarget`` and ``SslTarget``), controllers (such as
``TelnetController`` and ``SshController``), monitors and templates. Use
them when you write your fuzzer, as they will save you a lot of time, and
may serve as a reference for your own implementations.

What's Next?
------------

- Go over Kitty's :doc:`structure </base_structure>`
- Take a look at, and run, some examples (requires Katnip)
- Go over the :doc:`tutorials </tutorials/index>`
- Go fuzz something new :)

Contribution FAQ
----------------

*Found a bug?*
   Open an `issue <https://github.com/cisco-sas/kitty/issues/new>`_

*Have a fix?*
   Great! please submit a `pull request <https://github.com/cisco-sas/kitty/compare>`_

*Implemented an interesting controller/monitor/target?*
   Please submit a pull request in the `Katnip repository <https://github.com/cisco-sas/katnip>`_

*Found an interesting bug using a Kitty-based fuzzer?*
   We'd love to hear about it! please drop us a line

.. _Katnip: https://github.com/cisco-sas/katnip