"""System Utilities.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import os
import os.path
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

if isCygwin():
  def findExecutable(name, paths):
    """Find an executable given its name and a list of paths.  
    """
    for p in paths:
      executable = os.path.join(p, name)
      if os.path.isfile(executable):
        # On cygwin it can sometimes say a file exists at a path
        # when its real filename includes a .exe on the end.
        # We detect this by actually trying to open the path
        # for read, if it fails we know it should have a .exe.
        try:
          f = open(executable, 'rb')
          f.close()
          return executable
        except EnvironmentError:
          return executable + '.exe'
    else:
      raise EnvironmentError("Could not find executable.")
    
elif isWindows():
  def findExecutable(name, paths):
    """Find an executable given its name and a list of paths.  
    """
    # Windows executables could have any of a number of extensions
    # We just search through standard extensions so that we're not
    # dependent on the user's environment.
    pathExt = ['', '.bat', '.exe', '.com', '.cmd']
    for p in paths:
      basePath = os.path.join(p, name)
      for ext in pathExt:
        executable = basePath + ext
        if os.path.isfile(executable):
          return executable
    else:
      raise EnvironmentError("Could not find executable.")
    
else:
  def findExecutable(name, paths):
    """Find an executable given its name and a list of paths.  
    """
    for p in paths:
      executable = os.path.join(p, name)
      if os.path.isfile(executable):
        return executable
    else:
      raise EnvironmentError("Could not find executable.")
