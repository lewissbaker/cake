"""Utilities for querying the Windows registry.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""
import _winreg as winreg # Do this so Python 2to3 conversion works.
import sys

import cake.system

_shownWow64Warning = False

# Define locally here since some versions of the winreg module don't have them
KEY_WOW64_64KEY = 0x0100
KEY_WOW64_32KEY = 0x0200

if cake.system.isWindows64():
  _readAccessModes = (winreg.KEY_READ | KEY_WOW64_64KEY, winreg.KEY_READ | KEY_WOW64_32KEY)
else:
  _readAccessModes = (winreg.KEY_READ,)

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

  @raise WindowsError: If the value could not be found/read.
  """
  for sam in _readAccessModes:
    try:
      keyHandle = winreg.OpenKey(key, subKey, 0, sam)
      try:
        return str(winreg.QueryValueEx(keyHandle, name)[0])
      finally:
        winreg.CloseKey(keyHandle)
    except WindowsError:
      if sam is _readAccessModes[-1]:
        raise
