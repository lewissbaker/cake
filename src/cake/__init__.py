"""Cake Build System.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import threading
import platform
import sys

__version_info__ = (0, 9, 0)
"""Current version number tuple.

The number uses semantic versioning (see U{http://semver.org}).
"""
__version__ = '.'.join(str(v) for v in __version_info__)

# We want the 'cake.tools' module to have thread-local contents so that
# Cake scripts can get access to their tools using standard python import
# statements. 
tools = threading.local()
"""Cake tools module.

This is the main module for Cake tools. It allows users to import tools
using the standard Python import statement, eg::

  from cake.tools import compiler
  
  compiler.library(target="myLibrary", sources=myObjects) 
"""
sys.modules['cake.tools'] = tools

def _overrideOpen():
  """
  Override the built-in open() and os.open() to set the no-inherit
  flag on files to prevent processes from inheriting file handles.
  """
  import __builtin__
  import os
  
  def new_open(filename, mode="r", bufsize=0):
    if mode.startswith("r"):
      flags = os.O_RDONLY
    elif mode.startswith("w"):
      flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    elif mode.startswith("a"):
      flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    else:
      flags = os.O_RDONLY
      mode = 'r' + mode
    
    for ch in mode[1:]:
      if ch == "+":
        flags |= os.O_RDWR
        flags &= ~(os.O_RDONLY | os.O_WRONLY)
      elif ch == "t":
        flags |= os.O_TEXT
      elif ch == "b":
        flags |= os.O_BINARY
      elif ch in " ,":
        pass
      elif ch == "U":
        pass # Universal newline support
      elif ch == "N":
        flags |= os.O_NOINHERIT
      elif ch == "D":
        flags |= os.O_TEMPORARY
      elif ch == "T":
        flags |= os.O_SHORT_LIVED
      elif ch == "S":
        flags |= os.O_SEQUENTIAL
      elif ch == "R":
        flags |= os.O_RANDOM
      else:
        raise ValueError("unknown flag '%s' in mode" % ch)

    if flags & os.O_BINARY and flags & os.O_TEXT:
      raise ValueError("Cannot specify both 't' and 'b' in mode")
    #if flags & os.O_SEQUENTIAL and flags & os.O_RANDOM:
    #  raise ValueError("Cannot specify both 'S' and 'R' in mode")

    try:
      fd = os.open(filename, flags)
      return os.fdopen(fd, mode, bufsize)
    except OSError, e:
      raise IOError(str(e))
  __builtin__.open = new_open

  old_os_open = os.open
  def new_os_open(filename, flag, mode=0777):
    flag |= os.O_NOINHERIT
    return old_os_open(filename, flag, mode)
  os.open = new_os_open
  
_overrideOpen()

def _speedUp():
  """
  Speed up execution by importing Psyco and binding the slowest functions
  with it.
  """
  try:
    import psyco
    import engine
    psyco.bind(engine.DependencyInfo.isUpToDate)
    #psyco.full()
    #psyco.profile()
    #psyco.log()
  except ImportError:
    # Only report import failures on systems we know Psyco supports.
    if platform.system() == "Windows":
      sys.stderr.write(
        "warning: Psyco is not installed. Installing it may halve your incremental build time.\n"
        )

_speedUp()
