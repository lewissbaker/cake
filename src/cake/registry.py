"""Utilities for querying the Windows registry.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""
import _winreg
import cake.system

def queryValue(key, sub_key, name):
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
      keyHandle = _winreg.OpenKey(key, sub_key, 0, sam)
      try:
        return str(_winreg.QueryValueEx(keyHandle, name)[0])
      finally:
        _winreg.CloseKey(keyHandle)
    except WindowsError:
      if sam is sams[-1]:
        raise
