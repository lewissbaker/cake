"""The Microsoft Visual C++ Compiler.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

__all__ = ["MsvcCompiler", "findMsvcCompiler"]

import os
import os.path
import re
import threading

import cake.filesys
import cake.path
import cake.system
from cake.library.compilers import Compiler, makeCommand, CompilerNotFoundError
from cake.library import memoise, getPathsAndTasks
from cake.task import Task
from cake.msvs import getMsvcProductDir, getMsvsInstallDir, getPlatformSdkDir
from cake.engine import Script

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
  
  # Find the host bin dir for exe's such as 'cvtres.exe'
  if hostArchitecture == 'x86':
    msvcHostBinDir = cake.path.join(msvcProductDir, "bin")
  else:
    msvcHostArchitecture = _toArchitectureDir(hostArchitecture)
    msvcHostBinDir = cake.path.join(msvcProductDir, "bin", msvcHostArchitecture)
    
  msvcIncludeDir = cake.path.join(msvcProductDir, "include")
  platformSdkIncludeDir = cake.path.join(platformSdkDir, "Include")

  if architecture == 'x86':
    msvcLibDir = cake.path.join(msvcProductDir, "lib")
    platformSdkLibDir = cake.path.join(platformSdkDir, "Lib")
  elif architecture in ['x64', 'amd64']:
    msvcLibDir = cake.path.join(msvcProductDir, "lib", 'amd64')
    platformSdkLibDir = cake.path.join(platformSdkDir, "Lib", "amd64")
    # External Platform SDKs may use 'x64' instead of 'amd64'
    if not cake.filesys.isDir(platformSdkLibDir):
      platformSdkLibDir = cake.path.join(platformSdkDir, "Lib", "x64")
  elif architecture == 'ia64':
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
  
  binPaths = [msvcHostBinDir, msvsInstallDir]

  compiler = MsvcCompiler(
    configuration=configuration,
    clExe=clExe,
    libExe=libExe,
    linkExe=linkExe,
    rcExe=rcExe,
    mtExe=mtExe,
    binPaths=binPaths,
    architecture=architecture,
    )

  compiler.addIncludePath(msvcIncludeDir)
  compiler.addLibraryPath(msvcLibDir)
  compiler.addIncludePath(platformSdkIncludeDir)
  compiler.addLibraryPath(platformSdkLibDir)
  
  return compiler

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
        return _createMsvcCompiler(configuration, v, e, architecture, hostArchitecture)
      except WindowsError:
        # Try the next version/edition
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
  
  def __init__(
    self,
    configuration,
    clExe=None,
    libExe=None,
    linkExe=None,
    mtExe=None,
    rcExe=None,
    binPaths=None,
    architecture=None,
    ):
    Compiler.__init__(self, configuration=configuration, binPaths=binPaths)
    self.__clExe = clExe
    self.__libExe = libExe
    self.__linkExe = linkExe
    self.__mtExe = mtExe
    self.__rcExe = rcExe
    self.__architecture = architecture
    self.__messageExpression = re.compile(r'^(.+)\(\d+\) :', re.MULTILINE)
    self.forcedUsings = []
    self.forcedUsingScripts = []
    
  @property
  def architecture(self):
    return self.__architecture

  def addForcedUsing(self, assembly):
    """Add a .NET assembly to be forcibly referenced on the command-line.
    
    @param assembly: A path or FileTarget
    """
    self.forcedUsings.append(assembly)
    self._clearCache()
    
  def addForcedUsingScript(self, script):
    """Add a script that should be executed prior to any operation
    that makes use of the forcedUsings list of .NET assemblies.
    
    These scripts will typically build the .NET assembly that will
    be referenced on the command-line.
    """
    self.forcedUsingScripts.append(script)
    self._clearCache()

  def _formatMessage(self, inputText):
    """Format errors to be clickable in MS Visual Studio.
    """
    outputLines = []
    pos = 0
    while True:
      m = self.__messageExpression.search(inputText, pos)
      if m:
        path, = m.groups()
        startPos = m.start()
        endPos = startPos + len(path)
        if startPos != pos: 
          outputLines.append(inputText[pos:startPos])
        path = self.configuration.abspath(os.path.normpath(path))
        outputLines.append(path)
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
      
      if self.forcedUsingScripts:
        variant = Script.getCurrent().variant
        execute = self.configuration.execute
        for path in self.forcedUsingScripts:
          tasks.append(execute(path, variant))
          
      tasks.extend(getPathsAndTasks(self.forcedUsings)[1])
    
    return tasks
    
  @memoise
  def _getCompileCommonArgs(self, language):
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
 
    if language == 'c++':
      args.extend(self.cppFlags)

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
        
    elif language == 'c++/cli':
      args.extend(self.cppFlags)
      if self.clrMode == 'safe':
        args.append('/clr:safe') # Compile to verifiable CLR code
      elif self.clrMode == 'pure':
        args.append('/clr:pure') # Compile to pure CLR code 
      else:
        args.append('/clr') # Compile to mixed CLR/native code
        
      for assembly in getPathsAndTasks(self.forcedUsings)[0]:
        args.append('/FU' + assembly)

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
 
    args.extend("/D" + define for define in self.getDefines())
    args.extend("/I" + path for path in self.getIncludePaths())
    args.extend("/FI" + path for path in self.getForcedIncludes())

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
    
  def _getLanguage(self, path):
    language = self.language
    if language is None:
      if path[-2:].lower() == '.c':
        language = 'c'
      else:
        language = 'c++'
    return language

  def getPchCommands(self, target, source, header, object):
    language = self._getLanguage(source)
    
    args = list(self._getCompileCommonArgs(language))
    
    if language == 'c':
      args.append('/Tc' + source)
    else:
      args.append('/Tp' + source)

    args.extend([
      '/Yl' + _mungePathToSymbol(target),
      '/Fp' + target,
      '/Yc' + header,
      ])

    args.append('/Fo' + object)

    return self._getObjectCommands(target, source, args, None)
    
  def getObjectCommands(self, target, source, pch, shared):
    language = self._getLanguage(source)

    args = list(self._getCompileCommonArgs(language))
    
    if language == 'c':
      args.append('/Tc' + source)
    else:
      args.append('/Tp' + source)
      
    if pch is not None:
      args.extend([
        '/Yl' + _mungePathToSymbol(pch.path),
        '/Fp' + pch.path,
        '/Yu' + pch.header,
        ])
      deps = [pch.path]
    else:
      deps = []

    args.append('/Fo' + target)
    
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
        dependencies.extend(getPathsAndTasks(self.forcedUsings)[0])
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
      self._pdbQueueLock.acquire()
      try:
        predecessor = self._pdbQueue.get(absPdbFile, None)
        compileTask = self.engine.createTask(compile)
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
    canBeCached = pdbFile is None

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
      return [self.__libExe] + sources

    return archive, scan

  @memoise
  def _getLinkCommonArgs(self, dll):
    
    args = [self.__linkExe, '/NOLOGO']

    # XXX: MSVC8 linker complains about /errorReport being unrecognised.
    #if self.errorReport:
    #  args.append('/ERRORREPORT:%s' % self.errorReport.upper())
      
    if self.useIncrementalLinking is not None:
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
    
    if self.outputMapFile:
      args.append('/MAP')
    
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
  
  def getModuleCommands(self, target, sources):
    return self._getLinkCommands(target, sources, dll=True)

  def _getLinkCommands(self, target, sources, dll):
    
    objects, libraries = self._resolveObjects()
    
    absTarget = self.configuration.abspath(target)
    absTargetDir = cake.path.dirName(absTarget)
    
    args = list(self._getLinkCommonArgs(dll))

    if self.subSystem is not None:
      args.append('/SUBSYSTEM:' + self.subSystem)
    
    if self.debugSymbols and self.pdbFile is None:
      args.append('/PDB:%s.pdb' % target)
    
    if dll and self.importLibrary is not None:
      args.append('/IMPLIB:' + self.importLibrary)

    if self.optimisation == self.FULL_OPTIMISATION and \
       self.useIncrementalLinking:
      self.engine.raiseError(
        "Cannot set useIncrementalLinking with optimisation=FULL_OPTIMISATION\n"
        )
    
    if self.embedManifest:
      if not self.__mtExe:
        self.engine.raiseError(
          "You must set path to mt.exe with embedManifest=True\n"
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
            "You must set path to rc.exe with embedManifest=True and useIncrementalLinking=True\n"
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
    
    args.append('/OUT:' + target)
    args.extend(sources)
    args.extend(objects)

    # Msvc requires a .lib extension otherwise it will assume an .obj
    libraryPrefix, librarySuffix = self.libraryPrefixSuffixes[0]
    for l in libraries:
      if not cake.path.hasExtension(l):
        l = cake.path.forcePrefixSuffix(l, libraryPrefix, librarySuffix)
      args.append(l)
    
    @makeCommand(args)
    def link():
      if self.importLibrary:
        importLibrary = self.configuration.abspath(self.importLibrary)
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

        def processStdout(text):
          outputLines = text.splitlines()
  
          # Skip any leading logo output by some of the later versions of rc.exe
          if len(outputLines) >= 2 and \
             outputLines[0].startswith('Microsoft (R) Windows (R) Resource Compiler Version ') and \
             outputLines[1].startswith('Copyright (C) Microsoft Corporation.  All rights reserved.'):
            outputLines = outputLines[2:]
            
          if outputLines:
            self._outputStdout("\n".join(outputLines) + "\n")
        
        self._runProcess(
          args=rcArgs,
          target=embeddedRes,
          processStdout=processStdout,
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
            self.engine.raiseError("%s: failed with exit code %i\n" % (mtArgs[0], exitCode))
  
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
      return [self.__linkExe] + sources + objects + self._scanForLibraries(libraries)
    
    if self.embedManifest:
      if self.useIncrementalLinking:
        return linkWithManifestIncremental, scan
      else:
        return linkWithManifestNonIncremental, scan
    else:
      return link, scan

  @memoise
  def _getCommonResourceArgs(self):
    args = [self.__rcExe, '/nologo']
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
      self._runProcess(args, target, allowResponseFile=False)

    @makeCommand("rc-scan")
    def scan():
      # TODO: Add dependencies on DLLs used by rc.exe
      return [self.__rcExe, source]

    return compile, scan
