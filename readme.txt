Cake Build System (http://sourceforge.net/projects/cake-build)

Description
-----------

A relatively fast build system written in Python.

Features
--------

- Platorm support
  - Windows
  - Cygwin
- Compiler support
  - Visual Studio 2005/2008
  - Visual C++ Express
  - WindowsSDK
  - GCC
  - MinGW
- Build Variants
- Object file cache
- Multi-threaded builds
- Basic shell commands

Upcoming Features
-----------------

- Visual Studio Project Generation
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

boot.cake
=========

When Cake starts it will search for a 'boot.cake' file starting from the directory of the 'build.cake' script it is trying to execute. This file should generally be located in your projects root directory.

The quickest way to create a boot.cake file is to copy examples/boot.cake. The example boot file supports automatic detection of MSVC, MinGW and Gcc compilers, and two development modes, 'debug' and 'release'.

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

You can debug the build by using the '-d' option with any of the available debug keywords, eg:

  'cake -d run'

Will output the command lines that Cake runs.

  'cake -d reason'

Will output the reason cake is rebuilding your files (ie. what has changed).

Known Issues
------------

- There is an issue when trying to use outer scoped variables/imports within an inner scope in a cake script.

- Preprocessing and compiling are currently done separately. This can almost double the time of a full rebuild. In the future we will attempt to combine this into one stage for compilers that some form of support dependency output.

- The object cache currently requires preprocessing to determine what files have changed. In the future a set of cached versions each with their own dependencies may be used to prevent the preprocessing step and speed up cached object builds.

- There is no support for building a module (DLL) with import library under CodeWarrior.

- There is no support for finding a CodeWarrior compiler automatically, eg. mwcw.findCodeWarriorCompiler().

