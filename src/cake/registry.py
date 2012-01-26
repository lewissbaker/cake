"""Utilities for querying the Windows registry.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""
import _winreg as winreg # Do this so Python 2to3 conversion works.
import sys

import cake.system

_shownWow64Warning = False

def queryString(key, subKey, name):
  """Queries a string value from the Windows registry.
  
  On 64-bit Windows this function will first try to query the value from
  the 64-bit registry. If the value doesn't exist there it will then try to
  find the value in the 32-bit registry.
  
  @param key: The key to query, eg: winreg.HKEY_LOCAL_MACHINE
  @type key: string
  
  @param subKey: The subkey to query, eg: r"SOFTWARE\Microsoft"
  @type subKey: string
  
  @param name: The name to query, eg: "InstallDir"
  @type name: string
  
  @return: The value queried.
  @rtype: string 

  @raise WindowsError: If the value could not be found. 
  """
  # List of access modes to try.
  sams = [winreg.KEY_READ]
  
  # Also try for a 32-bit registry key on 64-bit Windows. On 64-bit Windows
  # the Windows SDK is usually installed in the 64-bit program files
  # directory but the compiler is usually installed in the 32-bit program
  # files directory.
  if cake.system.isWindows64():
    if hasattr(winreg, "KEY_WOW64_32KEY"):
      sams.append(winreg.KEY_READ | winreg.KEY_WOW64_32KEY)
    else:
      global _shownWow64Warning
      if not _shownWow64Warning:
        _shownWow64Warning = True
        sys.stderr.write(
          "warning: winreg module does not have access key KEY_WOW64_32KEY. "
          "It may not be possible to find all compiler and SDK install "
          "locations automatically.\n"
          )

  for sam in sams:
    try:
      keyHandle = winreg.OpenKey(key, subKey, 0, sam)
      try:
        return str(winreg.QueryValueEx(keyHandle, name)[0])
      finally:
        winreg.CloseKey(keyHandle)
    except WindowsError:
      if sam is sams[-1]:
        raise
