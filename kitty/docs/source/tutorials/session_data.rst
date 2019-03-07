Session Data in Server Fuzzing
==============================

Overview
--------

There are cases where not all of the data is available when writing the data model.
For example, when you have a multi-message session with the target,
and you need to use a session ID that was returned in the first message from the target.

Kitty provides means to handle these cases.
However, since this problem is a little complex, Kitty's solution is composed of 3 parts.

1. Special fields in the template to indicate that a data is session-specific (done by you)
2. Callback between messages in the session, providing a hook to parse responses and handle them (done by you)
3. Call to Target API to get the session specific data before rendering each template (done by the fuzzer)

We'll go over the usage of this feature using an example protocol.

Example Protocol
----------------

::

    Fuzzer (client)                               Target (server)
        ||---------------(open_session)----------------->||
        ||<---------------(session_id)-------------------||
        ||-------(do_something + session_id)------------>||
        ||<----------------(ok)--------------------------||

The Templates
-------------

We need to implement two templates:

1. open_session

    Used to request the server to open a session.
    The server responds with a session id, which should be used in subsequent calls.

    ::

        open_session = Template(name='open_session', fields=[
            String(name='username', value='user'),
            Static(': '),
            String(name='password', value='pass'),
        ])

2. do_something

    Tells the server to do something, providing the session ID to the open session.
    Since we don't know the session id at the time we write the tempalte,
    we define it as a :class:`~kitty.model.low_level.field.Dynamic` field,
    and assigning a key to it, this key will be used later on.

    ::

        do_something = Template(name='do_something', fields=[
            Static('session id: '),
            # this is the intersting field
            Dynamic(key='session_id', default_value=''),
            Static('\naction: '),
            String(name='the action', value='cry me a river')
        ])

Great.
So at this point we have two templates,
and the second one knows that it might be changed (partially)
by external entities at runtime.
Time to create a connection between the two messages.


The Callback
------------

What do we actually want to do?
We want to parse the resposnse to the **open_session** request,
extract the **session_id** from it
and provide the **session_id** to the **do_something** template.

We'll do that by using :class:`~kitty.model.high_level.graph.GraphModel`
:func:`~kitty.model.high_level.graph.GraphModel.connect` method's
third arguemnt - the callback.

::

    g = GraphModel('session-graph')
    g.connect(open_session)
    g.connect(open_session, do_something, new_session_callback)

``new_session_callback`` will be called when we get a response to the **open_session**
and before we render and send **do_something**

And here's the implementation of ``new_session_callback``:

::

    def new_session_callback(fuzzer, edge, resp):
        '''
        :param fuzzer: the fuzzer object
        :param edge: the edge in the graph we currently at.
                     edge.src is the open_session template
                     edge.dst is the do_something template
        :param resp: the response from the target
        '''
        # let's say that we have a reference to the target object,
        # or this might be a target's method
        target.session_data['session_id'] = extract_session_from_response(resp)

Once we set the **session_id** value in the ``session_data`` dictionary, we are good to go.
From this point, the fuzzer will take the ``session_data`` dictionary from the target
and set it in the template.
Note that you can have multiple key/value pairs in the dictionary,
and that you don't have to have key/value pairs for all dynamic fields.
Only those who exist in the dictionary will be set in the dynamic fields.
Also, you can have multiple dynamic fields with the same key.
