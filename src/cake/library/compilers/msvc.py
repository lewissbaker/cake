"""The Microsoft Visual C++ Compiler.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import os
import os.path
import re
import threading

import cake.filesys
import cake.path
import cake.system
from cake.library.compilers import Compiler, makeCommand, CompilerNotFoundError
from cake.library import memoise
from cake.target import getPaths, getTasks
from cake.msvs import getMsvcProductDir, getMsvsInstallDir, getPlatformSdkVersions, getWindowsKitsDir, vswhere

def _toArchitectureDir(architecture):
  """Re-map 'x64' to 'amd64' to match MSVC directory names.
  """
  return {'x64':'amd64'}.get(architecture, architecture)

def _createMsvcCompiler(
  configuration,
  version,
  edition,
  architecture,
  hostArchitecture,
  windowsSdkDir,
  ):
  """Attempt to create an MSVC compiler.
  
  @raise WindowsError: If the compiler could not be created.
  @return: The newly created compiler.
  @rtype: L{MsvcCompiler}
  """
  msvsRegistryPath = edition + '\\' + version
  msvcRegistryPath = msvsRegistryPath
  if edition == "WDExpress":
    msvcRegistryPath = "VisualStudio\\" + version

  msvsInstallDir = getMsvsInstallDir(msvsRegistryPath)
  msvcProductDir = getMsvcProductDir(msvcRegistryPath)

  msvcRootBinDir = cake.path.join(msvcProductDir, "bin")
  
  if architecture == 'x86':
    # Root bin directory is always used for the x86 compiler
    msvcBinDir = msvcRootBinDir
  else:
    msvcArchitecture = _toArchitectureDir(architecture)
    msvcHostArchitecture = _toArchitectureDir(hostArchitecture)
    
    if msvcArchitecture != msvcHostArchitecture:
      # Determine the bin directory for cross-compilers
      msvcBinDir = cake.path.join(
        msvcRootBinDir,
        "%s_%s" % (
          msvcHostArchitecture,
          msvcArchitecture,
          ),
        )
    else:
      # Try native compiler for target architecture first
      msvcBinDir = cake.path.join(
        msvcRootBinDir,
        "%s" % msvcArchitecture,
        )
      # Fall back to x86 cross-compiler for target architecture if on amd64 machine.
      if not cake.filesys.isDir(msvcBinDir) and msvcHostArchitecture == 'amd64':
        msvcBinDir = cake.path.join(
          msvcRootBinDir,
          "x86_%s" % (
            msvcArchitecture,
            ),
          )
          
  # Find the host bin dir for exe's such as 'cvtres.exe'
  if hostArchitecture == 'x86':
    msvcHostBinDir = msvcRootBinDir
  else:
    msvcHostBinDir = cake.path.join(msvcRootBinDir, _toArchitectureDir(hostArchitecture))
    if not cake.filesys.isDir(msvcHostBinDir):
      msvcHostBinDir = msvcRootBinDir

  msvcIncludeDirs = [cake.path.join(msvcProductDir, "include")]
  msvcLibDirs = []
  if architecture == 'x86':
    msvcLibDirs.append(cake.path.join(msvcProductDir, "lib"))
  elif architecture in ['x64', 'amd64']:
    msvcLibDirs.append(cake.path.join(msvcProductDir, "lib", "amd64"))
  elif architecture == 'ia64':
    msvcLibDirs.append(cake.path.join(msvcProductDir, "lib", "ia64"))

  if version == '14.0':
    # Visual Studio 2015 separates out some of the CRT into a separate area
    # under the Windows Kit 10. The Univercal C Run-time (ucrt).
    windowsKit10Dir = getWindowsKitsDir(version='10')
    windowsKit10LibArch = architecture
    if architecture == 'amd64':
      windowsKit10LibArch = 'x64'
    # HACK: Should really allow the caller to specify the desired Universal CRT version somehow.
    msvcIncludeDirs.append(cake.path.join(windowsKit10Dir, 'include', '10.0.10150.0', 'ucrt'))
    msvcLibDirs.append(cake.path.join(windowsKit10Dir, 'Lib', '10.0.10150.0', 'ucrt', windowsKit10LibArch))

  # Try using the compiler's platform SDK if none explicitly specified
  compilerPlatformSdkDir = cake.path.join(msvcProductDir, "PlatformSDK")
  compilerPlatformSdkIncludeDir = cake.path.join(compilerPlatformSdkDir, "Include")
  if architecture == 'x86':
    compilerPlatformSdkLibDir = cake.path.join(compilerPlatformSdkDir, "Lib")
  elif architecture in ['x64', 'amd64']:
    compilerPlatformSdkLibDir = cake.path.join(compilerPlatformSdkDir, "Lib", "x64")
  elif architecture == 'ia64':
    compilerPlatformSdkLibDir = cake.path.join(compilerPlatformSdkDir, "Lib", "IA64")

  if windowsSdkDir:
    windowsSdkIncludeDir = cake.path.join(windowsSdkDir, "Include")
    windowsSdkRootBinDir = cake.path.join(windowsSdkDir, "Bin")
    if architecture == 'x86':
      windowsSdkLibDir = cake.path.join(windowsSdkDir, "Lib")
      windowsSdkBinDir = windowsSdkRootBinDir
    elif architecture in ['x64', 'amd64']:
      # External Platform SDKs may use 'x64' instead of 'amd64'
      windowsSdkLibDir = cake.path.join(windowsSdkDir, "Lib", "x64")
      windowsSdkBinDir = cake.path.join(windowsSdkRootBinDir, "x64")
    elif architecture == 'ia64':
      windowsSdkLibDir = cake.path.join(windowsSdkDir, "Lib", "IA64")
      windowsSdkBinDir = cake.path.join(windowsSdkRootBinDir, "IA64")

  # TODO: Add support for Windows Kit as an alternative Windows SDK.

  # Use compiler's PlatformSDK in preference to Windows SDK
  if cake.filesys.isDir(compilerPlatformSdkLibDir) or not windowsSdkDir:
    platformSdkIncludeDir = compilerPlatformSdkIncludeDir
    platformSdkLibDir = compilerPlatformSdkLibDir
  else:
    platformSdkIncludeDir = cake.path.join(windowsSdkDir, "Include")
    platformSdkLibDir = windowsSdkLibDir

  clExe = cake.path.join(msvcBinDir, "cl.exe")
  libExe = cake.path.join(msvcBinDir, "lib.exe")
  linkExe = cake.path.join(msvcBinDir, "link.exe")
  
  bscExe = cake.path.join(msvcRootBinDir, "bscmake.exe")

  rcExe = cake.path.join(msvcBinDir, "rc.exe")
  if not cake.filesys.isFile(rcExe):
    rcExe = cake.path.join(msvcRootBinDir, "rc.exe")
  if windowsSdkDir and not cake.filesys.isFile(rcExe):
    # Should we by trying platform-specific directories here?
    rcExe = cake.path.join(windowsSdkRootBinDir, "rc.exe")

  mtExe = cake.path.join(msvcBinDir, "mt.exe")
  if not cake.filesys.isFile(mtExe):
    mtExe = cake.path.join(msvcRootBinDir, "mt.exe")
  if windowsSdkDir and not cake.filesys.isFile(mtExe):
    # Should we by trying platform-specific directories here?
    mtExe = cake.path.join(windowsSdkRootBinDir, "mt.exe")

  def checkFile(path):
    if not cake.filesys.isFile(path):
      raise WindowsError(path + " is not a file.")

  def checkDirectory(path):
    if not cake.filesys.isDir(path):
      raise WindowsError(path + " is not a directory.")

  checkFile(clExe)
  checkFile(libExe)
  checkFile(linkExe)
  checkFile(rcExe)
  checkFile(mtExe)
  if not cake.filesys.isFile(bscExe):
    bscExe = None # Not fatal. This just means we can't build browse info files.

  for msvcIncludeDir in msvcIncludeDirs:
    checkDirectory(msvcIncludeDir)
  for msvcLibDir in msvcLibDirs:
    checkDirectory(msvcLibDir)
  checkDirectory(platformSdkIncludeDir)
  checkDirectory(platformSdkLibDir)
  
  binPaths = [msvcHostBinDir, msvsInstallDir]
  includePaths = msvcIncludeDirs + [platformSdkIncludeDir]
  libraryPaths = msvcLibDirs + [platformSdkLibDir]

  compiler = MsvcCompiler(
    configuration=configuration,
    clExe=clExe,
    libExe=libExe,
    linkExe=linkExe,
    rcExe=rcExe,
    mtExe=mtExe,
    bscExe=bscExe,
    binPaths=binPaths,
    includePaths=includePaths,
    libraryPaths=libraryPaths,
    architecture=architecture,
    )
  
  return compiler

def _toVersionTuple(versionString):
  """Split a version string like "10.5.0.2345" into a tuple (10, 5, 0, 2345).
  """
  return tuple((int(part) if part.isdigit() else part)
               for part in versionString.split("."))

class WindowsSdkInfo(object):

  def __init__(self, version, architecture):
    self.version = version
    self.architecture = architecture
    self.includeDirs = []
    self.libDirs = []
    self.binDir = None

class UniversalCRuntimeInfo(object):

  def __init__(self, version, architecture):
    self.version = version
    self.architecture = architecture
    self.includeDirs = []
    self.libDirs = []

def findWindows10Sdks(windowsKits10Dir=None, targetArchitecture=None):
  if windowsKits10Dir is None:
    windowsKits10Dir = getWindowsKitsDir(version='10')

  includeBase = cake.path.join(windowsKits10Dir, 'Include')
  libBase = cake.path.join(windowsKits10Dir, 'Lib')
  binBase = cake.path.join(windowsKits10Dir, 'bin')

  if cake.system.isWindows64():
    binArch = "x64"
  else:
    binArch = "x86"

  results = []

  if not os.path.isdir(libBase) or not os.path.isdir(includeBase) or not os.path.isdir(binBase):
    return results

  versions = os.listdir(libBase)
  versions.sort(key=_toVersionTuple, reverse=True)

  for version in versions:
    binDir = cake.path.join(binBase, version, binArch)
    if not os.path.isdir(binDir):
      binDir = cake.path.join(binBase, binArch)

    umLibBase = os.path.join(libBase, version, 'um')

    umIncludeDir = os.path.join(includeBase, version, 'um')
    sharedIncludeDir = os.path.join(includeBase, version, 'shared')

    if all(os.path.isdir(p) for p in (umLibBase, umIncludeDir, sharedIncludeDir)):
      if targetArchitecture:
        architectures = [targetArchitecture]
      else:
        architectures = os.listdir(umLibBase)

      for architecture in architectures:
        umLibDir = os.path.join(umLibBase, architecture)
        if os.path.isdir(umLibDir):
          info = WindowsSdkInfo(version, architecture)
          info.includeDirs.extend([umIncludeDir, sharedIncludeDir])
          info.libDirs.append(umLibDir)
          info.binDir = binDir
          results.append(info)

  return results

def findUniversalCRuntimes(windowsKits10Dir=None, targetArchitecture=None):
  if windowsKits10Dir is None:
    windowsKits10Dir = getWindowsKitsDir(version='10')

  includeBase = cake.path.join(windowsKits10Dir, 'Include')
  libBase = cake.path.join(windowsKits10Dir, 'Lib')

  results = []

  if not os.path.isdir(libBase) or not os.path.isdir(includeBase):
    return results

  versions = os.listdir(libBase)
  versions.sort(key=_toVersionTuple, reverse=True)

  for version in versions:
    ucrtLibBase = os.path.join(libBase, version, 'ucrt')
    ucrtIncludeDir = os.path.join(includeBase, version, 'ucrt')

    if all(os.path.isdir(p) for p in (ucrtLibBase, ucrtIncludeDir)):
      if targetArchitecture:
        architectures = [targetArchitecture]
      else:
        architectures = os.listdir(ucrtLibBase)

      for architecture in architectures:
        ucrtLibDir = os.path.join(ucrtLibBase, architecture)
        if os.path.isdir(ucrtLibDir):
          info = UniversalCRuntimeInfo(version, architecture)
          info.includeDirs.append(ucrtIncludeDir)
          info.libDirs.append(ucrtLibDir)
          results.append(info)

  return results

def findMsvc2017InstallDir(targetArchitecture, allowPreRelease=False):
  """Find the location of the MSVC 2017 install directory.

  Returns path of the latest VC install directory that contains a compiler
  for the specified target architecture. Throws CompilerNotFoundError if
  couldn't find any MSVC 2017 version.
  """
  vswhereArgs = ["-version", "[15.0,16.0)"]
  if allowPreRelease:
    vswhereArgs.append("-prerelease")
  infos = vswhere(vswhereArgs)
  infos.sort(key=lambda info: _toVersionTuple(info.get("installationVersion", "0")), reverse=True)

  for info in infos:
    vsInstallDir = info["installationPath"]
    msvcBasePath = cake.path.join(vsInstallDir, r'VC\Tools\MSVC')
    if os.path.isdir(msvcBasePath):
      versions = os.listdir(msvcBasePath)
      versions.sort(key=_toVersionTuple, reverse=True)
      for version in versions:
        msvcPath = cake.path.join(msvcBasePath, version)
        if cake.system.isWindows64():
          if os.path.isdir(cake.path.join(msvcPath, 'bin', 'HostX64', targetArchitecture)):
            return msvcPath
        else:
          if os.path.isdir(cake.path.join(msvcPath, 'bin', 'HostX86', targetArchitecture)):
            return msvcPath
  else:
    raise CompilerNotFoundError()


def getVisualStudio2015Compiler(configuration, targetArchitecture, ucrtInfo=None, windowsSdkInfo=None, vcInstallDir=None):

  if vcInstallDir is None:
    vcInstallDir = getMsvcProductDir("VisualStudio\\14.0")

  if windowsSdkInfo is None:
    windowsSdks = findWindows10Sdks(targetArchitecture=targetArchitecture)
    if not windowsSdks:
      raise CompilerNotFoundError("Windows 10 SDK not found")
    windowsSdkInfo = windowsSdks[0]

  if ucrtInfo is None:
    ucrtInfos = findUniversalCRuntimes(targetArchitecture=targetArchitecture)
    if not ucrtInfos:
      raise CompilerNotFoundError("Universal C Runtime library not found")
    ucrtInfo = ucrtInfos[0]

  if cake.system.isWindows64():
    vcNativeBinDir = cake.path.join(vcInstallDir, "bin", "amd64")
  else:
    vcNativeBinDir = cake.path.join(vcInstallDir, "bin")

  vcIncludeDir = cake.path.join(vcInstallDir, "include")

  if targetArchitecture == "x64":
    if cake.system.isWindows64():
      vcBinDir = vcNativeBinDir
    else:
      vcBinDir = cake.path.join(vcInstallDir, "bin", "x86_amd64")
    vcLibDir = cake.path.join(vcInstallDir, "lib", "amd64")
  elif targetArchitecture == "x86":
    if cake.system.isWindows64():
      vcBinDir = cake.path.join(vcInstallDir, "bin", "amd64_x86")
    else:
      vcBinDir = vcNativeBinDir
    vcLibDir = cake.path.join(vcInstallDir, "lib")

  vcBinPaths = [vcBinDir]
  if vcNativeBinDir != vcBinDir:
    vcBinPaths.append(vcNativeBinDir)

  return MsvcCompiler(
    configuration=configuration,
    clExe=cake.path.join(vcBinDir, "cl.exe"),
    libExe=cake.path.join(vcBinDir, "lib.exe"),
    linkExe=cake.path.join(vcBinDir, "link.exe"),
    rcExe=cake.path.join(windowsSdkInfo.binDir, "rc.exe"),
    mtExe=cake.path.join(windowsSdkInfo.binDir, "mt.exe"),
    bscExe=None,
    binPaths=vcBinPaths + [windowsSdkInfo.binDir],
    includePaths=[vcIncludeDir] + ucrtInfo.includeDirs + windowsSdkInfo.includeDirs,
    libraryPaths=[vcLibDir] + ucrtInfo.libDirs + windowsSdkInfo.libDirs,
    architecture=targetArchitecture,
    )

def getVisualStudio2017Compiler(configuration, targetArchitecture=None, ucrtInfo=None, windowsSdkInfo=None, vcInstallDir=None):

  if targetArchitecture is None:
    if cake.system.isWindows64():
      targetArchitecture = "x64"
    else:
      targetArchitecture = "x86"

  if vcInstallDir is None:
    vcInstallDir = str(findMsvc2017InstallDir(targetArchitecture))

  if windowsSdkInfo is None:
    windowsSdks = findWindows10Sdks(targetArchitecture=targetArchitecture)
    if not windowsSdks:
      raise CompilerNotFoundError("Windows 10 SDK not found")
    windowsSdkInfo = windowsSdks[0]

  if ucrtInfo is None:
    ucrtInfos = findUniversalCRuntimes(targetArchitecture=targetArchitecture)
    if not ucrtInfos:
      raise CompilerNotFoundError("Universal C Runtime library not found")
    ucrtInfo = ucrtInfos[0]

  vcIncludeDir = cake.path.join(vcInstallDir, "include")

  if cake.system.isWindows64():
    vcNativeBinDir = cake.path.join(vcInstallDir, "bin", "HostX64", "x64")
  else:
    vcNativeBinDir = cake.path.join(vcInstallDir, "bin", "HostX86", "x86")

  if targetArchitecture == "x64":
    if cake.system.isWindows64():
      vcBinDir = vcNativeBinDir
    else:
      vcBinDir = cake.path.join(vcInstallDir, "bin", "HostX86", "x64")
    vcLibDir = cake.path.join(vcInstallDir, "lib", "x64")
  elif targetArchitecture == "x86":
    if cake.system.isWindows64():
      vcBinDir = cake.path.join(vcInstallDir, "bin", "HostX64", "x86")
    else:
      vcBinDir = vcNativeBinDir
    vcLibDir = cake.path.join(vcInstallDir, "lib", "x86")

  binPaths = [vcBinDir]
  if vcNativeBinDir != vcBinDir:
    binPaths.append(vcNativeBinDir)
  binPaths.append(windowsSdkInfo.binDir)

  return MsvcCompiler(
    configuration=configuration,
    clExe=cake.path.join(vcBinDir, "cl.exe"),
    libExe=cake.path.join(vcBinDir, "lib.exe"),
    linkExe=cake.path.join(vcBinDir, "link.exe"),
    rcExe=cake.path.join(windowsSdkInfo.binDir, "rc.exe"),
    mtExe=cake.path.join(windowsSdkInfo.binDir, "mt.exe"),
    bscExe=None,
    binPaths=binPaths,
    includePaths=[vcIncludeDir] + ucrtInfo.includeDirs + windowsSdkInfo.includeDirs,
    libraryPaths=[vcLibDir] + ucrtInfo.libDirs + windowsSdkInfo.libDirs,
    architecture=targetArchitecture,
    )

def findMsvcCompiler(
  configuration,
  version=None,
  architecture=None,
  ):
  """Returns an MSVC compiler given a version and architecture.
  
  Raises an EnvironmentError if a compiler or matching platform SDK
  cannot be found.
  
  @param version: The specific version to find. If version is None the
  latest version is found instead. 
  @param architecture: The machine architecture to compile for. If it's
  None an architecture that is a closest match to the host architecture
  is used.
  
  @return: A newly created MSVC compiler.
  @rtype: L{MsvcCompiler}
  
  @raise ValueError: When an invalid version or architecture is passed in.
  @raise CompilerNotFoundError: When a valid compiler or Windows SDK
  could not be found.
  """
  
  validArchitectures = ['x86', 'x64', 'amd64', 'ia64']

  # Valid versions - prefer later versions over earlier ones
  versions = [
    '14.0',
    '12.0',
    '11.0',
    '10.0',
    '9.0',
    '8.0',
    '7.1',
    '7.0',
    ]

  # Valid editions - prefer Enterprise edition over Express
  editions = [
    'VisualStudio',
    'VCExpress',
    'WDExpress',
    ]

  windowsSdkVersions = getPlatformSdkVersions()
  if not windowsSdkVersions:
    windowsSdkVersions.append((None, None, None))
    
  # Determine host architecture
  hostArchitecture = cake.system.architecture().lower()
  if hostArchitecture not in validArchitectures:
    raise ValueError("Unknown host architecture '%s'." % hostArchitecture)

  # Default architecture is hostArchitecture
  if architecture is None:
    architectures = [hostArchitecture]
    if hostArchitecture in ('x64', 'amd64'):
      architectures.append('x86')
  else:
    architecture = architecture.lower()
    if architecture not in validArchitectures:
      raise ValueError("Unknown architecture '%s'." % architecture)
    architectures = [architecture]

  if version is not None:
    # Validate version
    if version not in versions:
      raise ValueError("Unknown version '%s'." % version)
    # Only check for this version
    versions = [version]

  for a in architectures:
    for v in versions:
      for e in editions:
        for wsdkName, wsdkVer, wsdkPath in windowsSdkVersions:
          try:
            return _createMsvcCompiler(configuration, v, e, a, hostArchitecture, wsdkPath)
          except WindowsError, ex:
            pass
  else:
    raise CompilerNotFoundError(
      "Could not find Microsoft Visual Studio C++ compiler."
      )

def _mungePathToSymbol(path):
  return "_PCH_" + hex(abs(hash(path)))[2:]

class MsvcCompiler(Compiler):

  outputFullPath = None
  """Tell the compiler to output full paths.
  
  When set to True the compiler will output full (absolute) paths to
  source files during compilation. This applies to the paths output for
  warnings/errors and the __FILE__ macro.

  Related compiler options::
    /FC
  @type: bool
  """
  useBigObjects = None
  """Increase the number of sections an object file can contain.
  
  When set to True the compiler may produce bigger object files
  but each object file may contain more addressable sections (up
  to 2^32 in Msvc). If set to False only 2^16 addressable sections
  are available.

  Related compiler options::
    /bigobj
  @type: bool
  """
  memoryLimit = None
  """Set the memory limit for the precompiled header.
  
  The value is scaling factor such that 100 means a memory limit of 50MB,
  200 means a memory limit of 100MB, etc.
  If set to None the default memory limit of 100 (50MB) is used.

  Related compiler options::
    /Zm
  @type: int or None
  """
  runtimeLibraries = None
  """Set the runtime libraries to use.
  
  Possible values are 'debug-dll', 'release-dll', 'debug-static' and
  'release-static'.

  Related compiler options::
    /MD, /MDd, /MT, /MTd
  @type: string or None
  """
  moduleVersion = None
  """Set the program/module version.
  
  The version string should be of the form 'major[.minor]'. Where major and
  minor are decimal integers in the range 0 to 65,535.
  If set to None the default version 0.0 is used.

  Related compiler options::
    /VERSION
  @type: string or None
  """
  useStringPooling = None
  """Use string pooling.
  
  When set to True the compiler may eliminate duplicate strings by sharing
  strings that are identical.

  Related compiler options::
    /GF
  @type: bool
  """
  useMinimalRebuild = None
  """Use minimal rebuild.
  
  When set to True the compiler may choose not to recompile your source file
  if it determines that the information stored in it's dependency information
  file (.idb) has not changed.

  Related compiler options::
    /Gm
  @type: bool
  """
  useEditAndContinue = None
  """Use Edit and Continue.
  
  When set to True the compiler will produce debug information that supports
  the Edit and Continue feature. This option is generally not compatible with
  any form of program/code optimisation. Enabling this option will also
  enable function-level linking. This option is also not compatible with
  Common Language Runtime (CLR) compilation. 

  Related compiler options::
    /ZI
  @type: bool
  """
  outputBrowseInfo = None
  """Output a .sbr file for each object file and generate a final .bsc file.
  
  NOT FULLY IMPLEMENTED! At the moment Cake will not rebuild the .sbr file
  unless the associated .obj file is also out of date. Cake also won't yet
  generate the final .bsc file using bscmake.exe. Perhaps the best way would
  be to add a bsc(target, sources=objects) build function and require users
  to generate the bsc file explicitly. ObjectTarget would gain a .sbr member
  that points to the .sbr file corresponding to the .obj file.
  
  If enabled the compiler will output a .sbr file that matches the
  name of each object file. During program or library builds it will use
  these .sbr files to generate a browse info .bsc file. 

  Related compiler options::
    MSVC: /FR:<target>.sbr
  @type: bool
  """  
  errorReport = None
  """Set the error reporting behaviour.
  
  This value allows you to set how your program should send internal
  compiler error (ICE) information to Microsoft.
  Possible values are 'none', 'prompt', 'queue' and 'send'.
  When set to None the default error reporting behaviour 'queue' is used.

  Related compiler options::
    /errorReport
  @type: string or None
  """
  clrMode = None
  """Set the Common Language Runtime (CLR) mode.
  
  Set to 'pure' to allow native data types but only managed functions.
  Set to 'safe' to only allow managed types and functions.

  Related compiler options::
    /clr, /CLRIMAGETYPE
  @type: string or None
  """ 

  _lineRegex = re.compile('#line [0-9]+ "(?P<path>.+)"', re.MULTILINE)
  
  _pdbQueue = {}
  _pdbQueueLock = threading.Lock()
  
  objectSuffix = '.obj'
  libraryPrefixSuffixes = [('', '.lib')]
  modulePrefixSuffixes = [('', '.dll')]
  programSuffix = '.exe'
  pchSuffix = '.pch'
  pchObjectSuffix = '.obj'
  manifestSuffix = '.embed.manifest'
  resourceSuffix = '.res'
  _name = 'msvc'
  
  def __init__(
    self,
    configuration,
    clExe=None,
    libExe=None,
    linkExe=None,
    mtExe=None,
    rcExe=None,
    bscExe=None,
    binPaths=None,
    includePaths=None,
    libraryPaths=None,
    architecture=None,
    ):
    Compiler.__init__(
      self,
      configuration=configuration,
      binPaths=binPaths,
      includePaths=includePaths,
      libraryPaths=libraryPaths,
      )
    self.__clExe = clExe
    self.__libExe = libExe
    self.__linkExe = linkExe
    self.__mtExe = mtExe
    self.__rcExe = rcExe
    self.__bscExe = bscExe
    self.__architecture = architecture
    self.__messageExpression = re.compile(r'^(\s*)(.+)\(\d+\) :', re.MULTILINE)
    self.forcedUsings = []
    
  @property
  def architecture(self):
    return self.__architecture

  def addForcedUsing(self, assembly):
    """Add a .NET assembly to be forcibly referenced on the command-line.
    
    @param assembly: A path or FileTarget or ScriptResult that results
    in a path or FileTarget.
    """
    self.forcedUsings.append(self.configuration.basePath(assembly))
    self._clearCache()
    
  def _formatMessage(self, inputText):
    """Format errors to be clickable in MS Visual Studio.
    """
    if self.messageStyle != self.MSVS_CLICKABLE:
      return inputText
    
    outputLines = []
    pos = 0
    while True:
      m = self.__messageExpression.search(inputText, pos)
      if m:
        spaces, path, = m.groups()
        startPos = m.start()
        endPos = startPos + len(spaces) + len(path)
        if startPos != pos: 
          outputLines.append(inputText[pos:startPos])
        path = self.configuration.abspath(os.path.normpath(path))
        path = cake.path.fileSystemPath(path)
        outputLines.append(spaces + path)
        pos = endPos
      else:
        outputLines.append(inputText[pos:])
        break
    return ''.join(outputLines)
  
  def _outputStdout(self, text):
    Compiler._outputStdout(self, self._formatMessage(text))

  def _outputStderr(self, text):
    Compiler._outputStderr(self, self._formatMessage(text))
    
  @memoise
  def _getObjectPrerequisiteTasks(self):
    tasks = super(MsvcCompiler, self)._getObjectPrerequisiteTasks()
    
    if self.language == 'c++/cli':
      # Take a copy so we're not modifying the potentially cached
      # base version.
      tasks = list(tasks)
      tasks.extend(getTasks(self.forcedUsings))
    
    return tasks
    
  @memoise
  def _getCompileCommonArgs(self, suffix):
    args = [
      self.__clExe,
      "/nologo",
      "/showIncludes",
      "/c",
      ]

    if self.errorReport:
      args.append('/errorReport:' + self.errorReport)

    if self.outputFullPath:
      args.append("/FC")
      
    if self.useBigObjects:
      args.append("/bigobj")

    if self.memoryLimit is not None:
      args.append("/Zm%i" % self.memoryLimit)

    if self.runtimeLibraries == 'release-dll':
      args.append("/MD")
    elif self.runtimeLibraries == 'debug-dll':
      args.append("/MDd")
    elif self.runtimeLibraries == 'release-static':
      args.append("/MT")
    elif self.runtimeLibraries == 'debug-static':
      args.append("/MTd")
 
    if self.useFunctionLevelLinking:
      args.append('/Gy') # Enable function-level linking
 
    if self.useStringPooling:
      args.append('/GF') # Eliminate duplicate strings
 
    language = self._getLanguage(suffix)
    if language == 'c++':
      args.extend(self.cppFlags)
    elif language == 'c++/cli':
      args.extend(self.cppFlags)
    elif language == 'c':
      args.extend(self.cFlags)

    if self.enableRtti is not None:
      if self.enableRtti:
        args.append('/GR') # Enable RTTI
      else:
        args.append('/GR-') # Disable RTTI
    
    if self.enableExceptions is not None:
      if self.enableExceptions == "SEH":
        args.append('/EHa') # Enable SEH exceptions
      elif self.enableExceptions:
        args.append('/EHsc') # Enable exceptions
      else:
        args.append('/EHsc-') # Disable exceptions

    if self.language == 'c++/cli':
      if self.clrMode == 'safe':
        args.append('/clr:safe') # Compile to verifiable CLR code
      elif self.clrMode == 'pure':
        args.append('/clr:pure') # Compile to pure CLR code 
      else:
        args.append('/clr') # Compile to mixed CLR/native code
        
      for assembly in getPaths(self.forcedUsings):
        args.append('/FU' + assembly)
          
    if self.optimisation == self.FULL_OPTIMISATION:
      args.append('/GL') # Global optimisation
      args.append('/O2') # Full optimisation
    elif self.optimisation == self.PARTIAL_OPTIMISATION:
      args.append('/O2') # Full optimisation
    elif self.optimisation == self.NO_OPTIMISATION:
      args.append('/Od') # No optimisation
 
    if self.warningLevel is not None:
      args.append('/W%s' % self.warningLevel)
      
    if self.warningsAsErrors:
      args.append('/WX')

    if self.useEditAndContinue:
      args.append("/ZI") # Output debug info to PDB (edit-and-continue)
    elif self._needPdbFile:
      args.append("/Zi") # Output debug info to PDB (no edit-and-continue)
    elif self.debugSymbols:
      args.append("/Z7") # Output debug info embedded in .obj
    
    if self.useMinimalRebuild:
      args.append("/Gm") # Enable minimal rebuild
 
    args.extend("/D" + define for define in self.getDefines())
    args.extend("/I" + path for path in self.getIncludePaths())
    args.extend("/FI" + path for path in self.getForcedIncludes())

    return args 
    
  def _getLanguage(self, suffix):
    language = self.language
    if language is None:
      if suffix in self.cSuffixes:
        language = 'c'
      elif suffix in self.cppSuffixes:
        language = 'c++'
    return language
      
  @property
  @memoise
  def _needPdbFile(self):
    if self.pdbFile is not None and self.debugSymbols:
      return True
    elif self.useMinimalRebuild or self.useEditAndContinue:
      return True
    else:
      return False

  def getPchCommands(self, target, source, header, object):
    args = list(self._getCompileCommonArgs(cake.path.extension(source)))
    args.append('/Fo' + object)
    
    if self.outputBrowseInfo:
      args.append('/FR' + cake.path.stripExtension(target) + ".sbr")
    
    if self.language == 'c':
      args.append('/Tc' + source)
    elif self.language in ['c++', 'c++/cli']:
      args.append('/Tp' + source)
    else:
      args.append(source)

    args.extend([
      '/Yl' + _mungePathToSymbol(target),
      '/Fp' + target,
      '/Yc' + header,
      ])

    return self._getObjectCommands(target, source, args, None)
    
  def getObjectCommands(self, target, source, pch, shared):
    args = list(self._getCompileCommonArgs(cake.path.extension(source)))
    args.append('/Fo' + target)

    if self.outputBrowseInfo:
      args.append('/FR' + cake.path.stripExtension(target) + ".sbr")
    
    if self.language == 'c':
      args.append('/Tc' + source)
    elif self.language in ['c++', 'c++/cli']:
      args.append('/Tp' + source)
    else:
      args.append(source)
      
    if pch is not None:
      args.extend([
        '/Yl' + _mungePathToSymbol(pch.path),
        '/Fp' + pch.path,
        '/Yu' + pch.header,
        ])
      deps = [pch.path]
    else:
      deps = []
    
    return self._getObjectCommands(target, source, args, deps)
    
  def _getObjectCommands(self, target, source, args, deps):
    
    if self._needPdbFile:
      if self.pdbFile is not None:
        pdbFile = self.pdbFile
      else:
        pdbFile = target + '.pdb'
      args.append('/Fd' + pdbFile)
    else:
      pdbFile = None
      
    def compile():
      dependencies = [args[0], source]
      if deps is not None:
        dependencies.extend(deps)
      if self.language == 'c++/cli':
        dependencies.extend(getPaths(self.forcedUsings))
      dependenciesSet = set()

      def processStdout(text):
        includePrefix = ('Note: including file:')
        includePrefixLen = len(includePrefix)
        
        sourceName = cake.path.baseName(source)
        outputLines = []
        for line in text.splitlines():
          if line == sourceName:
            continue
          if line.startswith(includePrefix):
            path = line[includePrefixLen:].lstrip()
            normPath = os.path.normcase(os.path.normpath(path))
            if normPath not in dependenciesSet:
              dependenciesSet.add(normPath)
              dependencies.append(path)
          else:
            outputLines.append(line)
        
        if outputLines:
          self._outputStdout("\n".join(outputLines) + "\n")

      self._runProcess(
        args=args,
        target=target,
        processStdout=processStdout,
        )
      
      return dependencies
      
    def compileWhenPdbIsFree():
      absPdbFile = self.configuration.abspath(pdbFile)
      compileTask = self.engine.createTask(compile)
      compileTask.parent.completeAfter(compileTask)
      
      self._pdbQueueLock.acquire()
      try:
        predecessor = self._pdbQueue.get(absPdbFile, None)
        if predecessor is not None:
          predecessor.addCallback(
            lambda: compileTask.start(immediate=True)
            )
        else:
          compileTask.start(immediate=True)
        self._pdbQueue[absPdbFile] = compileTask
      finally:
        self._pdbQueueLock.release()
        
      return compileTask
      
    # Can only cache the object if it's debug info is not going into
    # a .pdb since multiple objects could all put their debug info
    # into the same .pdb.
    canBeCached = pdbFile is None and not self.outputBrowseInfo

    if pdbFile is None:
      return compile, args, canBeCached
    else:
      return compileWhenPdbIsFree, args, canBeCached

  @memoise
  def _getCommonLibraryArgs(self):
    args = [self.__libExe, '/NOLOGO']
    
    # XXX: MSDN says /errorReport:queue is supported by lib.exe
    # but it seems to go unrecognised in MSVC8.
    #if self.errorReport:
    #  args.append('/ERRORREPORT:' + self.errorReport.upper())

    if self.optimisation == self.FULL_OPTIMISATION:
      args.append('/LTCG')

    if self.warningsAsErrors:
      args.append('/WX')

    args.extend(self.libraryFlags)

    return args
      
  def getLibraryCommand(self, target, sources):
    
    args = list(self._getCommonLibraryArgs())

    args.append('/OUT:' + target)
    
    args.extend(sources)
    
    @makeCommand(args)
    def archive():
      self._runProcess(args, target)

    @makeCommand("lib-scan")
    def scan():
      # TODO: Add dependencies on DLLs used by lib.exe
      return [target], [self.__libExe] + sources

    return archive, scan

  @memoise
  def _getLinkCommonArgs(self, dll):
    
    args = [self.__linkExe, '/NOLOGO']

    # XXX: MSVC8 linker complains about /errorReport being unrecognised.
    #if self.errorReport:
    #  args.append('/ERRORREPORT:%s' % self.errorReport.upper())
      
    # Trying to combine /incremental with /clrimagetype gives a linker
    # warning LNK4075: ingoring '/INCREMENTAL'
    if self.useIncrementalLinking is not None and self.clrMode is None:
      if self.useIncrementalLinking:
        args.append('/INCREMENTAL')
      else:
        args.append('/INCREMENTAL:NO')

    if dll:
      args.append('/DLL')
      args.extend(self.moduleFlags)
    else:
      args.extend(self.programFlags)
      
    if self.useFunctionLevelLinking is not None:
      if self.useFunctionLevelLinking:
        args.append('/OPT:REF') # Eliminate unused functions (COMDATs)
        args.append('/OPT:ICF') # Identical COMDAT folding
      else:
        args.append('/OPT:NOREF') # Keep unreferenced functions
    
    if self.moduleVersion is not None:
      args.append('/VERSION:' + self.moduleVersion)
    
    if isinstance(self.stackSize, tuple):
      # Specify stack (reserve, commit) sizes
      args.append('/STACK:%i,%i' % self.stackSize)
    elif self.stackSize is not None:
      # Specify stack reserve size
      args.append('/STACK:%i' % self.stackSize)
    
    if isinstance(self.heapSize, tuple):
      # Specify heap (reserve, commit) sizes
      args.append('/HEAP:%i,%i' % self.heapSize)
    elif self.heapSize is not None:
      # Specify heap reserve size
      args.append('/HEAP:%i' % self.heapSize)
    
    if self.optimisation == self.FULL_OPTIMISATION:
      # Link-time code generation (global optimisation)
      args.append('/LTCG:NOSTATUS')
    
    if self.clrMode is not None:
      if self.clrMode == "pure":
        args.append('/CLRIMAGETYPE:PURE')
      elif self.clrMode == "safe":
        args.append('/CLRIMAGETYPE:SAFE')
      else:
        args.append('/CLRIMAGETYPE:IJW')
    
    if self.debugSymbols:
      args.append('/DEBUG')
      
      if self.clrMode is not None:
        args.append('/ASSEMBLYDEBUG')
      
      if self.pdbFile is not None:
        args.append('/PDB:' + self.pdbFile)
        
      if self.strippedPdbFile is not None:
        args.append('/PDBSTRIPPED:' + self.strippedPdbFile)
    
    if self.warningsAsErrors:
      args.append('/WX')
    
    if self.__architecture == 'x86':
      args.append('/MACHINE:X86')
    elif self.__architecture == 'x64':
      args.append('/MACHINE:X64')
    elif self.__architecture == 'ia64':
      args.append('/MACHINE:IA64')
    
    args.extend('/LIBPATH:' + path for path in self.getLibraryPaths())
    
    return args

  def getProgramCommands(self, target, sources):
    return self._getLinkCommands(target, sources, dll=False)
  
  def getModuleCommands(self, target, sources, importLibrary, installName):
    return self._getLinkCommands(target, sources, importLibrary, installName, dll=True)

  def _getLinkCommands(self, target, sources, importLibrary=None, installName=None, dll=False):
    
    objects, libraries = self._resolveObjects()
    
    if importLibrary:
      importLibrary = self.configuration.abspath(importLibrary)
    
    absTarget = self.configuration.abspath(target)
    absTargetDir = cake.path.dirName(absTarget)
    
    args = list(self._getLinkCommonArgs(dll))

    if self.subSystem is not None:
      args.append('/SUBSYSTEM:' + self.subSystem)
    
    if self.debugSymbols and self.pdbFile is None:
      args.append('/PDB:%s.pdb' % target)
    
    if dll and importLibrary:
      args.append('/IMPLIB:' + importLibrary)

    if self.optimisation == self.FULL_OPTIMISATION and \
       self.useIncrementalLinking:
      self.engine.raiseError(
        "Cannot set useIncrementalLinking with optimisation=FULL_OPTIMISATION\n",
        targets=[target],
        )

    if self.embedManifest:
      if not self.__mtExe:
        self.engine.raiseError(
          "You must set path to mt.exe with embedManifest=True\n",
          targets=[target],
          )
      
      if dll:
        manifestResourceId = 2
      else:
        manifestResourceId = 1
      embeddedManifest = target + '.embed.manifest'
      absEmbeddedManifest = self.configuration.abspath(embeddedManifest)
      if self.useIncrementalLinking:
        if not self.__rcExe:
          self.engine.raiseError(
            "You must set path to rc.exe with embedManifest=True and useIncrementalLinking=True\n",
            targets=[target],
            )
        
        intermediateManifest = target + '.intermediate.manifest'
        absIntermediateManifest = absTarget + '.intermediate.manifest'
        
        embeddedRc = embeddedManifest + '.rc'
        absEmbeddedRc = absEmbeddedManifest + '.rc' 
        embeddedRes = embeddedManifest + '.res'
        args.append('/MANIFESTFILE:' + intermediateManifest)
        args.append(embeddedRes)
      else:
        args.append('/MANIFESTFILE:' + embeddedManifest)
    
    if self.outputMapFile:
      mapFile = cake.path.stripExtension(target) + '.map'
      args.append('/MAP:' + mapFile)
    
    args.append('/OUT:' + target)
    args.extend(sources)
    args.extend(objects)

    # Msvc requires a .lib extension otherwise it will assume an .obj
    libraryPrefix, librarySuffix = self.libraryPrefix, self.librarySuffix
    for l in libraries:
      if not cake.path.hasExtension(l):
        l = cake.path.forcePrefixSuffix(l, libraryPrefix, librarySuffix)
      args.append(l)
    
    @makeCommand(args)
    def link():
      if dll and importLibrary:
        cake.filesys.makeDirs(cake.path.dirName(importLibrary))
      self._runProcess(args, target)
       
    @makeCommand(args) 
    def linkWithManifestIncremental():

      def compileRcToRes():
        rcArgs = [
          self.__rcExe,
          "/fo" + embeddedRes,
          embeddedRc,
          ]

        self._runProcess(
          args=rcArgs,
          target=embeddedRes,
          processStdout=self._processRcStdout,
          allowResponseFile=False,
          )
      
      def updateEmbeddedManifestFile():
        """Updates the embedded manifest file based on the manifest file
        output by the link stage.
        
        @return: True if the manifest file changed, False if the manifest
        file stayed the same.
        """
        
        mtArgs = [
          self.__mtExe,
          "/nologo",
          "/notify_update",
          "/manifest", intermediateManifest,
          "/out:" + embeddedManifest,
          ]
        
        result = []

        def processExitCode(exitCode):
          # The magic number here is the exit code output by the mt.exe
          # tool when the manifest file hasn't actually changed. We can
          # avoid a second link if the manifest file hasn't changed.
          if exitCode != 0 and exitCode != 1090650113:
            self.engine.raiseError(
              "%s: failed with exit code %i\n" % (mtArgs[0], exitCode),
              targets=[target],
              )
  
          result.append(exitCode != 0)
      
        self._runProcess(
          args=mtArgs,
          target=embeddedManifest,
          processExitCode=processExitCode,
          )
        
        return result[0]
      
      # Create an empty embeddable manifest if one doesn't already exist
      if not cake.filesys.isFile(absEmbeddedManifest):
        self.engine.logger.outputInfo(
          "Creating dummy manifest: %s\n" % embeddedManifest
          )
        cake.filesys.makeDirs(absTargetDir)
        open(absEmbeddedManifest, 'wb').close()
      
      # Generate .embed.manifest.rc
      self.engine.logger.outputInfo("Creating %s\n" % embeddedRc)
      f = open(absEmbeddedRc, 'w')
      try:
        # Use numbers so we don't have to include any headers
        # 24 - RT_MANIFEST
        f.write('%i 24 "%s"\n' % (
          manifestResourceId,
          embeddedManifest.replace("\\", "\\\\")
          ))
      finally:
        f.close()
      
      compileRcToRes()
      link()
      
      if cake.filesys.isFile(absIntermediateManifest) and updateEmbeddedManifestFile():
        # Manifest file changed so we need to re-link to embed it
        compileRcToRes()
        link()
    
    @makeCommand(args)
    def linkWithManifestNonIncremental():
      """This strategy for embedding the manifest embeds the manifest in-place
      in the executable since it doesn't need to worry about invalidating the
      ability to perform incremental links.
      """
      # Perform the link as usual
      link()
      
      # If we are linking with static runtimes there may be no manifest
      # output, in which case we can skip embedding it.
      
      if not cake.filesys.isFile(absEmbeddedManifest):
        self.engine.logger.outputInfo(
          "Skipping embedding manifest: no manifest to embed\n"
          )
        return
      
      mtArgs = [
        self.__mtExe,
        "/nologo",
        "/manifest", embeddedManifest,
        "/outputresource:%s;%i" % (target, manifestResourceId),
        ]
      
      self._runProcess(mtArgs, embeddedManifest)
        
    @makeCommand("link-scan")
    def scan():
      targets = [target]
      if dll and importLibrary:
        exportFile = cake.path.stripExtension(importLibrary) + '.exp'
        targets.append(importLibrary)
        targets.append(exportFile)
      if self.outputMapFile:
        targets.append(mapFile)
      if self.debugSymbols:
        if self.pdbFile is not None:
          targets.append(self.pdbFile)
        if self.strippedPdbFile is not None:
          targets.append(self.strippedPdbFile)
      if not self.embedManifest:
        # If we are linking with static runtimes there may be no manifest
        # output, in which case we don't need to flag it as a target.
        manifestFile = target + '.manifest'
        absManifestFile = self.configuration.abspath(manifestFile)
        if cake.filesys.isFile(absManifestFile):
          targets.append(manifestFile)
        
      dependencies = [self.__linkExe]
      dependencies += sources
      dependencies += objects
      dependencies += self._scanForLibraries(libraries)
      return targets, dependencies
    
    if self.embedManifest:
      if self.useIncrementalLinking:
        return linkWithManifestIncremental, scan
      else:
        return linkWithManifestNonIncremental, scan
    else:
      return link, scan

  @memoise
  def _getCommonResourceArgs(self):
    args = [self.__rcExe] # Cannot use '/nologo' due to WindowsSDK 6.0A rc.exe not supporting it.
    args.extend(self.resourceFlags)
    args.extend("/d" + define for define in self.getDefines())
    args.extend("/i" + path for path in self.getIncludePaths())
    return args

  def getResourceCommand(self, target, source):
    
    args = list(self._getCommonResourceArgs())
    args.append('/fo' + target)
    args.append(source)
    
    @makeCommand(args)
    def compile():
      self._runProcess(
        args,
        target,
        processStdout=self._processRcStdout,
        allowResponseFile=False)

    @makeCommand("rc-scan")
    def scan():
      # TODO: Add dependencies on DLLs used by rc.exe
      return [target], [self.__rcExe, source]

    return compile, scan
    
  def _processRcStdout(self, text):
    """Process the output of rc.exe, suppressing the leading logo.
    
    We use this rather than /nologo as the /nologo flag isn't supported on all
    versions of rc.exe.
    """
    outputLines = text.splitlines()

    # Skip any leading logo output by some of the later versions of rc.exe
    if len(outputLines) >= 2 and \
       outputLines[0].startswith('Microsoft (R) Windows (R) Resource Compiler Version ') and \
       outputLines[1].startswith('Copyright (C) Microsoft Corporation.  All rights reserved.'):
      outputLines = outputLines[2:]
      
    if outputLines:
      self._outputStdout("\n".join(outputLines) + "\n")
