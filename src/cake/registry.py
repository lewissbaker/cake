"""Utilities for querying the Windows registry.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""
import _winreg
import cake.system

def queryString(key, subKey, name):
  """Queries a string value from the Windows registry.
  
  On 64-bit Windows this function will first try to query the value from
  the 64-bit registry. If the value doesn't exist there it will then try to
  find the value in the 32-bit registry.
  
  @param key: The key to query, eg: _winreg.HKEY_LOCAL_MACHINE
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
  sams = [_winreg.KEY_READ]
  
  # Also try for a 32-bit registry key on 64-bit Windows. On 64-bit Windows
  # the Windows SDK is usually installed in the 64-bit program files
  # directory but the compiler is usually installed in the 32-bit program
  # files directory.
  if cake.system.isWindows64():
    sams.append(_winreg.KEY_READ | _winreg.KEY_WOW64_32KEY)

  for sam in sams:
    try:
      keyHandle = _winreg.OpenKey(key, subKey, 0, sam)
      try:
        return str(_winreg.QueryValueEx(keyHandle, name)[0])
      finally:
        _winreg.CloseKey(keyHandle)
    except WindowsError:
      if sam is sams[-1]:
        raise
