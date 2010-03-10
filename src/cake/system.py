"""System Utilities.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import os
import platform as platty

try:
  _architecture = os.environ['PROCESSOR_ARCHITECTURE']
except KeyError:
  _architecture = platty.machine()
  if not _architecture:
    _architecture = 'unknown'

def platform():
  """Returns the current operating system (platform).
  """
  return platty.system()

def architecture():
  """Returns the current machines architecture.
  
  @return: The host architecture, or 'unknown' if the host
  architecture could not be determined.
  @rtype: string
  """
  return _architecture
