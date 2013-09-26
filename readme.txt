Cake Build System (http://sourceforge.net/projects/cake-build)

Description
-----------

Cake is a fast, general purpose build system written in Python.

Cake has builtin support for building C/C++ projects but can be easily extended to support other kinds of build targets.

Features
--------

- Platorm support
  - Windows
  - Cygwin
- Compiler support
  - Visual Studio 2005/2008/2010
  - Visual C++ Express
  - WindowsSDK
  - GCC
  - MinGW
- Build Variants
- Object file cache
- Multi-threaded builds
- Basic shell commands
- Pre-compiled headers

Upcoming Features
-----------------

- Linux support
- OSX support
- CodeWarrior support

License
-------

Licensed under the MIT license.

Installing
----------

1 - Open a command prompt in this documents directory.
2 - Type 'python setup.py install'.

Optionally run the chosen installer executable or script for your operating system, if it exists.

Usage
-----

config.cake
===========

When Cake starts it will search for a 'config.cake' file starting from the directory of the 'build.cake' script it is trying to execute. This file should generally be located in your projects root directory.

The quickest way to create a config.cake file is to copy src/cake/config.py. The example config file supports automatic detection of MSVC, MinGW and Gcc compilers, and two development modes, 'debug' and 'release'.

Running Cake
============

To run cake you simply type cake at the command line:

  'cake'

It will automatically look for a file called 'build.cake' in the current directory and execute it.

You can optionally supply the script filename you want to run as an argument, eg:

  'cake C:\projects\mylibrary\buildmylibrary.cake'.

You can also specify which variants to run by supplying variant keywords, eg:

  'cake platform=windows compiler=msvc'

This will run all variants that build for the windows platform using the msvc compiler.

You can debug the build by using the '--debug' option with any of the available debug keywords, eg:

  'cake --debug=run'

Will output the command lines that Cake runs.

  'cake --debug=reason'

Will output the reason cake is rebuilding your files (ie. what has changed).

Known Issues
------------

- There is no support for building a module (DLL) with import library under CodeWarrior.

- There is no support for finding a CodeWarrior compiler automatically, eg. mwcw.findCodeWarriorCompiler().
