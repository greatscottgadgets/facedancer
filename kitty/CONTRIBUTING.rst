Contributing to Kitty
=====================

If you look here - thanks!

This document describes the guidelines for contribution for Kitty.
This is not to discourage you from contributing -
we only benefit from contribution.
However, we want to keep Kitty stable, documented and easy to read.

At this point, this guide is rather short, so please read it from start to end.

Code
----

- **Python 3 compatibility**

  Kitty now supports both Python 2.7 and Python 3. please make any change or
  addition Python2 and Python3 compatible.

- **Coding conventions**

  We do try to make the pass pylint checks (although it is still far from it)
  don't make it harder for us, check your code with pylint before you issue
  a pull request.
  Specifically, you should not have redundant spaces/line breaks in your code,
  nor lines longer than 160 characters.

- **Comments**

  We do try not to comment the code, in most cases, comments tell us that the
  code is not clear enough to begin with.
  If this is the case - please refactor your code.
  Of course, if the code is unclear but there's no way to make it better,
  put a comment there.

- **logging**

  There should be no calls to ``print()`` in your code.
  Kitty uses python's logging infrastructure,
  and every object that derives from ``KittyObject`` have a member ``self.logger``
  just for you.
  Kitty's default logging level is ``INFO``,
  and in this mode there shouldn't be too much logging to the terminal,
  Please use the appropriate logger functions.

Tests
-----

We try to keep Kitty tested, tests run on each push and pull request.
The tests are located at the **tests** directory,
and ``python runner.py`` should run all of them.
We have a few requests:

- Run the tests before you open a pull requests.
- Run the test in Python 2.7 AND Python 3.6 environments.
- Add tests for every new module, feature, class or code that you create.
  if your pull request is meant to fix a bug in Kitty,
  it means that we are missing a test there.
  Add such a test with your fix.
- If you create a new test file, add it to the runner,
  so it will run with the rest of the tests.

Documentation
-------------

We also try to keep Kitty documented.
We use Sphinx to generate the documentation.
Sphinx generates documentation from both code and documentation files.
So we require a few things in pull requests.

- **Docstrings**

  Add docstrings to your code - modules, classes and public methods.
  Take a look at other modules (mainly in **kitty/model/low_level**)
  to get an idea of how we document the code.

- **New modules**

  If you add a new file to kitty, you should:

  - Add a class description file to **docs/source**.
    Take a look at **kitty.model.low_level.aliases.rst**
    as an example.

    Your file name should match the ``import`` of this file,
    for example,
    if you add the file **kitty/model/low_level/mymodule.py**
    the documentation file will be called **kitty.model.low_level.mymodule.rst**

  - Add this description file to the TOC of the package.
    If we keep the example from the last bullet,
    Open the file **kitty.model.low_level.rst** and add
    the line **kitty.model.low_level.mymodule** to the TOC tree.

- **New features**

  If you add a new feature to kitty,
  consider adding a more thorough documentation and a tutorial.
  Add them to the TOC tree of **index.rst** and **tutorials/index.rst**
  (respectively).


That's it, and thanks for your help!

