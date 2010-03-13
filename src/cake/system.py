"""System Utilities.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import os
import platform as platty

_platform = platty.system()
_isWindows = _platform.lower().startswith('windows')
_isCygwin = _platform.lower().startswith('cygwin')
_isDarwin = _platform.lower().startswith('darwin')

try:
  _architecture = os.environ['PROCESSOR_ARCHITECTURE']
except KeyError:
  _architecture = platty.machine()
  if not _architecture:
    _architecture = 'unknown'

def platform():
  """Returns the current operating system (platform).
  """
  return _platform

def isWindows():
  """Returns True if the current platform is Windows.
  """
  return _isWindows

def isCygwin():
  """Returns True if the current platform is Cygwin.
  """
  return _isCygwin

def isDarwin():
  """Returns True if the current platform is Darwin.
  """
  return _isDarwin

def architecture():
  """Returns the current machines architecture.
  
  @return: The host architecture, or 'unknown' if the host
  architecture could not be determined.
  @rtype: string
  """
  return _architecture
