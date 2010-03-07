"""The Gcc Compiler.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

from __future__ import with_statement

import os
import os.path
import re
import sys
import subprocess
import platform

import cake.filesys
import cake.path
from cake.library import memoise
from cake.library.compilers import Compiler, makeCommand, CompilerNotFoundError
from cake.gnu import parseDependencyFile
from cake.system import getHostArchitecture

if platform.system().lower().startswith('cygwin'):
  def _findExecutable(name, paths):
    """Find an executable given its name and a list of paths.  
    """
    for p in paths:
      executable = cake.path.join(p, name)
      if cake.filesys.isFile(executable):
        # On cygwin it can sometimes say a file exists at a path
        # when its real filename includes a .exe on the end.
        # We detect this by actually trying to open the path
        # for read, if it fails we know it should have a .exe.
        try:
          with open(executable, 'rb'):
            return executable
        except EnvironmentError:
          return executable + '.exe'
    else:
      raise EnvironmentError("Could not find executable.")
    
elif platform.system().lower().startswith('windows'):
  def _findExecutable(name, paths):
    """Find an executable given its name and a list of paths.  
    """
    # Windows executables could have any of a number of extensions
    # We just search through standard extensions so that we're not
    # dependent on the user's environment.
    pathExt = ['', '.bat', '.exe', '.com', '.cmd']
    for p in paths:
      basePath = cake.path.join(p, name)
      for ext in pathExt:
        executable = basePath + ext
        if cake.filesys.isFile(executable):
          return executable
    else:
      raise EnvironmentError("Could not find executable.")
    
else:
  def _findExecutable(name, paths):
    """Find an executable given its name and a list of paths.  
    """
    for p in paths:
      executable = cake.path.join(p, name)
      if cake.filesys.isFile(executable):
        return executable
    else:
      raise EnvironmentError("Could not find executable.")

def _getMinGWInstallDir():
  """Returns the MinGW install directory.
  
  Typically: 'C:\MinGW'.

  @return: The path to the MinGW install directory.
  @rtype: string 

  @raise WindowsError: If MinGW is not installed. 
  """
  import _winreg
  subKey = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\MinGW"
  key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, subKey)
  try:
    return str(_winreg.QueryValueEx(key, "InstallLocation")[0])
  finally:
    _winreg.CloseKey(key)

def findMinGWCompiler(architecture=None):
  """Returns a MinGW compiler given an architecture.
  
  @param architecture: The machine architecture to compile for. If
  architecture is None then the current architecture is used.

  @raise CompilerNotFoundError: When a valid MinGW compiler could not be found.
  """
  if architecture is None:
    architecture = getHostArchitecture()

  try:
    installDir = _getMinGWInstallDir()
    arExe = cake.path.join(installDir, "bin", "ar.exe")
    gccExe = cake.path.join(installDir, "bin", "gcc.exe")
    
    def checkFile(path):
      if not cake.filesys.isFile(path):
        raise WindowsError(path + " is not a file.")

    checkFile(arExe)
    checkFile(gccExe)

    return WindowsGccCompiler(
      arExe=arExe,
      gccExe=gccExe,
      architecture=architecture,
      )
  except WindowsError:
    raise CompilerNotFoundError("Could not find MinGW install directory.")

def _hostPlatform():
  return platform.system().lower()

def findGccCompiler(platform=None, architecture=None):
  """Returns a GCC compiler given an architecture.

  @param platform: The platform/operating system to compile for. If
  platform is None then the current platform is used.
  @param architecture: The machine architecture to compile for. If
  architecture is None then the current architecture is used.

  @raise CompilerNotFoundError: When a valid gcc compiler could not be found.
  """
  if platform is None:
    platform = _hostPlatform()
    
  if architecture is None:
    architecture = getHostArchitecture()

  paths = os.environ.get('PATH', '').split(os.path.pathsep)

  try:
    arExe = _findExecutable("ar", paths)
    gccExe = _findExecutable("gcc", paths)

    def checkFile(path):
      if not cake.filesys.isFile(path):
        raise EnvironmentError(path + " is not a file.")

    checkFile(arExe)
    checkFile(gccExe)

    if platform == "windows" or platform.startswith("cygwin"):
      constructor = WindowsGccCompiler
    elif platform == "darwin":
      constructor = MacGccCompiler
    elif platform == "ps3":
      constructor = Ps3GccCompiler
    else:
      constructor = GccCompiler 
    
    return constructor(
      arExe=arExe,
      gccExe=gccExe,
      architecture=architecture,
      )
  except EnvironmentError:
    raise CompilerNotFoundError("Could not find GCC compiler and AR archiver.")

class GccCompiler(Compiler):

  def __init__(
    self,
    arExe=None,
    gccExe=None,
    architecture=None,
    ):
    Compiler.__init__(self)
    self.__arExe = arExe
    self.__gccExe = gccExe
    self.__architecture = architecture
  
  @property
  def architecture(self):
    return self.__architecture

  @memoise
  def _getProcessEnv(self, executable):
    temp = os.environ.get('TMP', os.environ.get('TEMP', os.getcwd()))
    env = {
      'COMPSPEC' : os.environ.get('COMSPEC', ''),
      'PATHEXT' : ".com;.exe;.bat;.cmd",
      'SYSTEMROOT' : os.environ.get('SYSTEMROOT', ''),
      'TMP' : temp,
      'TEMP' : temp,  
      'PATH' : cake.path.dirName(executable),
      }
    if env['SYSTEMROOT']:
      env['PATH'] = os.path.pathsep.join([
        env['PATH'],
        os.path.join(env['SYSTEMROOT'], 'System32'),
        env['SYSTEMROOT'],
        ])
    return env

  def _formatMessage(self, inputText):
    """Format errors to be clickable in MS Visual Studio.
    """
    if platform.system() != "Windows":
      return inputText
    
    outputText = ""
    lines = inputText.split('\n')
    for line in lines:
      line = line.rstrip('\r')
      m = re.search('(?P<linenum>:\d+)(?P<colnum>:\d+)?', line)
      if m:
        linenum, _colnum = m.groups()
        sourceFile = line[:m.start('linenum')]
        sourceFile = os.path.abspath(os.path.normpath(sourceFile))
        lineNumber = linenum[1:]
        message = line[m.end()+2:]
        outputText += "%s(%s): %s\n" % (sourceFile, lineNumber, message)
      elif line.strip(): # Don't print blank lines
        outputText += line + '\n'
    return outputText
      
  def _executeProcess(self, args, target, engine):
    engine.logger.outputDebug(
      "run",
      "run: %s\n" % " ".join(args),
      )
    cake.filesys.makeDirs(cake.path.dirName(target))

# TODO: Response file support...but gcc 3.x doesn't support it???     
#    argsFile = target + '.args'
#    with open(argsFile, 'wt') as f:
#      for arg in args[1:]:
#        f.write(arg + '\n')

    try:
      p = subprocess.Popen(
        #args=[args[0], '@' + argsFile],
        args=args,
        executable=args[0],
        env=self._getProcessEnv(args[0]),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        )
    except EnvironmentError, e:
      engine.raiseError(
        "cake: failed to launch %s: %s\n" % (args[0], str(e))
        )
  
    p.stdin.close()
    output = p.stdout.read()
    exitCode = p.wait()
    
    if output:
      sys.stderr.write(self._formatMessage(output))
        
    if exitCode != 0:
      engine.raiseError(
        "%s: failed with exit code %i\n" % (args[0], exitCode)
        )

  @memoise
  def _getCompileArgs(self, language):
    args = [self.__gccExe, '-c', '-MD']

    args.extend(['-x', language])

    if self.warningsAsErrors:
      args.append('-Werror')

    if self.debugSymbols:
      args.append('-g')

    if language == 'c++':
      if self.enableRtti:
        args.append('-frtti')
      else:
        args.append('-fno-rtti')

    if self.enableExceptions:
      args.append('-fexceptions')
    else:
      args.append('-fno-exceptions')

    if self.optimisation == self.NO_OPTIMISATION:
      args.append('-O0')
    elif self.optimisation == self.PARTIAL_OPTIMISATION:
      args.append('-O2')
    elif self.optimisation == self.FULL_OPTIMISATION:
      args.extend([
        '-O4',
        '-ffunction-sections',
        '-fdata-sections',
        ])
      
    if self.useSse:
      args.append('-msse')
  
    for p in reversed(self.includePaths):
      args.extend(['-I', p])

    args.extend('-D' + d for d in reversed(self.defines))
    
    for p in reversed(self.forcedIncludes):
      args.extend(['-include', p])
    
    return args

  def getObjectCommands(self, target, source, engine):
    
    language = self.language
    if not language:
      if source.lower().endswith('.c'):
        language = 'c'
      else:
        language = 'c++'
   
    args = list(self._getCompileArgs(language))
    args += [source, '-o', target]
    
    def compile():
      self._executeProcess(args, target, engine)
      
      dependencyFile = cake.path.stripExtension(target) + '.d'
      engine.logger.outputDebug(
        "scan",
        "scan: %s\n" % dependencyFile,
        )
      
      # TODO: Add dependencies on DLLs used by gcc.exe
      dependencies = [args[0]]
      dependencies.extend(parseDependencyFile(
        dependencyFile,
        self.objectSuffix
        ))
      return dependencies
    
    def command():
      task = engine.createTask(compile)
      task.start(immediate=True)
      return task
    
    canBeCached = True
    return command, args, canBeCached

  @memoise
  def _getCommonLibraryArgs(self):
    # q - Quick append file to the end of the archive
    # c - Don't warn if we had to create a new file
    # s - Build an index
    return [self.__arExe, '-qcs']

  def getLibraryCommand(self, target, sources, engine):
    args = list(self._getCommonLibraryArgs())
    args.append(target)
    args.extend(sources)
    
    @makeCommand(args)
    def archive():
      cake.filesys.remove(target)
      self._executeProcess(args, target, engine)

    @makeCommand("lib-scan")
    def scan():
      # TODO: Add dependencies on DLLs used by ar.exe
      return [args[0]] + sources

    return archive, scan

  @memoise
  def _getCommonLinkArgs(self, dll):
    return [self.__gccExe]
  
  def getProgramCommands(self, target, sources, engine):
    return self._getLinkCommands(target, sources, engine, dll=False)
  
  def getModuleCommands(self, target, sources, engine):
    return self._getLinkCommands(target, sources, engine, dll=True)

  def _getLinkCommands(self, target, sources, engine, dll):
    
    resolvedPaths, unresolvedLibs = self._resolveLibraries(engine)

    args = list(self._getCommonLinkArgs(dll))
    args.extend(sources)
    args.extend(resolvedPaths)    
    args.extend('-L' + p for p in reversed(self.libraryPaths))
    args.extend('-l' + l for l in unresolvedLibs)    
    args.extend(['-o', target])

    if dll and self.importLibrary is not None:
      args.append('-Wl,--out-implib=' + self.importLibrary)
    
    @makeCommand(args)
    def link():
      if self.importLibrary:
        cake.filesys.makeDirs(cake.path.dirName(self.importLibrary))
      self._executeProcess(args, target, engine)      
    
    @makeCommand("link-scan")
    def scan():
      # TODO: Add dependencies on DLLs used by gcc.exe
      # Also add dependencies on system libraries, perhaps
      #  by parsing the output of ',Wl,--trace'
      return [args[0]] + sources + resolvedPaths
    
    return link, scan

class WindowsGccCompiler(GccCompiler):
  
  objectSuffix = '.obj'
  libraryPrefixSuffixes = [('', '.lib'), ('lib', '.a')]
  moduleSuffix = '.dll'
  programSuffix = '.exe'

  @memoise
  def _getCommonLinkArgs(self, dll):
    args = GccCompiler._getCommonLinkArgs(self, dll)

    if dll:
      args.append('-shared')

    if self.optimisation == self.FULL_OPTIMISATION:
      args.append('-Wl,--gc-sections')
      
    return args

class MacGccCompiler(GccCompiler):

  @memoise
  def _getCommonLinkArgs(self, dll):
    args = GccCompiler._getCommonLinkArgs(self, dll)

    if dll:
      args.append('-shared')

    return args
  
class Ps3GccCompiler(GccCompiler):

  moduleSuffix = '.sprx'
  programSuffix = '.self'

  @memoise
  def _getCommonLinkArgs(self, dll):
    args = GccCompiler._getCommonLinkArgs(self, dll)

    if dll:
      args.append('-Wl,--oformat=fsprx')
    else:
      args.append('-Wl,--oformat=fself')

    if self.optimisation == self.FULL_OPTIMISATION:
      args.extend([
        '-Wl,-strip-unused',
        '-Wl,-strip-unused-data',
        ])
      
    return args
  