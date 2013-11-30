"""Utilities for querying Microsoft Visual Studio settings.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""
import _winreg as winreg

import cake.system
from cake.registry import queryString, KEY_WOW64_32KEY
  
def getMsvsInstallDir(version=r'VisualStudio\8.0'):
  """Returns the MSVS install directory.
  
  Typically: 'C:\Program Files\Microsoft Visual Studio 8\Common7\IDE'.
  
  @param version: The registry path used to search for MSVS.
  @type version: string
  
  @return: The path to the MSVS install directory.
  @rtype: string 

  @raise WindowsError: If MSVS is not installed. 
  """
  subKey = r"SOFTWARE\Microsoft\%s" % version
  return queryString(winreg.HKEY_LOCAL_MACHINE, subKey, "InstallDir")

def getMsvsProductDir(version=r'VisualStudio\8.0'):
  """Returns the MSVS product directory.
  
  Typically: 'C:\Program Files\Microsoft Visual Studio 8\'.

  @param version: The registry path used to search for MSVS.
  @type version: string

  @return: The path to the MSVS product directory.
  @rtype: string 

  @raise WindowsError: If MSVS is not installed. 
  """
  subKey = r"SOFTWARE\Microsoft\%s\Setup\VS" % version
  return queryString(winreg.HKEY_LOCAL_MACHINE, subKey, "ProductDir")

def getMsvcProductDir(version=r'VisualStudio\8.0'):
  """Returns the MSVC product directory as obtained from the registry.

  Typically: 'C:\Program Files\Microsoft Visual Studio 8\VC'.

  @param version: The registry path used to search for MSVS.
  @type version: string

  @return: The path to the MSVC product directory.
  @rtype: string 

  @raise WindowsError: If MSVC is not installed. 
  """
  subKey = r"SOFTWARE\Microsoft\%s\Setup\VC" % version
  return queryString(winreg.HKEY_LOCAL_MACHINE, subKey, "ProductDir")

def getDefaultPlatformSdkDir():
  """Returns the Microsoft Platform SDK directory.

  @return: The path to the Platform SDK directory.
  @rtype: string 

  @raise WindowsError: If the Platform SDK is not installed. 
  """
  subKey = r"SOFTWARE\Microsoft\Microsoft SDKs\Windows"
  return queryString(winreg.HKEY_LOCAL_MACHINE, subKey, "CurrentInstallFolder")

def getPlatformSdkVersions():
  """Returns a list of the installed Microsoft Platform SDK versions.
  
  @return: A list of (key, productVersion, path) tuples sorted in reverse
  order of product version.
  @rtype: list of (str, tuple of int, string) tuples.
  """
  key = r"SOFTWARE\Microsoft\Microsoft SDKs\Windows"
  
  # Only bother looking on 32-bit registry as all PlatformSDK's register
  # there, however only some are registered in 64-bit registry.
  if cake.system.isWindows64():
    sam = winreg.KEY_READ | KEY_WOW64_32KEY
  else:
    sam = winreg.KEY_READ
    
  try:
    keyHandle = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key, 0, sam)
  except WindowsError:
    return []

  results = []
  try:
    subKeyCount, valueCount, timestamp = winreg.QueryInfoKey(keyHandle)
    for i in xrange(subKeyCount):
      name = winreg.EnumKey(keyHandle, i)
      subKeyHandle = winreg.OpenKey(keyHandle, name, 0, sam)
      try:
        try:
          installDir = str(winreg.QueryValueEx(subKeyHandle, "InstallationFolder")[0])
          productVersion = str(winreg.QueryValueEx(subKeyHandle, "ProductVersion")[0])
        except WindowsError:
          continue
      finally:
        winreg.CloseKey(subKeyHandle)
      
      productVersionTuple = tuple(int(s) if s.isdigit() else None for s in productVersion.split("."))
      results.append((name, productVersionTuple, installDir))
  finally:
    winreg.CloseKey(keyHandle)
  
  results.sort(key=(lambda x: x[1]), reverse=True)
  return results
  
def getPlatformSdkDir(version=None):
  """Returns the directory of the specified Microsoft Platform SDK version.
  
  @param version: The Platform SDK version to search for.
  @type version: string
  
  @raise WindowsError: If this version of the Platform SDK is not installed.
  """
  
  subKey = r"SOFTWARE\Microsoft\Microsoft SDKs\Windows\%s" % version
  return queryString(winreg.HKEY_LOCAL_MACHINE, subKey, "InstallationFolder")
  
def getDotNetFrameworkSdkDir(version='2.0'):
  """Looks up the path of the Microsoft .NET Framework SDK directory.

  @param version: The .NET Framework version to search for.
  @type version: string

  @return: The path to the .NET Framework SDK root directory.
  @rtype: string

  @raise WindowsError: If the .NET Framework SDK is not installed.
  """
  subKey = r"SOFTWARE\Microsoft\.NETFramework"
  valueName = "sdkInstallRootv" + version
  return queryString(winreg.HKEY_LOCAL_MACHINE, subKey, valueName)
