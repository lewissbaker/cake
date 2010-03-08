"""System Utilities.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import os
import platform

def getHostArchitecture():
  """Returns the current machines architecture.
  
  @return: The host architecture, or 'unknown' if the host
  architecture could not be determined.
  @rtype: string
  """
  try:
    architecture = os.environ['PROCESSOR_ARCHITECTURE'].lower()
    return {"amd64":"x64"}.get(architecture, architecture)
  except KeyError:
    architecture = platform.machine()
    if architecture:
      return architecture
    else:
      return 'unknown'
