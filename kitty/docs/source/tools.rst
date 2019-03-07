Kitty Tools
===========

When installing Kitty using setup.py or pip, it will install several
tools:

Template Tester
---------------

::

    Usage:
        kitty-template-tester [--fast] [--tree] [--verbose] <FILE> ...

    This tool mutates and renders templates in a file, making sure there are no
    syntax issues in the templates.
    It doesn't prove that the data model is correct, only checks that the it is
    a valid model

    Options:
        <FILE>      python file that contains templates in dictionaries, lists or globals
        --fast      only import, don't run all mutations
        --tree      print fields tree of the template instead of mutating it
        --verbose   print full call stack upon exception


Kitty Tools
-----------

kitty-tool will replace kitty-template tester and provide extended functionality

::

    Tools for testing and manipulating kitty templates.

    Usage:
        kitty-tool generate [--verbose] [-s SKIP] [-c COUNT] [-o OUTDIR] [-f FORMAT] <FILE> <TEMPLATE> ...
        kitty-tool list <FILE>
        kitty-tool --version

    Commands:

        generate    generate files with mutated payload
        list        list templates in a file

    Options:
        <FILE>                  python file that contains the template
        <TEMPLATE>              template name(s) to generate files from
        --out -o OUTDIR         output directory for the generated mutations [default: out]
        --skip -s SKIP          how many mutations to skip [default: 0]
        --count -c COUNT        end index to generate
        --verbose -v            verbose output
        --filename-format -f FORMAT  format for generated file names [default: %(template)s.%(index)s.bin]
        --version               print version and exit
        --help -h               print this help and exit

    File name formats:
        You can control the name of an output file by giving a filename format,
        it follows python's dictionary format string.
        The available keywords are:
            template - the template name
            index - the template index


CLI Web Client
--------------

::

    Usage:
        kitty-web-client (info [-v]|pause|resume) [--host <hostname>] [--port <port>]
        kitty_web_client.py reports store <folder> [--host <hostname>] [--port <port>]
        kitty_web_client.py reports show <file> ...

    Retrieve and parse kitty status and reports from a kitty web server

    Options:
        -v --verbose            verbose information
        -h --host <hostname>    kitty web server host [default: localhost]
        -p --port <port>        kitty web server port [default: 26000]
