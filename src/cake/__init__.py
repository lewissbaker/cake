"""Cake Build System.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import sys

# We want the 'cake.tools' module to have contents based on the current
# thread's Script.
# Cake scripts can get access to their tools using standard python import
# statements.

class ToolsProxy(object):

  def __getattribute__(self, key):
    from cake.script import Script
    script = Script.getCurrent()
    if script is None:
      raise AttributeError("No current script.")
    else:
      try:
        return script.tools[key]
      except KeyError:
        raise AttributeError("No such tool '%s'" % key)

  def __setattr__(self, key, value):
    from cake.script import Script
    script = Script.getCurrent()
    if script is None:
      raise AttributeError("No current script.")
    else:
      script.tools[key] = value

tools = ToolsProxy()
"""Cake tools module.

This is the main module for Cake tools. It allows users to import tools
using the standard Python import statement, eg::

  from cake.tools import compiler
  
  compiler.library(target="myLibrary", sources=myObjects) 
"""
sys.modules['cake.tools'] = tools
