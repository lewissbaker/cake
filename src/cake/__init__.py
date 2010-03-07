"""Cake Build System.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import threading
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
