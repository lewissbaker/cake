Cake Build System

Description
-----------

A relatively fast build system written in Python.

Installing
----------

1 - Open a command prompt in this documents directory.
2 - Type 'python setup.py install'.

Optionally run the chosen installer executable or script for your operating system.

Usage
-----

boot.cake
=========

When Cake starts it will search for a 'boot.cake' file starting from the current working directory. This file should generally be located in your projects root directory.

The quickest way to create a boot.cake file is to copy examples/boot.cake. The example boot file supports automatic detection of MSVC, MinGW and gcc compilers, and two development modes, 'debug' and 'release'.

Running Cake
============

To run cake you can simply type cake at the command line:

  'cake'

It will automatically look for a file called 'build.cake' in the current directory and execute it.

You can optionally supply the script filename you want to run as an argument, eg:

  'cake mylibrary\buildmylibrary.cake'.

You can also specify which variant to run by supplying variant keywords, eg:

  'cake platform=windows compiler=msvc'

This will run all variants that build for the windows platform using the msvc compiler.
