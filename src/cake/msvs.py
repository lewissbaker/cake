"""Utilities for querying Microsoft Visual Studio settings.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""
import json
import os
import subprocess
import _winreg as winreg
import codecs

import cake.path
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
  if version:
    subKey = r"SOFTWARE\Microsoft\Microsoft SDKs\Windows\%s" % version
    valueName = "InstallationFolder"
  else:
    subKey = r"SOFTWARE\Microsoft\Microsoft SDKs\Windows"
    valueName = "CurrentInstallFolder"
  return queryString(winreg.HKEY_LOCAL_MACHINE, subKey, valueName)

def getWindowsKitsDir(version='80'):
  """Returns the Microsoft Windows Kit directory.
  
  @param version: The version of the SDK to look-up.
  @type version: string
  
  @return: The path to the Windows Kit directory.
  @rtype: string
  
  @raise WindowsError: If this version of the Platform SDK is not installed.
  """
  subKey = r"SOFTWARE\Microsoft\Windows Kits\Installed Roots"
  valueName = 'KitsRoot' if version == '80' else 'KitsRoot' + version
  return queryString(winreg.HKEY_LOCAL_MACHINE, subKey, valueName)

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

try:
  import ctypes
  import ctypes.wintypes

  _GetConsoleOutputCP = ctypes.windll.kernel32.GetConsoleOutputCP
  _GetConsoleOutputCP.argtypes = []
  _GetConsoleOutputCP.restype = ctypes.wintypes.UINT

  # Constructed from translating between:
  # https://docs.microsoft.com/en-gb/windows/desktop/Intl/code-page-identifiers
  # and
  # https://docs.python.org/2.4/lib/standard-encodings.html
  _codepageToCodec = {
    950 : "big5",
    1200 : "utf_16_le",
    1201 : "utf_16_be",
    12000 : "utf_32_le",
    12001 : "utf_32_be",
    20127 : "us-ascii",
    28591 : "latin_1",
    28592 : "iso8859_2",
    28593 : "iso8859_3",
    28594 : "iso8859_4",
    28595 : "iso8859_5",
    28596 : "iso8859_6",
    28597 : "iso8859_7",
    28598 : "iso8859_8",
    28599 : "iso8859_9",
    28603 : "iso8859_13",
    28605 : "iso8859_15",
    65000 : "utf_7",
    65001 : "utf_8",
    }

  def _getCodecFromCodepage():
    codepage = _GetConsoleOutputCP()
    codecName = _codepageToCodec.get(codepage, None)
    if codecName is None:
      codecName = "cp{0:03}".format(codepage)

    try:
      return codecs.lookup(codecName)
    except LookupError:
      return None

except Exception:

  def _getCodecFromCodepage():
    return None

def vswhere(args=[]):
  """Helper function for running vswhere helper utility and parsing the output.

  The vswhere utility can be used to find the installation locations of Visual Studio 2017 or later.
  It can also be used to find older install locations by passing "-legacy" as an argument.

  @return: An array of dictionaries containing information about each installation.

  @raise EnvironmentError:
  If there was a problem running vswhere with the provided arguments.
  """
  if cake.system.isWindows64():
    programFiles = os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')
  else:
    programFiles = os.environ.get('ProgramFiles', r'C:\Program Files')
  vsInstaller = cake.path.join(programFiles, 'Microsoft Visual Studio', 'Installer')
  vsWherePath = cake.path.join(vsInstaller, 'vswhere.exe')
  if not os.path.isfile(vsWherePath):
    raise EnvironmentError("vswhere not found at " + vsWherePath)

  p = subprocess.Popen(
    args=["vswhere", "-format", "json", "-utf8"] + args,
    executable=vsWherePath,
    cwd=vsInstaller,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    stdin=subprocess.PIPE,
    )
  out, err = p.communicate(input=b"")
  codec = codecs.lookup("utf_8")

  if p.returncode != 0:
    # Probably failed because it's an old version of vswhere that doesn't support
    # -utf8 flag. Let's try using it without -utf8 and then use whatever the current
    # Windows codepage is to decode it.
    p = subprocess.Popen(
      args=["vswhere", "-format", "json"] + args,
      executable=vsWherePath,
      cwd=vsInstaller,
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
      stdin=subprocess.PIPE,
      )
    out, err = p.communicate(input=b"")
    codec = _getCodecFromCodepage()
    if codec is None:
      # Fall back to ASCII if we couldn't figure out the codec for
      # the current Windows codepage.
      codec = codecs.lookup("ascii")

    if p.returncode != 0:
      raise EnvironmentError("vswhere: returned with exit code " + str(p.returncode) + "\n" + out) 

  return json.loads(codec.decode(out, 'replace')[0])
