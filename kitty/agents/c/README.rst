Kitty agent library for C
=========================

Overview
--------

Kitty client fuzzing strategy requires embedding of an agent into the server stack. This project provides you with a such an agent for stacks written in C.

Dependencies
------------
The kitty agent for C stacks depends on two libraries:

1. json-c
    - Author: Eric Haszlakiewicz
    - License: MIT license
    - Site: https://github.com/json-c/json-c
2. libcurl
    - Author: Daniel Stenberg
    - License: MIT/X license
    - Site: http://curl.haxx.se/

Building the library
--------------------

1. Download and build json-c
2. Copy **path/to/json-c/.lib/libjson-c.a** to **kitty/agents/json-c/**
3. Copy all json-c **\*.h** files to **kitty/agents/c/json-c/**
4. make

Compiling with the library
--------------------------

Compile your stack code with **lib/libkitty-agent.a** and with **-lcurl**

Using the library
-----------------

.. code:: c

    #include "kitty.h"

    // this example uses a global kitty handler for simplicity
    kitty * hkitty = NULL;

    // IP and port should match the kitty fuzzer itself, so this definitions below match the following python part
    // RemoteFuzzer(my_fuzzer, name='Remote Fuzzer', host='127.0.0.1', port=25000)
    const char * KITTY_FUZZER_IP = "127.0.0.1";
    const int KITTY_FUZZER_PORT = 25000;

    // Some stack initialization function
    void stack_init(){
        hkitty = kitty_init(KITTY_FUZZER_IP, KITTY_FUZZER_PORT);
        // start fuzzing (when stack is up...)
        kitty_start(hkitty);
    }

    // handle message X from client
    void handle_message_X(int client_handle){
        // only fuzz if fuzzer agent initialized
        if(hkitty) {
            // You can send parameters to the fuzzer
            // For example, if client handle is sent in the response as well
            char s_client_handle[4];
            int_to_buff(client_handle, s_client_handle);
            kitty_buff * mutation;
            kitty_add_session_data(hkitty, "client_handle", s_client_handle, sizeof(s_client_handle));
            // Now, we ask the fuzzer for a mutation for the message X
            if(kitty_get_mutation(hkitty, "X", &mutation))
            {
                // This is the mutation, send it back to the client...
                memcpy(local_buff, mutation->buffer, mutation->buffer_len);
                // done with the mutation? clear it
                kitty_buffer_release(mutation);
            }
        }
        else {
            // do normal processing
        }
    }

    void stack_shutdown(){
        kitty_quit(hkitty);
        kitty_destroy(hkitty);
    }
