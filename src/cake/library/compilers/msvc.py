"""The Microsoft Visual C++ Compiler.
"""

__all__ = ["MsvcCompiler"]

import os
import os.path
import subprocess
import tempfile
import re
import threading
import weakref
import ctypes
import ctypes.wintypes
import platform

import cake.filesys
import cake.path
from cake.library.compilers import Compiler, makeCommand
from cake.library import memoise
from cake.task import Task
from cake.msvs import getMsvcProductDir, getMsvsInstallDir, getPlatformSdkDir

kernel32 = ctypes.windll.kernel32
IsWow64Process = kernel32.IsWow64Process
IsWow64Process.restype = ctypes.wintypes.BOOL
IsWow64Process.argtypes = (ctypes.wintypes.HANDLE,
                           ctypes.POINTER(ctypes.wintypes.BOOL))

GetCurrentProcess = kernel32.GetCurrentProcess
GetCurrentProcess.restype = ctypes.wintypes.HANDLE
GetCurrentProcess.argtypes = ()

def getHostArchitecture():
  """Returns the current machines architecture.
  """
  if platform.architecture()[0] == '32bit':
    result = ctypes.wintypes.BOOL()
    ok = IsWow64Process(GetCurrentProcess(), ctypes.byref(result))
    if not ok:
      raise WindowsError("IsWow64Process")

    if result.value == 1:
      return "x64"
    else:
      return "x86"
  else:
    # HACK: Could be IA-64 but who uses that these days?
    return "x64"

def findCompiler(
  version=None,
  architecture=None,
  ):
  """Returns an MSVC compiler given a version and architecture.
  
  Raises an EnvironmentError if a compiler or matching platform SDK
  cannot be found.
  
  @param version: The specific version to find. If version is None the
  latest version is found instead. 
  @param architecture: The machine architecture to compile for. If
  architecture is None then the current architecture is used.
  
  @raise ValueError: When an invalid architecture is passed in.
  @raise EnvironmentError: Then a valid compiler or Windows SDK could
  not be found.
  """
  # Valid architectures
  architectures = ['x86', 'x64', 'ia64']

  # Valid versions - prefer later versions over earlier ones
  versions = [
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
    ]

  # Determine host architecture
  hostArchitecture = getHostArchitecture()
  if hostArchitecture not in architectures:
    raise ValueError("Unknown host architecture '%s'." % hostArchitecture)

  # Default architecture is hostArchitecture
  if architecture is None:
    architecture = hostArchitecture
  elif architecture not in architectures:
    raise ValueError("Unknown architecture '%s'." % architecture)

  if version is not None:
    # Validate version
    if version not in versions:
      raise ValueError("Unknown version '%s'." % version)
    # Only check for this version
    versions = [version]

  for v in versions:
    found = False
    for e in editions:
      try:
        registryPath = e + '\\' + v
        msvsInstallDir = getMsvsInstallDir(registryPath)
        msvcProductDir = getMsvcProductDir(registryPath)
      
        # Use the compilers platform SDK if installed
        platformSdkDir = cake.path.join(msvcProductDir, "PlatformSDK")
        if not cake.filesys.isDir(platformSdkDir):
          platformSdkDir = getPlatformSdkDir()

        # Break when we have found all compiler dirs
        found = True
        break
      except WindowsError:
        # Try the next version/edition
        continue
    if found:
      break
  else:
    raise EnvironmentError(
      "Could not find Microsoft Visual Studio C++ compiler."
      )

  def toArchitectureDir(architecture):
    """Re-map 'x64' to 'amd64' to match MSVC directory names.
    """
    return {'x64' : 'amd64'}.get(architecture, architecture)

  if architecture == 'x86':
    # Root bin directory is always used for the x86 compiler
    msvcBinDir = cake.path.join(msvcProductDir, "bin")
  elif architecture != hostArchitecture:
    # Determine the bin directory for cross-compilers
    msvcBinDir = cake.path.join(
      msvcProductDir,
      "bin",
      "%s_%s" % (
        toArchitectureDir(hostArchitecture),
        toArchitectureDir(architecture),
        ),
      )
  else:
    # Determine the bin directory for 64-bit compilers
    msvcBinDir = cake.path.join(
      msvcProductDir,
      "bin",
      "%s" % toArchitectureDir(architecture),
      )
    
  clExe = cake.path.join(msvcBinDir, "cl.exe")
  libExe = cake.path.join(msvcBinDir, "lib.exe")
  linkExe = cake.path.join(msvcBinDir, "link.exe")
  rcExe = cake.path.join(msvcBinDir, "rc.exe")
  mtExe = cake.path.join(msvcBinDir, "mt.exe")

  if not cake.filesys.isFile(rcExe):
    rcExe = cake.path.join(platformSdkDir, "Bin", "rc.exe")
  if not cake.filesys.isFile(mtExe):
    mtExe = cake.path.join(platformSdkDir, "Bin", "mt.exe")
  
  dllPaths = [msvsInstallDir]
    
  compiler = MsvcCompiler(
    clExe=clExe,
    libExe=libExe,
    linkExe=linkExe,
    rcExe=rcExe,
    mtExe=mtExe,
    dllPaths=dllPaths,
    architecture=architecture,
    )

  msvcIncludeDir = cake.path.join(msvcProductDir, "include")
  platformSdkIncludeDir = cake.path.join(platformSdkDir, "Include")

  if architecture == 'x86':
    defines = ['WIN32']
    msvcLibDir = cake.path.join(msvcProductDir, "lib")
    platformSdkLibDir = cake.path.join(platformSdkDir, "Lib")
  elif architecture == 'x64':
    defines = ['WIN32', 'WIN64']
    msvcLibDir = cake.path.join(msvcProductDir, "lib", 'amd64')
    platformSdkLibDir = cake.path.join(platformSdkDir, "Lib", "amd64")
    # External Platform SDKs may use 'x64' instead of 'amd64'
    if not cake.filesys.isDir(platformSdkLibDir):
      platformSdkLibDir = cake.path.join(platformSdkDir, "Lib", "x64")
  elif architecture == 'ia64':
    defines = ['WIN32', 'WIN64']
    msvcLibDir = cake.path.join(msvcProductDir, "lib", 'ia64')
    platformSdkLibDir = cake.path.join(platformSdkDir, "Lib", "IA64")

  compiler.addIncludePath(msvcIncludeDir)
  compiler.addLibraryPath(msvcLibDir)
  compiler.addIncludePath(platformSdkIncludeDir)
  compiler.addLibraryPath(platformSdkLibDir)
  for d in defines:
    compiler.addDefine(d)

  return compiler

