"""
Utilities for querying Microsoft Visual Studio settings.
"""
import _winreg

def getMsvsInstallDir(version=r'VisualStudio\8.0'):
  """Returns the MSVS install directory.
  
  This will be a native path or None if MSVS is not installed.

  Typically: 'C:\Program Files\Microsoft Visual Studio 8\Common7\IDE'
  """
  subKey = r"SOFTWARE\Microsoft\%s" % version
  key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, subKey)
  try:
    return str(_winreg.QueryValueEx(key, "InstallDir")[0])
  finally:
    _winreg.CloseKey(key)

def getMsvsProductDir(version=r'VisualStudio\8.0'):
  """Returns the MSVS product directory.
  
  This will be a native path or None if MSVS is not installed.

  Typically: 'C:\Program Files\Microsoft Visual Studio 8\'
  """
  subKey = r"SOFTWARE\Microsoft\%s\Setup\VS" % version
  key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, subKey)
  try:
    return str(_winreg.QueryValueEx(key, "ProductDir")[0])
  finally:
    _winreg.CloseKey(key)

def getMsvcProductDir(version=r'VisualStudio\8.0'):
  """Returns the MSVC product directory as obtained from the registry.

  This will be a native path or None if MSVC is not installed.

  Typically: 'C:\Program Files\Microsoft Visual Studio 8\VC'
  """
  subKey = r"SOFTWARE\Microsoft\%s\Setup\VC" % version
  key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, subKey)
  try:
    return str(_winreg.QueryValueEx(key, "ProductDir")[0])
  finally:
    _winreg.CloseKey(key)

def getPlatformSdkDir():
  
  """Returns the Microsoft Platform SDK directory.

  This will be a native path or None if the PlatformSDK could not be found.
  """
  subKey = r"SOFTWARE\Microsoft\Microsoft SDKs\Windows"
  key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, subKey)
  try:
    return str(_winreg.QueryValueEx(key, "CurrentInstallFolder")[0])
  finally:
    _winreg.CloseKey(key)
