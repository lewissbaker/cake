"""The Gcc Compiler.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

from cake.library import memoise
from cake.target import getPaths
from cake.library.compilers import Compiler, makeCommand, CompilerNotFoundError
import cake.filesys
import cake.path
import cake.system
import os
import os.path
import re
import subprocess
import tempfile

def _getMinGWInstallDir():
  """Returns the MinGW install directory.
  
  Typically: 'C:\MinGW'.

  @return: The path to the MinGW install directory.
  @rtype: string 

  @raise WindowsError: If MinGW is not installed. 
  """
  import _winreg
  
  from cake.registry import queryString
  
  possibleSubKeys = [
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\MinGW",
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{AC2C1BDB-1E91-4F94-B99C-E716FE2E9C75}_is1",
    ]
  
  # Try all known registry locations.
  for subKey in possibleSubKeys:
    try:
      return queryString(_winreg.HKEY_LOCAL_MACHINE, subKey, "InstallLocation")
    except WindowsError:
      # If this is the last possibility, re-raise the exception.
      if subKey is possibleSubKeys[-1]:
        raise

def _getGccVersion(gccExe):
  """Returns the Gcc version number given an executable.
  """
  stdout = tempfile.TemporaryFile(mode="w+t")
  try:
    try:
      args = [gccExe, '-dumpversion']
      p = subprocess.Popen(
        args=args,
        stdout=stdout,
        )
    except EnvironmentError, e:
      raise EnvironmentError(
        "cake: failed to launch %s: %s\n" % (args[0], str(e))
        )
    exitCode = p.wait()
    stdout.seek(0)
    stdoutText = stdout.read()
  finally:
    stdout.close()
  
  if exitCode != 0:
    raise EnvironmentError(
      "%s: failed with exit code %i\n" % (args[0], exitCode)
      )
  
  return [
    int(n) for n in stdoutText.strip().split(".")
    ]
  
def findMinGWCompiler(configuration):
  """Returns a MinGW compiler if found.
  
  @raise CompilerNotFoundError: When a valid MinGW compiler could not be found.
  """
  try:
    installDir = _getMinGWInstallDir()
    binDir = cake.path.join(installDir, "bin")
    arExe = cake.path.join(binDir, "ar.exe")
    gccExe = cake.path.join(binDir, "gcc.exe")
    rcExe = cake.path.join(binDir, "windres.exe")
    
    def checkFile(path):
      if not cake.filesys.isFile(path):
        raise WindowsError(path + " is not a file.")

    checkFile(arExe)
    checkFile(gccExe)
    checkFile(rcExe)
    
    try:
      version = _getGccVersion(gccExe)
    except EnvironmentError:
      raise CompilerNotFoundError("Could not find MinGW version.")

    return WindowsMinGWCompiler(
      configuration=configuration,
      arExe=arExe,
      gccExe=gccExe,
      rcExe=rcExe,
      binPaths=[binDir],
      version=version,
      )
  except WindowsError:
    raise CompilerNotFoundError("Could not find MinGW install directory.")

def findGccCompiler(configuration, platform=None):
  """Returns a GCC compiler if found.

  @param platform: The platform/operating system to compile for. If
  platform is None then the current platform is used.

  @raise CompilerNotFoundError: When a valid gcc compiler could not be found.
  """
  if platform is None:
    platform = cake.system.platform()
  platform = platform.lower()
  
  isDarwin = platform.startswith("darwin")
    
  paths = os.environ.get('PATH', '').split(os.path.pathsep)

  try:
    binPaths = []

    def checkFile(path):
      if not cake.filesys.isFile(path):
        raise EnvironmentError(path + " is not a file.")

    if isDarwin:
      libtoolExe = cake.system.findExecutable("libtool", paths)
      checkFile(libtoolExe)
      binPaths.append(cake.path.dirName(libtoolExe))
    else:
      arExe = cake.system.findExecutable("ar", paths)
      checkFile(arExe)
      binPaths.append(cake.path.dirName(arExe))

    gccExe = cake.system.findExecutable("gcc", paths)
    checkFile(gccExe)
    binPaths.append(cake.path.dirName(gccExe))

    binPaths = list(set(binPaths)) # Only want unique paths
    
    try:
      version = _getGccVersion(gccExe)
    except EnvironmentError:
      raise CompilerNotFoundError("Could not find GCC version.")
    
    if platform.startswith("windows") or platform.startswith("cygwin"):
      return WindowsGccCompiler(
        configuration=configuration,
        arExe=arExe,
        gccExe=gccExe,
        binPaths=binPaths,
        version=version,
        )
    elif isDarwin:
      return MacGccCompiler(
        configuration=configuration,
        gccExe=gccExe,
        libtoolExe=libtoolExe,
        binPaths=binPaths,
        version=version,
        )
    elif platform.startswith("ps3"):
      return Ps3GccCompiler(
        configuration=configuration,
        arExe=arExe,
        gccExe=gccExe,
        binPaths=binPaths,
        version=version,
        )
    else:
      return GccCompiler(
        configuration=configuration,
        arExe=arExe,
        gccExe=gccExe,
        binPaths=binPaths,
        version=version,
        )
  except EnvironmentError:
    raise CompilerNotFoundError("Could not find GCC compiler, AR archiver or libtool.")

class GccCompiler(Compiler):
  
  _name = 'gcc'

  def __init__(
    self,
    configuration,
    arExe=None,
    gccExe=None,
    libtoolExe=None,
    binPaths=None,
    version=None,
    ):
    Compiler.__init__(self, configuration=configuration, binPaths=binPaths)
    self._arExe = arExe
    self._gccExe = gccExe
    self._libtoolExe = libtoolExe
    self.__version = version
    self.__messageExpression = re.compile(r'^(.+?):(\d+)(:\d+)?:', re.MULTILINE)

  @property
  def version(self):
    return self.__version
  
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
        path, line, _column = m.groups()
        startPos = m.start()
        endPos = m.end()
        if startPos != pos: 
          outputLines.append(inputText[pos:startPos])
        path = self.configuration.abspath(os.path.normpath(path))
        outputLines.append('%s(%s) :' % (path, line))
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
  def _getCompileArgs(self, suffix, shared=False, pch=False):
    args = [self._gccExe, '-c', '-MD']

    language = self._getLanguage(suffix, pch)
    if pch: # Pch requires '-header' so must use derived language.
      if language is not None:
        args.extend(['-x', language])
    else:
      if self.language is not None:
        args.extend(['-x', self.language])
    
    if self.warningsAsErrors:
      args.append('-Werror')

    # This test is req'd for Python 3.x or it barfs on 'self.warningLevel >= 4'
    # below when self.warningLevel is None.
    if self.warningLevel is not None:
      if self.warningLevel == 0:
        args.append('-w')
      elif self.warningLevel >= 4:
        args.append('-Wall')

    if self.debugSymbols:
      args.append('-g')

    if language in ['c++', 'c++-header', 'c++-cpp-output']:
      args.extend(self.cppFlags)
    elif language in ['c', 'c-header', 'cpp-output']:
      args.extend(self.cFlags)
    elif language in ['objective-c', 'objective-c-header', 'objc-cpp-output']:
      args.extend(self.mFlags)
    elif language in ['objective-c++', 'objective-c++-header', 'objective-c++-cpp-output']:
      args.extend(self.mmFlags)

    if self.enableRtti is not None:
      if self.enableRtti:
        args.append('-frtti')
      else:
        args.append('-fno-rtti')
          
    if self.enableExceptions is not None:
      if self.enableExceptions:
        args.append('-fexceptions')
      else:
        args.append('-fno-exceptions')

    if self.useFunctionLevelLinking:
      args.extend([
        '-ffunction-sections',
        '-fdata-sections',
        ])
      
    if self.optimisation == self.NO_OPTIMISATION:
      args.append('-O0')
    elif self.optimisation == self.PARTIAL_OPTIMISATION:
      args.append('-O2')
    elif self.optimisation == self.FULL_OPTIMISATION:
      args.append('-O3')
      
    if self.useSse:
      args.append('-msse')
 
    if shared and self.__version[0] >= 4:
      args.append('-fvisibility=hidden')
      args.append('-fPIC')

    for p in self.getIncludePaths():
      args.extend(['-I', p])

    args.extend('-D' + d for d in self.getDefines())
    
    for p in getPaths(self.getForcedIncludes()):
      args.extend(['-include', p])
    
    return args

  def _getLanguage(self, suffix, pch=False):
    language = self.language
    
    if language is None:
      # Attempt to derive the language based on the suffix.
      if suffix in self.cSuffixes:
        language = 'c'
      elif suffix in self.cppSuffixes:
        language = 'c++'
      elif suffix in self.mSuffixes:
        language = 'objective-c'
      elif suffix in self.mmSuffixes:
        language = 'objective-c++'
      elif suffix in self.sSuffixes:
        language = 'assembler'
    
    # Pch generation requires '-header' at the end.
    if pch and language in ['c', 'c++', 'objective-c', 'objective-c++']:
      language += '-header'
    
    return language

  def getPchCommands(self, target, source, header, object):
    depPath = self._generateDependencyFile(target)
    args = list(self._getCompileArgs(cake.path.extension(source), shared=False, pch=True))
    args.extend([source, '-o', target])

    def compile():   
      dependencies = self._runProcess(args + ['-MF', depPath], target)
      dependencies.extend(self._scanDependencyFile(depPath, target))
      return dependencies
    
    canBeCached = True
    return compile, args, canBeCached
  
  def getObjectCommands(self, target, source, pch, shared):
    depPath = self._generateDependencyFile(target)
    args = list(self._getCompileArgs(cake.path.extension(source), shared))
    args.extend([source, '-o', target])
  
    if pch is not None:
      args.extend([
        '-Winvalid-pch',
        '-include', cake.path.stripExtension(pch.path),
        ])
        
    def compile():
      dependencies = self._runProcess(args + ['-MF', depPath], target)
      dependencies.extend(self._scanDependencyFile(depPath, target))
              
      if pch is not None:
        dependencies.append(pch.path)
        
      return dependencies
    
    canBeCached = True
    return compile, args, canBeCached

  @memoise
  def _getCommonLibraryArgs(self):
    # q - Quick append file to the end of the archive
    # c - Don't warn if we had to create a new file
    # s - Build an index
    args = [self._arExe, '-qcs']
    args.extend(self.libraryFlags)
    return args

  def getLibraryCommand(self, target, sources):
    args = list(self._getCommonLibraryArgs())
    args.append(target)
    args.extend(sources)
    
    @makeCommand(args)
    def archive():
      cake.filesys.remove(target)
      self._runProcess(args, target)

    @makeCommand("lib-scan")
    def scan():
      # TODO: Add dependencies on DLLs used by ar.exe
      return [target], [args[0]] + sources

    return archive, scan

  @memoise
  def _getCommonLinkArgs(self, dll):
    args = [self._gccExe]
    if dll:
      args.extend(self.moduleFlags)
    else:
      args.extend(self.programFlags)
      
    if dll:
      args.append('-shared')
      args.append('-fPIC')

    args.extend('-L' + p for p in self.getLibraryPaths())
    return args
  
  def getProgramCommands(self, target, sources):
    return self._getLinkCommands(target, sources, dll=False)
  
  def getModuleCommands(self, target, sources, importLibrary, installName):
    return self._getLinkCommands(target, sources, importLibrary, installName, dll=True)

  def _getLinkCommands(self, target, sources, importLibrary=None, installName=None, dll=False):
    
    objects, libraries = self._resolveObjects()

    if importLibrary:
      importLibrary = self.configuration.abspath(importLibrary)

    args = list(self._getCommonLinkArgs(dll))
    args.extend(sources)
    args.extend(objects)
    for lib in libraries:
      if os.path.sep in lib or os.path.altsep and os.path.altsep in lib:
        args.append(lib)
      else:
        args.append('-l' + lib)
    args.extend(['-o', target])

    if self.outputMapFile:
      args.append('-Wl,-Map=' + cake.path.stripExtension(target) + '.map')
    
    @makeCommand(args)
    def link():
      self._runProcess(args, target)

      if dll and importLibrary:
        # Since the target .dylib is also the import library, copy it to the
        # .a 'importLibrary' filename the user expects
        cake.filesys.makeDirs(cake.path.dirName(importLibrary))
        cake.filesys.copyFile(self.configuration.abspath(target), importLibrary)      
    
    @makeCommand("link-scan")
    def scan():
      # TODO: Add dependencies on DLLs used by gcc.exe
      # Also add dependencies on system libraries, perhaps
      #  by parsing the output of ',Wl,--trace'
      targets = [target]
      if dll and importLibrary:
        targets.append(importLibrary)
      dependencies = [args[0]]
      dependencies += sources
      dependencies += objects
      dependencies += self._scanForLibraries(libraries)
      return targets, dependencies
    
    return link, scan

class WindowsGccCompiler(GccCompiler):
  
  objectSuffix = '.obj'
  libraryPrefixSuffixes = [('', '.lib'), ('lib', '.a')]
  modulePrefixSuffixes = [('', '.dll'), ('lib', '.so')]
  programSuffix = '.exe'
  resourceSuffix = '.obj'

  def __init__(
    self,
    configuration,
    arExe=None,
    gccExe=None,
    rcExe=None,
    binPaths=None,
    version=None,
    ):
    GccCompiler.__init__(
      self,
      configuration=configuration,
      arExe=arExe,
      gccExe=gccExe,
      binPaths=binPaths,
      version=version,
      )
    self.__rcExe = rcExe
    
  @memoise
  def _getCommonLinkArgs(self, dll):
    args = GccCompiler._getCommonLinkArgs(self, dll)

    if dll and self.importLibrary is not None:
      args.append('-Wl,--out-implib=' + self.importLibrary)

    if self.useFunctionLevelLinking:
      args.append('-Wl,--gc-sections')

    return args

  @memoise
  def _getCommonResourceArgs(self):
    args = [self.__rcExe]
    args.extend(self.resourceFlags)
    args.extend("-D" + define for define in self.getDefines())
    args.extend("-I" + path for path in self.getIncludePaths())
    return args

  def getResourceCommand(self, target, source):
    
    # TODO: Dependency scanning of .h files (can we use gcc and '-MD'?)
    args = list(self._getCommonResourceArgs())
    args.append('-o' + target)
    args.append('-i' + source)

    @makeCommand(args)
    def compile():
      cake.filesys.remove(self.configuration.abspath(target))
      self._runProcess(args, target)

    @makeCommand("rc-scan")
    def scan():
      # TODO: Add dependencies on DLLs used by rc.exe
      return [target], [args[0], source]

    return compile, scan

class WindowsMinGWCompiler(WindowsGccCompiler):

  _name = 'mingw'

  @memoise
  def _getCommonLinkArgs(self, dll):
    args = WindowsGccCompiler._getCommonLinkArgs(self, dll)

    # TODO: If this breaks try supporting the older '-mwindows' flag for older
    # compiler versions. The flag below works for MinGW/GCC 4.5.2.
    if self.subSystem is not None:
      args.append('-Wl,-subsystem,' + self.subSystem.lower())
      
    return args
  
class MacGccCompiler(GccCompiler):

  modulePrefixSuffixes = [('lib', '.dylib')]

  @memoise
  def _getCommonLibraryArgs(self):
    args = [self._libtoolExe]
    args.extend(self.libraryFlags)
    return args
  
  def getLibraryCommand(self, target, sources):
    args = list(self._getCommonLibraryArgs())
    args.append('-static')
    args.extend(['-o', target])
    args.extend(sources)
    
    @makeCommand(args)
    def archive():
      cake.filesys.remove(target)
      self._runProcess(args, target)

    @makeCommand("lib-scan")
    def scan():
      # TODO: Add dependencies on DLLs used by ar.exe
      return [target], [args[0]] + sources

    return archive, scan
    
  @memoise
  def _getCommonLinkArgs(self, dll):
    args = GccCompiler._getCommonLinkArgs(self, dll)
 
    if dll:
      args.append('-dynamiclib')
      args.extend(["-current_version", "1.0"])
      args.extend(["-compatibility_version", "1.0"])
 
    return args
  
  def _getLinkCommands(self, target, sources, importLibrary=None, installName=None, dll=False):
    
    objects, libraries = self._resolveObjects()

    if importLibrary:
      importLibrary = self.configuration.abspath(importLibrary)
    
    args = list(self._getCommonLinkArgs(dll))
    
    # Should only need this if we're linking with any shared
    # libs, but I don't know how to detect that
    args.extend(["-Wl,-rpath,@loader_path/."])
    
    args.extend(sources)
    args.extend(objects)
    for lib in libraries:
      if os.path.sep in lib or os.path.altsep and os.path.altsep in lib:
        args.append(lib)
      else:
        args.append('-l' + lib)
    args.extend(['-o', target])
    
    if dll and installName:
      args.extend(["-install_name", installName])

    if self.outputMapFile:
      mapFile = cake.path.stripExtension(target) + '.map'
      args.append('-map=' + mapFile)

    @makeCommand(args)
    def link():
      self._runProcess(args, target)      

      if dll and importLibrary:
        # Since the target .dylib is also the import library, copy it to the
        # .a 'importLibrary' filename the user expects
        cake.filesys.makeDirs(cake.path.dirName(importLibrary))
        cake.filesys.copyFile(self.configuration.abspath(target), importLibrary)
        
    @makeCommand("link-scan")
    def scan():
      # TODO: Add dependencies on DLLs used by gcc.exe
      # Also add dependencies on system libraries, perhaps
      #  by parsing the output of ',Wl,--trace'
      targets = [target]
      if dll and importLibrary:
        targets.append(importLibrary)
      if self.outputMapFile:
        targets.append(mapFile)
      
      return targets, [args[0]] + sources

    return link, scan

class Ps3GccCompiler(GccCompiler):

  modulePrefixSuffixes = [('', '.sprx')]
  programSuffix = '.self'

  @memoise
  def _getCommonLinkArgs(self, dll):
    args = GccCompiler._getCommonLinkArgs(self, dll)

    if dll:
      args.append('-Wl,--oformat=fsprx')
    else:
      args.append('-Wl,--oformat=fself')

    if self.useFunctionLevelLinking:
      args.extend([
        '-Wl,-strip-unused',
        '-Wl,-strip-unused-data',
        ])
      
    return args