def _escapeArg(arg):
  if ' ' in arg:
    if '"' in arg:
      arg = arg.replace('"', '\\"')
    return '"%s"' % arg
  else:
    return arg

def _escapeArgs(args):
  return [_escapeArg(arg) for arg in args]

class MsvcCompiler(Compiler):

  name = 'msvc'

  _lineRegex = re.compile('#line [0-9]+ "(?P<path>.+)"', re.MULTILINE)
  
  _pdbQueue = {}
  _pdbQueueLock = threading.Lock()
  
  objectSuffix = '.obj'
  libraryPrefix = ''
  librarySuffix = '.lib'
  moduleSuffix = '.dll'
  programSuffix = '.exe'
  
  outputFullPath = True
  memoryLimit = None
  runtimeLibraries = None
  moduleVersion = None
  
  useStringPooling = False
  useMinimalRebuild = False
  useEditAndContinue = False
  
  errorReport = 'queue'
  
  def __init__(
    self,
    clExe=None,
    libExe=None,
    linkExe=None,
    mtExe=None,
    rcExe=None,
    dllPaths=None,
    architecture=None,
    ):
    super(MsvcCompiler, self).__init__()
    self.__clExe = clExe
    self.__libExe = libExe
    self.__linkExe = linkExe
    self.__mtExe = mtExe
    self.__rcExe = rcExe
    self.__dllPaths = dllPaths
    self.__architecture = architecture
    
  @property
  def architecture(self):
    return self.__architecture
    
  @memoise
  def _getCommonArgs(self, language):
    args = [
      self.__clExe,
      "/nologo",
      "/bigobj",
      ]
    
    if self.outputFullPath:
      args.append("/FC")

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
 
    if language == 'c++':
      if self.enableRtti:
        args.append('/GR') # Enable RTTI
      else:
        args.append('/GR-') # Disable RTTI
      
      if self.enableExceptions == "SEH":
        args.append('/EHa') # Enable SEH exceptions
      elif self.enableExceptions:
        args.append('/EHsc') # Enable exceptions
      else:
        args.append('/EHsc-') # Disable exceptions

    if self.optimisation == self.FULL_OPTIMISATION:
      args.append('/GL') # Global optimisation
    elif self.optimisation == self.PARTIAL_OPTIMISATION:
      args.append('/Ox') # Full optimisation
    elif self.optimisation == self.NO_OPTIMISATION:
      args.append('/Od') # No optimisation
 
    if self.warningLevel is not None:
      args.append('/W%s' % self.warningLevel)
      
    if self.warningsAsErrors:
      args.append('/WX')
 
    if self.errorReport:
      args.append('/errorReport:' + self.errorReport)
 
    return args 
    
  @memoise
  def _getPreprocessorCommonArgs(self, language):
    args = list(self._getCommonArgs(language))
   
    args.extend("/D" + define for define in self.defines)
    args.extend("/I" + path for path in reversed(self.includePaths))
    args.extend("/FI" + path for path in self.forceIncludes)

    args.append("/E")
    
    return args
    
  @property
  @memoise
  def _needPdbFile(self):
    if self.pdbFile is not None and self.debugSymbols:
      return True
    elif self.useMinimalRebuild or self.useEditAndContinue:
      return True
    else:
      return False
    
  @memoise
  def _getCompileCommonArgs(self, language):
    args = list(self._getCommonArgs(language))

    if self.useEditAndContinue:
      args.append("/ZI") # Output debug info to PDB (edit-and-continue)
    elif self._needPdbFile:
      args.append("/Zi") # Output debug info to PDB (no edit-and-continue)
    elif self.debugSymbols:
      args.append("/Z7") # Output debug info embedded in .obj
    
    if self.useMinimalRebuild:
      args.append("/Gm") # Enable minimal rebuild
    
    args.append("/c")
    args.append("/u")
    return args
    
  @memoise
  def _getProcessEnv(self):
    temp = os.environ.get('TMP', os.environ.get('TEMP', os.getcwd()))
    env = {
      'COMPSPEC' : os.environ.get('COMSPEC', ''),
      'PATHEXT' : ".com;.exe;.bat;.cmd",
      'SYSTEMROOT' : os.environ.get('SYSTEMROOT', ''),
      'TMP' : temp,
      'TEMP' : temp,  
      'PATH' : '.',
      }
    if self.__dllPaths is not None:
      env['PATH'] = os.path.pathsep.join(
        [env['PATH']] + self.__dllPaths
        )
    
    if env['SYSTEMROOT']:
      env['PATH'] = os.path.pathsep.join([
        env['PATH'],
        os.path.join(env['SYSTEMROOT'], 'System32'),
        env['SYSTEMROOT'],
        ])
      
    return env
    
  def getObjectCommands(self, target, source, engine):
    
    language = self.language
    if language is None:
      # Try to auto-detect
      if source.lower().endswith('.c'):
        language = 'c'
      else:
        language = 'c++'

    preprocessTarget = target + '.i'

    processEnv = dict(self._getProcessEnv())    
    compileArgs = list(self._getCompileCommonArgs(language))
    preprocessArgs = list(self._getPreprocessorCommonArgs(language))
    
    if language == 'c':
      preprocessArgs.append('/Tc' + source)
      compileArgs.append('/Tc' + preprocessTarget)
    else:
      preprocessArgs.append('/Tp' + source)
      compileArgs.append('/Tp' + preprocessTarget)

    if self._needPdbFile:
      pdbFile = self.pdbFile if self.pdbFile is not None else target + '.pdb'
      compileArgs.append('/Fd' + pdbFile)
    else:
      pdbFile = None

    compileArgs.append('/Fo' + target)
    
    preprocessorOutput = []
    
    @makeCommand(preprocessArgs + ['>', _escapeArg(preprocessTarget)])
    def preprocess():
      engine.logger.outputDebug(
        "run",
        "run: %s\n" % " ".join(preprocessArgs),
        )
      
      with tempfile.TemporaryFile() as errFile:
        # Launch the process
        try:
          p = subprocess.Popen(
            args=preprocessArgs,
            executable=self.__clExe,
            env=processEnv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=errFile,
            )
        except EnvironmentError, e:
          engine.raiseError("cake: failed to launch %s: %s\n" % (self.__clExe, str(e)))
        p.stdin.close()
        
        output = p.stdout.read()
        exitCode = p.wait()
        
        sourceName = cake.path.baseName(source)
        
        errFile.seek(0)
        for line in errFile:
          line = line.rstrip()
          if not line or line == sourceName:
            continue
          if 'error' in line:
            engine.logger.outputError(line + '\n')
          elif 'warning' in line:
            engine.logger.outputWarning(line + '\n')
          else:
            engine.logger.outputInfo(line + '\n')

        if exitCode != 0:
          raise engine.raiseError("cl: failed with exit code %i\n" % exitCode)

      cake.filesys.makeDirs(cake.path.dirName(preprocessTarget))
      with open(preprocessTarget, 'wb') as f:
        f.write(output)

      preprocessorOutput.append(output)

    @makeCommand("msvc-scan")
    def scan():
      engine.logger.outputDebug(
        "scan",
        "scan: %s\n" % preprocessTarget,
        )
      # TODO: Add dependencies on DLLs used by cl.exe
      dependencies = [self.__clExe]
      uniqueDeps = set()
      for match in self._lineRegex.finditer(preprocessorOutput[0]):
        path = match.group('path').replace('\\\\', '\\')
        if path not in uniqueDeps:
          uniqueDeps.add(path)
          dependencies.append(path)
      return dependencies
    
    @makeCommand(compileArgs)
    def compile():
      engine.logger.outputDebug(
        "run",
        "run: %s\n" % " ".join(compileArgs),
        )
      cake.filesys.makeDirs(cake.path.dirName(target))
      
      with tempfile.TemporaryFile() as errFile:
        try:
          p = subprocess.Popen(
            args=compileArgs,
            executable=self.__clExe,
            env=processEnv,
            stdin=subprocess.PIPE,
            stdout=errFile,
            stderr=subprocess.STDOUT,
            )
        except EnvironmentError, e:
          engine.raiseError("cake: failed to run %s: %s\n" % (self.__clExe, str(e)))
          
        p.stdin.close()
        
        exitCode = p.wait()
        
        sourceName = cake.path.baseName(preprocessTarget)
        
        errFile.seek(0)
        for line in errFile:
          line = line.rstrip()
          if not line or line == sourceName:
            continue
          if 'error' in line:
            engine.logger.outputError(line + '\n')
          elif 'warning' in line:
            engine.logger.outputError(line + '\n')
          else: 
            engine.logger.outputInfo(line + '\n')
        
      if exitCode != 0:
        engine.raiseError("cl: failed with code %i\n" % exitCode)
      
    @makeCommand(compileArgs)
    def compileWhenPdbIsFree():
      with self._pdbQueueLock:
        predecessor = self._pdbQueue.get(pdbFile, None)
        if predecessor is None or predecessor.completed:
          # No prior compiles using this .pdb can start this
          # one immediately in the same task.
          compileTask = Task.getCurrent()
          compileNow = True
        else:
          # Another compile task is using this .pdb
          # We'll start after it finishes
          compileTask = engine.createTask(compile)
          predecessor.addCallback(compileTask.start)
          compileNow = False
        self._pdbQueue[pdbFile] = compileTask
        
      if compileNow:
        compile()
      
    if pdbFile is not None:
      # Debug info is embedded in the .pdb so we can't cache the
      # object file without somehow pulling the .pdb along for
      # the ride.
      canBeCached = False
      return preprocess, scan, compileWhenPdbIsFree, canBeCached 
    else:
      # Debug info is embedded in the .obj so we can cache the
      # object file without losing debug info.
      canBeCached = True
      return preprocess, scan, compile, canBeCached

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
    else:
      args.append('/WX:NO')

    return args

  def getLibraryCommand(self, target, sources, engine):
    
    args = list(self._getCommonLibraryArgs())

    args.append('/OUT:' + _escapeArg(target))
    
    args.extend(_escapeArgs(sources))
    
    @makeCommand(args)
    def archive():

      engine.logger.outputDebug(
        "run",
        "run: %s\n" % " ".join(args),
        )
      
      argsFile = target + '.args'
      cake.filesys.makeDirs(cake.path.dirName(argsFile))
      with open(argsFile, 'wt') as f:
        for arg in args[2:]:
          f.write(arg + '\n')

      try:
        p = subprocess.Popen(
          args=[args[0], args[1], '@' + argsFile],
          executable=self.__libExe,
          env=self._getProcessEnv(),
          stdin=subprocess.PIPE,
          stdout=subprocess.PIPE,
          stderr=subprocess.STDOUT,
          )
      except EnvironmentError, e:
        engine.raiseError("cake: failed to launch %s: %s\n" % (self.__libExe, str(e)))
    
      p.stdin.close()
      output = p.stdout.readlines()
      exitCode = p.wait()
    
      for line in output:
        if not line.rstrip():
          continue
        if 'error' in line:
          engine.logger.outputError(line)
        elif 'warning' in line:
          engine.logger.outputWarning(line)
        else:
          engine.logger.outputInfo(line)
          
      if exitCode != 0:
        engine.raiseError("lib: failed with exit code %i\n" % exitCode)

    @makeCommand("lib-scan")
    def scan():
      # TODO: Add dependencies on DLLs used by lib.exe
      return [self.__libExe] + sources

    return archive, scan

  @memoise
  def _getLinkCommonArgs(self, dll):
    
    args = [self.__linkExe, '/NOLOGO']

    # XXX: MSVC8 linker complains about /errorReport being unrecognised.
    #if self.errorReport:
    #  args.append('/ERRORREPORT:%s' % self.errorReport.upper())
      
    if self.useIncrementalLinking:
      args.append('/INCREMENTAL')
    else:
      args.append('/INCREMENTAL:NO')
      
    if dll:
      args.append('/DLL')
      
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
    
    if self.outputMapFile:
      args.append('/MAP')
    
    if self.debugSymbols:
      args.append('/DEBUG')
      
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
    
    args.extend('/LIBPATH:' + path for path in self.libraryPaths)
    
    return args

  def getProgramCommands(self, target, sources, engine):
    return self._getLinkCommands(target, sources, engine, dll=False)
  
  def getModuleCommands(self, target, sources, engine):
    return self._getLinkCommands(target, sources, engine, dll=True)

  def _getLinkCommands(self, target, sources, engine, dll):
    
    libraryPaths = self._resolveLibraries(engine)
    sources = sources + libraryPaths
    
    args = list(self._getLinkCommonArgs(dll))

    if self.subSystem is not None:
      args.append('/SUBSYSTEM:' + self.subSystem)
    
    if self.debugSymbols and self.pdbFile is None:
      args.append('/PDB:%s.pdb' % target)
    
    if dll and self.importLibrary is not None:
      args.append('/IMPLIB:' + self.importLibrary)

    if self.optimisation == self.FULL_OPTIMISATION and \
       self.useIncrementalLinking:
      engine.raiseError("Cannot set useIncrementalLinking with optimisation=FULL_OPTIMISATION\n")
    
    if self.embedManifest:
      if not self.__mtExe:
        engine.raiseError("You must set path to mt.exe with embedManifest=True\n")
      
      manifestResourceId = 2 if dll else 1
      embeddedManifest = target + '.embed.manifest'
      if self.useIncrementalLinking:
        if not self.__rcExe:
          engine.raiseError("You must set path to rc.exe with embedManifest=True and useIncrementalLinking=True\n")
        
        intermediateManifest = target + '.intermediate.manifest'
        embeddedRc = embeddedManifest + '.rc'
        embeddedRes = embeddedManifest + '.res'
        args.append('/MANIFESTFILE:' + intermediateManifest)
        args.append(embeddedRes)
      else:
        args.append('/MANIFESTFILE:' + embeddedManifest)
    
    args.append('/OUT:' + target)
    args.extend(sources)
    
    @makeCommand(args)
    def link():
      engine.logger.outputDebug(
        "run",
        "run: %s\n" % " ".join(args),
        )
      
      argFile = target + '.args'
      cake.filesys.makeDirs(cake.path.dirName(argFile))
      with open(argFile, 'wt') as f:
        for arg in args[1:]:
          f.write(_escapeArg(arg) + '\n')

      if self.importLibrary:
        cake.filesys.makeDirs(cake.path.dirName(self.importLibrary))
      
      try:
        p = subprocess.Popen(
          args=[args[0], '@' + argFile],
          executable=self.__linkExe,
          env=self._getProcessEnv(),
          stdin=subprocess.PIPE,
          stdout=subprocess.PIPE,
          stderr=subprocess.STDOUT,
          )
      except EnvironmentError, e:
        engine.raiseError(
          "cake: failed to launch %s: %s\n" % (self.__linkExe, str(e))
          )

      p.stdin.close()
      output = p.stdout.readlines()
      exitCode = p.wait()
      
      for line in output:
        if not line.rstrip():
          continue
        engine.logger.outputInfo(line)
        
      if exitCode != 0:
        engine.raiseError("link: failed with exit code %i\n" % exitCode)
       
    @makeCommand(args) 
    def linkWithManifestIncremental():
      
      def compileRcToRes():
        
        rcArgs = [
          self.__rcExe,
          "/fo" + embeddedRes,
          embeddedRc,
          ]

        engine.logger.outputDebug(
          "run",
          "run: %s\n" % " ".join(rcArgs),
          )
        
        try:
          p = subprocess.Popen(
            args=rcArgs,
            executable=self.__rcExe,
            env=self._getProcessEnv(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            )
        except EnvironmentError, e:
          engine.raiseError("cake: failed to launch %s: %s\n" % (
            self.__rcExe,
            str(e),
            ))
          
        p.stdin.close()
        output = [line for line in p.stdout.readlines() if line.strip()]
        exitCode = p.wait()

        # Skip any leading logo output by some of the later versions of rc.exe
        if len(output) >= 2 and \
           output[0].startswith('Microsoft (R) Windows (R) Resource Compiler Version ') and \
           output[1].startswith('Copyright (C) Microsoft Corporation.  All rights reserved.'):
          output = output[2:]
        
        for line in output:
          engine.logger.outputInfo(line)
        
        if exitCode != 0:
          engine.raiseError("rc: failed with exit code %i" % exitCode)
      
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

        engine.logger.outputDebug(
          "run",
          "run: %s\n" % " ".join(mtArgs),
          )
        
        try:
          p = subprocess.Popen(
            args=mtArgs,
            executable=self.__mtExe,
            env=self._getProcessEnv(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            )
        except EnvironmentError, e:
          engine.raiseError("cake: failed to launch %s: %s\n" % (
            self.__mtExe,
            str(e),
            ))
          
        p.stdin.close()
        output = p.stdout.readlines()
        exitCode = p.wait()
        
        for line in output:
          if not line.rstrip():
            continue
          engine.logger.outputInfo(line)
        
        # The magic number here is the exit code output by the mt.exe
        # tool when the manifest file hasn't actually changed. We can
        # avoid a second link if the manifest file hasn't changed.
        
        if exitCode != 0 and exitCode != 1090650113:
          engine.raiseError("mt: failed with exit code %i\n" % exitCode)

        return exitCode != 0
      
      # Create an empty embeddable manifest if one doesn't already exist
      if not cake.filesys.isFile(embeddedManifest):
        engine.logger.outputInfo("Creating dummy manifest: %s\n" % embeddedManifest)
        open(embeddedManifest, 'wb').close()
      
      # Generate .embed.manifest.rc
      engine.logger.outputInfo("Creating %s\n" % embeddedRc)
      with open(embeddedRc, 'w') as f:
        # Use numbers so we don't have to include any headers
        # 24 - RT_MANIFEST
        f.write('%i 24 "%s"\n' % (
          manifestResourceId,
          embeddedManifest.replace("\\", "\\\\")
          ))
      
      compileRcToRes()
      link()
      
      if cake.filesys.isFile(intermediateManifest) and updateEmbeddedManifestFile():
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
      
      if not cake.filesys.isFile(embeddedManifest):
        engine.logger.outputInfo("Skipping embedding manifest: no manifest to embed\n")
        return
      
      mtArgs = [
        self.__mtExe,
        "/nologo",
        "/manifest", embeddedManifest,
        "/outputresource:%s;%i" % (target, manifestResourceId),
        ]
      
      engine.logger.outputDebug(
        "run",
        "run: %s\n" % " ".join(mtArgs),
        )
      
      try:
        p = subprocess.Popen(
          args=mtArgs,
          executable=self.__mtExe,
          env=self._getProcessEnv(),
          stdin=subprocess.PIPE,
          stdout=subprocess.PIPE,
          stderr=subprocess.STDOUT,
          )
      except EnvironmentError, e:
        engine.raiseError("cake: failed to launch %s: %s\n" % (
          self.__mtExe,
          str(e),
          ))
        
      p.stdin.close()
      output = p.stdout.readlines()
      exitCode = p.wait()
      
      for line in output:
        if not line.rstrip():
          continue
        if 'error' in line:
          engine.logger.outputError(line)
        else:
          engine.logger.outputInfo(line)
          
      if exitCode != 0:
        engine.raiseError("mt: failed with exit code %i\n" % exitCode)
        
    @makeCommand("link-scan")
    def scan():
      return [self.__linkExe] + sources
    
    if self.embedManifest:
      if self.useIncrementalLinking:
        return linkWithManifestIncremental, scan
      else:
        return linkWithManifestNonIncremental, scan
    else:
      return link, scan
  
