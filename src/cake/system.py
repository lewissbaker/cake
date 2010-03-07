"""System Utilities.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import os
import platform

if platform.system() == 'Windows':
  import ctypes
  import ctypes.wintypes
  
  kernel32 = ctypes.windll.kernel32
  IsWow64Process = kernel32.IsWow64Process
  IsWow64Process.restype = ctypes.wintypes.BOOL
  IsWow64Process.argtypes = (ctypes.wintypes.HANDLE,
                             ctypes.POINTER(ctypes.wintypes.BOOL))
  
  GetCurrentProcess = kernel32.GetCurrentProcess
  GetCurrentProcess.restype = ctypes.wintypes.HANDLE
  GetCurrentProcess.argtypes = ()
  
  def getHostArchitecture():
    """Returns the current machines architecture.
    
    @return: The host architecture, or 'unknown' if the host
    architecture could not be determined.
    @rtype: string
    """
    if platform.architecture()[0] == '32bit':
      # Could be a 32-bit process running under 64-bit OS
      result = ctypes.wintypes.BOOL()
      ok = IsWow64Process(GetCurrentProcess(), ctypes.byref(result))
      if not ok:
        raise WindowsError("IsWow64Process")
  
      if result.value == 1:
        return "x64"
      else:
        return "x86"
    else:
      # Could be IA-64 but who uses that these days?
      return "x64"
else:
  # Non-windows platforms
  def getHostArchitecture():
    """Returns the current machines architecture.
    
    @return: The host architecture, or 'unknown' if the host
    architecture could not be determined.
    @rtype: string
    """
    try:
      return os.environ['PROCESSOR_ARCHITECTURE']
    except KeyError:
      return platform.machine()
