"""The Microsoft Visual C++ Compiler.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

__all__ = ["MsvcCompiler", "findMsvcCompiler"]

import sys
import os
import os.path
import subprocess
import tempfile
import re
import threading

import cake.filesys
import cake.path
import cake.system
from cake.library.compilers import Compiler, makeCommand, CompilerNotFoundError
from cake.library import memoise
from cake.task import Task
from cake.msvs import getMsvcProductDir, getMsvsInstallDir, getPlatformSdkDir

def _toArchitectureDir(architecture):
  """Re-map 'x64' to 'amd64' to match MSVC directory names.
  """
  return {'x64':'amd64'}.get(architecture, architecture)

def _createMsvcCompiler(
  version,
  edition,
  architecture,
  hostArchitecture,
  ):
  """Attempt to create an MSVC compiler.
  
  @raise WindowsError: If the compiler could not be created.
  @return: The newly created compiler.
  @rtype: L{MsvcCompiler}
  """
  registryPath = edition + '\\' + version
  msvsInstallDir = getMsvsInstallDir(registryPath)
  msvcProductDir = getMsvcProductDir(registryPath)

  # Use the compilers platform SDK if installed
  platformSdkDir = cake.path.join(msvcProductDir, "PlatformSDK")
  if not cake.filesys.isDir(platformSdkDir):
    platformSdkDir = getPlatformSdkDir()

  if architecture == 'x86':
    # Root bin directory is always used for the x86 compiler
    msvcBinDir = cake.path.join(msvcProductDir, "bin")
  else:
    msvcArchitecture = _toArchitectureDir(architecture)
    msvcHostArchitecture = _toArchitectureDir(hostArchitecture)
    
    if msvcArchitecture != msvcHostArchitecture:
      # Determine the bin directory for cross-compilers
      msvcBinDir = cake.path.join(
        msvcProductDir,
        "bin",
        "%s_%s" % (
          msvcHostArchitecture,
          msvcArchitecture,
          ),
        )
    else:
      # Determine the bin directory for 64-bit compilers
      msvcBinDir = cake.path.join(
        msvcProductDir,
        "bin",
        "%s" % msvcArchitecture,
        )
  
  msvcIncludeDir = cake.path.join(msvcProductDir, "include")
  platformSdkIncludeDir = cake.path.join(platformSdkDir, "Include")

  if architecture == 'x86':
    defines = ['WIN32']
    msvcLibDir = cake.path.join(msvcProductDir, "lib")
    platformSdkLibDir = cake.path.join(platformSdkDir, "Lib")
  elif architecture in ['x64', 'amd64']:
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

  clExe = cake.path.join(msvcBinDir, "cl.exe")
  libExe = cake.path.join(msvcBinDir, "lib.exe")
  linkExe = cake.path.join(msvcBinDir, "link.exe")
  rcExe = cake.path.join(msvcBinDir, "rc.exe")
  mtExe = cake.path.join(msvcBinDir, "mt.exe")

  if not cake.filesys.isFile(rcExe):
    rcExe = cake.path.join(platformSdkDir, "Bin", "rc.exe")
  if not cake.filesys.isFile(mtExe):
    mtExe = cake.path.join(platformSdkDir, "Bin", "mt.exe")

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

  checkDirectory(msvcIncludeDir)
  checkDirectory(platformSdkIncludeDir)
  checkDirectory(msvcLibDir)
  checkDirectory(platformSdkLibDir)

  compiler = MsvcCompiler(
    clExe=clExe,
    libExe=libExe,
    linkExe=linkExe,
    rcExe=rcExe,
    mtExe=mtExe,
    dllPaths=[msvsInstallDir],
    architecture=architecture,
    )

  compiler.addIncludePath(msvcIncludeDir)
  compiler.addLibraryPath(msvcLibDir)
  compiler.addIncludePath(platformSdkIncludeDir)
  compiler.addLibraryPath(platformSdkLibDir)
  
  for d in defines:
    compiler.addDefine(d)

  return compiler

def findMsvcCompiler(
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
  
  @return: A newly created MSVC compiler.
  @rtype: L{MsvcCompiler}
  
  @raise ValueError: When an invalid version or architecture is passed in.
  @raise CompilerNotFoundError: When a valid compiler or Windows SDK
  could not be found.
  """
  # Valid architectures
  architectures = ['x86', 'x64', 'amd64', 'ia64']

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
  hostArchitecture = cake.system.architecture().lower()
  if hostArchitecture not in architectures:
    raise ValueError("Unknown host architecture '%s'." % hostArchitecture)

  # Default architecture is hostArchitecture
  if architecture is None:
    architecture = hostArchitecture
  else:
    architecture = architecture.lower()
    if architecture not in architectures:
      raise ValueError("Unknown architecture '%s'." % architecture)

  if version is not None:
    # Validate version
    if version not in versions:
      raise ValueError("Unknown version '%s'." % version)
    # Only check for this version
    versions = [version]

  for v in versions:
    for e in editions:
      try:
        return _createMsvcCompiler(v, e, architecture, hostArchitecture)
      except WindowsError:
        # Try the next version/edition
        pass
  else:
    raise CompilerNotFoundError(
      "Could not find Microsoft Visual Studio C++ compiler."
      )

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

  _lineRegex = re.compile('#line [0-9]+ "(?P<path>.+)"', re.MULTILINE)
  
  _pdbQueue = {}
  _pdbQueueLock = threading.Lock()
  
  objectSuffix = '.obj'
  libraryPrefixSuffixes = [('', '.lib')]
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
  def _getCompileCommonArgs(self, language):
    args = [
      self.__clExe,
      "/nologo",
      "/bigobj",
      "/showIncludes",
      ]

    if self.errorReport:
      args.append('/errorReport:' + self.errorReport)

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
      args.extend(self.cppFlags)

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
    else:
      args.extend(self.cFlags)

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

    if self.useEditAndContinue:
      args.append("/ZI") # Output debug info to PDB (edit-and-continue)
    elif self._needPdbFile:
      args.append("/Zi") # Output debug info to PDB (no edit-and-continue)
    elif self.debugSymbols:
      args.append("/Z7") # Output debug info embedded in .obj
    
    if self.useMinimalRebuild:
      args.append("/Gm") # Enable minimal rebuild
    
    args.append("/c")
 
    args.extend("/D" + define for define in self.defines)
    args.extend("/I" + path for path in reversed(self.includePaths))
    args.extend("/FI" + path for path in self.forcedIncludes)

 
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

    processEnv = dict(self._getProcessEnv())    
    compileArgs = list(self._getCompileCommonArgs(language))
    
    if language == 'c':
      compileArgs.append('/Tc' + source)
    else:
      compileArgs.append('/Tp' + source)

    if self._needPdbFile:
      if self.pdbFile is not None:
        pdbFile = self.pdbFile
      else:
        pdbFile = target + '.pdb'
      compileArgs.append('/Fd' + pdbFile)
    else:
      pdbFile = None

    compileArgs.append('/Fo' + target)
    
    def compile():
      engine.logger.outputDebug(
        "run",
        "run: %s\n" % " ".join(compileArgs),
        )

      cake.filesys.makeDirs(cake.path.dirName(target))
      
      errFile = tempfile.TemporaryFile()
      try:
        # Launch the process
        try:
          p = subprocess.Popen(
            args=compileArgs,
            executable=self.__clExe,
            env=processEnv,
            stdin=subprocess.PIPE,
            stdout=errFile,
            stderr=errFile,
            )
        except EnvironmentError, e:
          engine.raiseError(
            "cake: failed to launch %s: %s\n" % (self.__clExe, str(e))
            )
        p.stdin.close()
        
        exitCode = p.wait()
        
        sourceName = cake.path.baseName(source)

        errFile.seek(0)
        output = errFile.read()

        includePrefix = ('Note: including file:')
        includePrefixLen = len(includePrefix)

        dependencies = [self.__clExe, source]
        dependenciesSet = set()
        
        for line in output.decode("latin1").splitlines():
          line = line.rstrip()
          if not line or line == sourceName:
            continue
          if line.startswith(includePrefix):
            path = line[includePrefixLen:].lstrip()
            normPath = os.path.normcase(os.path.normpath(path))
            if normPath not in dependenciesSet:
              dependenciesSet.add(normPath)
              dependencies.append(path)
          else:
            sys.stderr.write(line + '\n')
        sys.stderr.flush()

        if exitCode != 0:
          raise engine.raiseError("cl: failed with exit code %i\n" % exitCode)
      finally:
        errFile.close()        
      
      return dependencies
      
    def compileWhenPdbIsFree():
      self._pdbQueueLock.acquire()
      try:
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
      finally:
        self._pdbQueueLock.release()
        
      if compileNow:
        return compile()
      else:
        return compileTask
      
    # Can only cache the object if it's debug info is not going into
    # a .pdb since multiple objects could all put their debug info
    # into the same .pdb.
    canBeCached = pdbFile is None

    def startCompile():
      if pdbFile is None:
        compileTask = engine.createTask(compile)
      else:
        compileTask = engine.createTask(compileWhenPdbIsFree)
      compileTask.start(immediate=True)
      return compileTask
      
    return startCompile, compileArgs, canBeCached

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
      f = open(argsFile, 'wt')
      try:
        for arg in args[2:]:
          f.write(arg + '\n')
      finally:
        f.close()            

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
        sys.stderr.write(line)
      sys.stderr.flush()
          
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
      args.extend(self.moduleFlags)
    else:
      args.extend(self.programFlags)
      
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
    
    args.extend('/LIBPATH:' + path for path in reversed(self.libraryPaths))
    
    return args

  def getProgramCommands(self, target, sources, engine):
    return self._getLinkCommands(target, sources, engine, dll=False)
  
  def getModuleCommands(self, target, sources, engine):
    return self._getLinkCommands(target, sources, engine, dll=True)

  def _getLinkCommands(self, target, sources, engine, dll):
    
    resolvedPaths, unresolvedLibs = self._resolveLibraries(engine)
    sources = sources + resolvedPaths
    
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
      
      if dll:
        manifestResourceId = 2
      else:
        manifestResourceId = 1
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
    args.extend(unresolvedLibs)
    
    @makeCommand(args)
    def link():
      engine.logger.outputDebug(
        "run",
        "run: %s\n" % " ".join(args),
        )
      
      argFile = target + '.args'
      cake.filesys.makeDirs(cake.path.dirName(argFile))
      f = open(argFile, 'wt')
      try:      
        for arg in args[1:]:
          f.write(_escapeArg(arg) + '\n')
      finally:
        f.close()

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
      output = p.stdout.read()
      exitCode = p.wait()
      
      for line in output.decode("latin1").splitlines():
        if not line.rstrip():
          continue
        sys.stderr.write(line)
      sys.stderr.flush()

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
          sys.stderr.write(line)
        sys.stderr.flush()
        
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
          sys.stderr.write(line)
        sys.stderr.flush()
        
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
      f = open(embeddedRc, 'w')
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
        sys.stderr.write(line)
      sys.stderr.flush()

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
  
