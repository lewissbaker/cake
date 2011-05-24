"""Cake Build System.

@var __version__: Version string for Cake. Useful for printing to screen.

@var __version_tuple__: Version tuple for Cake. Useful for comparing
whether one version is newer than another.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import sys

# Define some version strings based on info in the setup.py
# __version__ 
try:
  import pkg_resources
  _pkg = pkg_resources.require("Cake")[0]
  __version__ = _pkg.version
  __version_tuple__ = _pkg.parsed_version
  del _pkg
except Exception:
  __version__ = 'unknown'
  __version_tuple__ = ()

# We want the 'cake.tools' module to have contents based on the current
# thread's Script.
# Cake scripts can get access to their tools using standard python import
# statements.

class ToolsProxy(object):

  def __getattribute__(self, key):
    from cake.engine import Script
    script = Script.getCurrent()
    if script is not None:
      try:
        return script.tools[key]
      except KeyError:
        raise AttributeError("No such tool '%s'" % key)

  def __setattr__(self, key, value):
    from cake.engine import Script
    script = Script.getCurrent()
    if script is not None:
      script.tools[key] = value

tools = ToolsProxy()
"""Cake tools module.

This is the main module for Cake tools. It allows users to import tools
using the standard Python import statement, eg::

  from cake.tools import compiler
  
  compiler.library(target="myLibrary", sources=myObjects) 
"""
sys.modules['cake.tools'] = tools
