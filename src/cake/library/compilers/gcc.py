"""The Gcc Compiler.
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
from cake.library.compilers import Compiler, makeCommand

def getHostArchitecture():
  """Returns the current machines architecture.
  
  @return: The host architecture, or 'unknown' if the host
  architecture could not be determined.
  @rtype: string
  """
  try:
    return os.environ['PROCESSOR_ARCHITECTURE']
  except KeyError:
    return 'unknown'

def findExecutable(name, paths):
  """Find an executable given its name and a list of paths.  
  """
  for p in paths:
    executable = cake.path.join(p, name)
    if cake.filesys.isFile(executable):
      return executable
  else:
    raise EnvironmentError("Could not find executable.");

def getMinGWInstallDir():
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

  @raise EnvironmentError: When a valid MinGW compiler could not be found.
  """
  if architecture is None:
    architecture = getHostArchitecture()

  try:
    installDir = getMinGWInstallDir()
  except WindowsError:
    raise EnvironmentError("Could not find MinGW install directory.")

  gccExe = cake.path.join(installDir, "bin", "gcc.exe")
  arExe = cake.path.join(installDir, "bin", "ar.exe")
  
  compiler = GccCompiler(
    ccExe=gccExe,
    arExe=arExe,
    ldExe=gccExe,
    architecture=architecture,
    )

  return compiler

def findGccCompiler(architecture=None):
  """Returns a GCC compiler given an architecture.

  @param architecture: The machine architecture to compile for. If
  architecture is None then the current architecture is used.

  @raise EnvironmentError: When a valid gcc compiler could not be found.
  """
  if architecture is None:
    architecture = getHostArchitecture()

  paths = os.environ.get('PATH', '').split(os.path.pathsep)

  try:
    gccExe = findExecutable("gcc", paths)
    arExe = findExecutable("ar", paths)
  except EnvironmentError:
    raise EnvironmentError("Could not find GCC compiler and AR archiver.")
    
  compiler = GccCompiler(
    ccExe=gccExe,
    arExe=arExe,
    ldExe=gccExe,
    architecture=architecture,
    )

  return compiler

class GccCompiler(Compiler):

  _lineRegex = re.compile('# [0-9]+ "(?!\<)(?P<path>.+)"', re.MULTILINE)
  
  useSse = False
  
  def __init__(
    self,
    ccExe=None,
    arExe=None,
    ldExe=None,
    architecture=None,
    ):
    Compiler.__init__(self)
    self.__ccExe = ccExe
    self.__arExe = arExe
    self.__ldExe = ldExe
    self.__architecture = architecture
    
    if architecture == 'x86':
      self.objectSuffix = '.obj'
      self.libraryPrefixSuffixes = [('', '.lib'), ('lib', '.a')]
      self.moduleSuffix = '.dll'
      self.programSuffix = '.exe'
    elif architecture == 'ppu':
      self.moduleSuffix = '.sprx'
      self.programSuffix = '.self'

# TODO: Is this needed?
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
  def _getCommonArgs(self, language):
    # Almost all compile options can also set preprocessor defines (see
    # http://gcc.gnu.org/onlinedocs/cpp/Common-Predefined-Macros.html),
    # so for safety all compile options are shared across preprocessing
    # and compiling.
    # Note: To dump predefined compiler macros: 'echo | gcc -E -dM -'
    args = [self.__ccExe]

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

    if self.__architecture == 'x86':
      args.append("-m32")
    elif self.__architecture == 'x64':
      args.append("-m64")
      
    if self.useSse:
      args.append('-msse')
    
    return args

  @memoise
  def _getCompileArgs(self, language):
    args = list(self._getCommonArgs(language))
    
    args.append('-c')

    return args

  @memoise
  def _getPreprocessArgs(self, language):
    args = list(self._getCommonArgs(language))

    args.append('-E')
    
    for p in reversed(self.includePaths):
      args.extend(['-I', p])

# TODO: Should Lewis reverse defines?
    args.extend('-D' + d for d in reversed(self.defines))
    
# TODO: Should Lewis reverse this in msvc.py?    
    for p in reversed(self.forceIncludes):
      args.extend(['-include', p])

    return args
    
  def getObjectCommands(self, target, source, engine):
    
    language = self.language
    if not language:
      if source.lower().endswith('.c'):
        language = 'c'
      else:
        language = 'c++'
    
    preprocessTarget = target + '.ii'

    preprocessArgs = list(self._getPreprocessArgs(language))
    preprocessArgs += [source, '-o', preprocessTarget]
    
    compileArgs = list(self._getCompileArgs(language))
    compileArgs += [preprocessTarget, '-o', target]
    
    @makeCommand(preprocessArgs)
    def preprocess():
      self._executeProcess(preprocessArgs, preprocessTarget, engine)

    @makeCommand("obj-scan")
    def scan():
      engine.logger.outputDebug(
        "scan",
        "scan: %s\n" % preprocessTarget,
        )
      
      # TODO: Add dependencies on DLLs used by cc.exe
      dependencies = [self.__ccExe]
      uniqueDeps = set()

      with open(preprocessTarget, 'rb') as f:
        for match in self._lineRegex.finditer(f.read()):
          path = match.group('path').replace('\\\\', '\\')
          if path not in uniqueDeps:
            uniqueDeps.add(path)
            if not cake.filesys.isFile(path):
              engine.logger.outputDebug(
                "scan",
                "scan: Ignoring missing include '" + path + "'\n",
                )
            else:
              dependencies.append(path)

      return dependencies

    @makeCommand(compileArgs)
    def compile():
      self._executeProcess(compileArgs, target, engine)

    canBeCached = True
    return preprocess, scan, compile, canBeCached    

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
      # TODO: Add dependencies on DLLs used by lib.exe
      return [self.__arExe] + sources

    return archive, scan

  @memoise
  def _getCommonLinkArgs(self, dll):
    args = [self.__ldExe]

    if dll:
      args.append('-Wl,-shared')
    else:
      if self.__architecture == 'ppu':
        args.append('-Wl,--oformat=fself')

    if self.optimisation == self.FULL_OPTIMISATION:
      if self.__architecture == 'ppu':
        args.extend([
          '-Wl,-strip-unused',
          '-Wl,-strip-unused-data',
          ])
      else:
        args.append('-Wl,--gc-sections')
      
    return args
  
  def getProgramCommands(self, target, sources, engine):
    return self._getLinkCommands(target, sources, engine, dll=False)
  
  def getModuleCommands(self, target, sources, engine):
    return self._getLinkCommands(target, sources, engine, dll=True)

  def _getLinkCommands(self, target, sources, engine, dll):
    
    resolvedPaths, unresolvedLibs = self._resolveLibraries(engine)
    
    args = list(self._getCommonLinkArgs(dll))
    #args.extend('-L' + p for p in self.libraryPaths)
    args.extend(sources)
    args.extend(resolvedPaths)    
    args.extend('-l' + l for l in unresolvedLibs)    
    args.extend(['-o', target])
    
    @makeCommand(args)
    def link():
      self._executeProcess(args, target, engine)      
    
    @makeCommand("link-scan")
    def scan():
      # TODO: Add dependencies on DLLs used by ld.exe
      # TODO: Add dependencies on system libraries, perhaps
      #  by parsing the output of ',Wl,--trace'
      return [self.__ldExe] + sources + resolvedPaths
    
    return link, scan
