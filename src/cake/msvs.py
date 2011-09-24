"""Utilities for querying Microsoft Visual Studio settings.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""
import _winreg

from cake.registry import queryValue
  
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
  return queryValue(_winreg.HKEY_LOCAL_MACHINE, subKey, "InstallDir")

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
  return queryValue(_winreg.HKEY_LOCAL_MACHINE, subKey, "ProductDir")

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
  return queryValue(_winreg.HKEY_LOCAL_MACHINE, subKey, "ProductDir")

def getPlatformSdkDir():
  """Returns the Microsoft Platform SDK directory.

  @return: The path to the Platform SDK directory.
  @rtype: string 

  @raise WindowsError: If the Platform SDK is not installed. 
  """
  subKey = r"SOFTWARE\Microsoft\Microsoft SDKs\Windows"
  return queryValue(_winreg.HKEY_LOCAL_MACHINE, subKey, "CurrentInstallFolder")

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
  return queryValue(_winreg.HKEY_LOCAL_MACHINE, subKey, valueName)
