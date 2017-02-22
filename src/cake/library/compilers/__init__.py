"""Base Class and Utilities for C/C++ Compiler Tools.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import sys
import weakref
import os
import os.path
import datetime
import tempfile
import subprocess
import itertools
try:
  import cPickle as pickle
except ImportError:
  import pickle

import cake.filesys
import cake.hash
import cake.path
import cake.system
import cake.zipping

from cake.gnu import parseDependencyFile
from cake.async import AsyncResult, waitForAsyncResult, flatten, getResult
from cake.target import FileTarget, getPath, getPaths, getTask, getTasks
from cake.task import Task
from cake.library import Tool, memoise
from cake.script import Script

def _totalSeconds(td):
  """Return the total number of seconds for a datetime.timedelta value.
  """
  return (td.microseconds + (
    td.seconds + td.days * 24 * 3600) * 10**6) / float(10**6)

class CompilerNotFoundError(Exception):
  """Exception raised when a compiler cannot be found.
  
  This exception may be raised by the findCompiler() group of
  functions such as L{cake.library.compilers.msvc.findMsvcCompiler}
  and L{cake.library.compilers.gcc.findGccCompiler}.
  """
  pass

class CompilerTarget(FileTarget):
  """Base class for compiler targets.

  @ivar compiler: The compiler usd to build the target.
  @type compiler: L{Compiler}
  """  
  def __init__(self, path, task, compiler):
    FileTarget.__init__(self, path, task)
    self.compiler = compiler

class PchTarget(CompilerTarget):
  """A precompiled header target.

  @ivar pch: The pch file target.
  @type pch: L{FileTarget}
  @ivar object: The object file target.
  @type object: L{FileTarget}
  @ivar header: The #include used to build the pch.
  @type header: string
  """
  def __init__(self, path, task, compiler, header, object):
    CompilerTarget.__init__(self, path, task, compiler)
    self.pch = FileTarget(path, task)
    if object is None:
      self.object = None
    else:
      self.object = FileTarget(object, task)
    self.header = header

class ObjectTarget(CompilerTarget):
  """An object target.

  @ivar object: The object file target.
  @type object: L{FileTarget}
  """
  def __init__(self, path, task, compiler):
    CompilerTarget.__init__(self, path, task, compiler)
    self.object = FileTarget(path, task)
  
class LibraryTarget(CompilerTarget):
  """A library target.

  @ivar library: The library file target.
  @type library: L{FileTarget}
  """
  def __init__(self, path, task, compiler):
    CompilerTarget.__init__(self, path, task, compiler)
    self.library = FileTarget(path, task)

class ModuleTarget(CompilerTarget):
  """A module target.

  @ivar module: The module file target.
  @type module: L{FileTarget}
  @ivar library: An optional import library file target.
  @type library: L{FileTarget}
  @ivar manifest: An optional manifest file target.
  @type manifest: L{FileTarget}
  """
  def __init__(self, path, task, compiler, library, manifest):
    CompilerTarget.__init__(self, path, task, compiler)
    self.module = FileTarget(path, task)
    if library is None:
      self.library = None
    else:
      self.library = FileTarget(library, task)
    if manifest is None:
      self.manifest = None
    else:
      self.manifest = FileTarget(manifest, task)

class ProgramTarget(CompilerTarget):
  """A program target.

  @ivar program: The program file target.
  @type program: L{FileTarget}
  @ivar manifest: An optional manifest file target.
  @type manifest: L{FileTarget}
  """
  def __init__(self, path, task, compiler, manifest):
    CompilerTarget.__init__(self, path, task, compiler)
    self.program = FileTarget(path, task)
    if manifest is None:
      self.manifest = None
    else:
      self.manifest = FileTarget(manifest, task)

class ResourceTarget(CompilerTarget):
  """A resource target.

  @ivar resource: The resource file target.
  @type resource: L{FileTarget}
  """
  def __init__(self, path, task, compiler):
    CompilerTarget.__init__(self, path, task, compiler)
    self.resource = FileTarget(path, task)

def getLinkPaths(files):
  paths = []
  for f in files:
    while isinstance(f, AsyncResult):
      f = f.result
    if isinstance(f, PchTarget):
      if f.object is not None:
        paths.append(f.object.path)
    elif isinstance(f, FileTarget):
      paths.append(f.path)
    else:
      paths.append(f)
  return paths

def getLibraryPaths(files):
  paths = []
  for f in files:
    while isinstance(f, AsyncResult):
      f = f.result
    if isinstance(f, (list, set, tuple)):
      paths.extend(getLibraryPaths(f))
    elif isinstance(f, ModuleTarget):
      paths.append(f.library.path)
    elif isinstance(f, FileTarget):
      paths.append(f.path)
    else:
      paths.append(f)
  return paths

class Command(object):
  
  def __init__(self, args, func):
    self.args = args
    self.func = func
    
  def __repr__(self):
    return repr(self.args)
  
  def __call__(self, *args):
    return self.func(*args)

def makeCommand(args):
  def run(func):
    return Command(args, func)
  return run

def _escapeArg(arg):
  if ' ' in arg:
    return '"' + arg + '"'
  else:
    return arg

def _escapeArgs(args):
  return [_escapeArg(arg) for arg in args]

class Compiler(Tool):
  """Base class for C/C++ compiler tools.
  """
  
  NO_OPTIMISATION = 0
  """No optimisation.
  
  Your code should run slowest at this level, but debugging should
  be easiest. The code you step through with a debugger should closely
  match the original source.
  
  Related compiler options::
    GCC:  -O0
    MSVC: /Od
    MWCW: -opt off
  """
  PARTIAL_OPTIMISATION = 1
  """Code is partially optimised.
  
  Depending on the compiler this may include everything up to but
  not including link-time code generation.

  Related compiler options::
    GCC:  -O2
    MSVC: /Ox
    MWCW: -opt level=2  
  """
  FULL_OPTIMISATION = 2
  """Code is fully optimised.
  
  This may include link-time code generation for compilers that
  support it.

  Related compiler options::
    GCC:  -O4
    MSVC: /GL
    MWCW: -opt level=4  
  """
  MSVS_CLICKABLE = 0
  """Messages are clickable in Microsoft Visual Studio.
  
  When this options is chosen compiler warnings and error messages
  will be formatted to be clickable in Microsoft Visual Studio.
  
  The format of each message will be as follows::
  sourceFile(lineNumber) : message
  
  Note that if 'MsvcCompiler.outputFullPath' is set to False this
  option may need to be enabled so that relative source file paths
  are converted to clickable absolute paths. 
  """
  debugSymbols = None
  """Enable debug symbols.

  Enabling debug symbols will allow you to debug your code, but will
  significantly increase the size of the executable.

  Related compiler options::
    GCC:  -g
    MSVC: /Z7
    MWCW: -sym dwarf-2
  @type: bool
  """
  keepDependencyFile = False
  """Whether to keep the compiler generated dependency file.
  
  If the value is set then Cake will keep the compiler generated dependency
  file after a build. The dependency file is used by Cake to obtain a list
  of source files an object file is dependent on. It will be located next to
  the target object file with a '.d' extension. This switch is only relevant
  for compilers that use a dependency file (eg. GCC/MWCW).
  
  Related compiler options::
    GCC/MWCW:  -MD
  @type: bool
  """
  optimisation = None
  """Set the optimisation level.
  
  Available enum values are: L{NO_OPTIMISATION} L{PARTIAL_OPTIMISATION}
  L{FULL_OPTIMISATION}

  If the value is None the compiler default is used.
  @type: enum or None
  """
  messageStyle = None
  """Set the message style.
  
  Available enum values are: L{MSVS_CLICKABLE}

  If the value is None the compiler default output is used.
  @type: enum or None
  """
  enableRtti = None
  """Enable Run-Time Type Information for C++ compilation.
  
  Disabling RTTI can reduce the executable size, but will prevent you from
  using dynamic_cast to downcast between classes, or typeid() to determine
  the type of a class or struct.

  If the value is None the compiler default is used.

  Related compiler options::
    GCC:  -frtti
    MSVC: /GR
    MWCW: -RTTI on
  @type: bool or None 
  """
  enableExceptions = None
  """Enable exception handling.
  
  Disabling exceptions can significantly reduce the size of the executable.  

  If the value is None the compiler default is used.

  Related compiler options::
    GCC:  -fexceptions
    MSVC: /EHsc
    MWCW: -cpp_exceptions on  
  @type: bool or None
  """  
  warningLevel = None
  """Set the warning level.
  
  What the warning level does may depend on the compiler, but in general
  setting it to 0 will disable all warnings, and setting it to 4 will
  enable all warnings.
  
  If the value is None the compiler default is used.

  Related compiler options (warning level 0)::
    GCC:  -w
    MSVC: /W0

  Related compiler options (warning level 4)::
    GCC:  -Wall
    MSVC: /W4
  @type: int or None
  """
  warningsAsErrors = None
  """Treat warnings as errors.
  
  If enabled warnings will be treated as errors and may prevent compilation
  from succeeding.

  Related compiler options::
    GCC:  -Werror
    MSVC: /WX
    MWCW: -w error  
  @type: bool
  """
  linkObjectsInLibrary = None
  """Link objects rather than libraries.
  
  Linking objects can provide faster program/module links, especially
  if incremental linking is also enabled.

  Note that libraries will still be built, but only the object files will
  be passed to the compilers link line.
  
  If the linker you're using doesn't support response files then linking
  objects may quickly cause the link command line to go over the command
  line limit, causing your link to fail with unexpected results. 
  @type: bool
  """
  outputMapFile = None
  """Output a map file.
  
  If enabled the compiler will output a map file that matches the name of
  the executable with an appropriate extension (usually .map). The map file
  will contain a list of symbols used in the program or module and their
  addresses.

  Related compiler options::
    GCC:  -Map=<target>.map
    MSVC: /MAP:<target>.map
    MWCW: -map <target>.map
  @type: bool
  """
  useResponseFile = None
  """Use a response file.
  
  If enabled a response file will be generated containing the compiler
  command line options, and this file will be passed to the compiler
  rather than the options themselves.
  
  This enables you to compile large projects on systems that have
  restrictive command line length limits.
  
  Note that not all compiler versions will support response files, so
  turning it on may prevent compilation from succeeding.
  @type: bool
  """
  useIncrementalLinking = None
  """Use incremental linking.
  
  Incremental linking may speed up linking, but will also increase the size
  of the program or module.

  If the value is None the compiler default is used.

  Related compiler options::
    MSVC: /INCREMENTAL
  @type: bool
  """
  useFunctionLevelLinking = None
  """Use function-level linking.
  
  When function-level linking is enabled the linker will strip out any unused
  functions. For some compilers this option will also strip out any unused
  data.
  
  If the value is None the compiler default is used.

  Related compiler options::
    GCC:  -ffunction-sections, -fdata-sections, --gc-sections
    MSVC: /Gy, /OPT:REF, /OPT:ICF
  @type: bool
  """
  stackSize = None
  """Set the stack size of a program or module.
  
  If the value is None the compiler will use it's default stack sizes.
  If the value is a single int then the value is the stack reserve size.
  If the value is a tuple(int, int) then the first value is the reserve
  size and the second value is the commit size.
   
  Note that some compilers may require you to set the stack size in the linker
  script instead (see L{linkerScript}).
  
  Related compiler options::
    MSVC: /STACK
  @type: None or int or tuple(int, int)
  """
  heapSize = None
  """Set the heap size of a program or module.
  
  If the value is None the compiler will use it's default heap sizes.
  If the value is a single int then the value is the heap reserve size.
  If the value is a tuple(int, int) then the first value is the reserve
  size and the second value is the commit size.

  Related compiler options::
    MSVC: /HEAP
  @type: None or int or tuple(int, int)
  """
  linkerScript = None
  """Set the linker script for a program or module.
  
  This should be set to the path of linker script file.

  Related compiler options::
    MWCW: -lcf <linkerScript>
  @type: string or None
  """
  objectCachePath = None
  """Set the path to the object cache.
  
  Setting this to a path will enable caching of object files for
  compilers that support it. If an object file with the same checksum of
  dependencies exists in the cache then it will be copied from the cache
  rather than being compiled.
  
  You can share an object cache with others by putting the object cache
  on a network share. You will also have to make sure all of your project
  paths match. This could be done by using a virtual drive. An alternative
  is to set a workspace root, but this can be problematic for debugging
  (see L{objectCacheWorkspaceRoot}).
  
  If the value is None then object caching will be turned off.
  @type: string or None
  """
  objectCacheWorkspaceRoot = None
  """Set the object cache workspace root.
  
  Set this if the object cache is to be shared across workspaces.
  This will cause objects and their dependencies under this directory
  to be stored as paths relative to this directory. This allows 
  workspaces at different paths to reuse object files with the 
  potential danger of debug information embedded in the object
  files referring to paths in the wrong workspace.
  @type: string or None
  """
  language = None
  """Set the compilation language.
  
  If the value is set then the compiler will compile all source files
  using the specified language. Example languages are 'c', 'c++'.  
  If the value is None then the language is determined automatically
  based on the extension of each source file.
  
  Related compiler options::
    GCC:  -x <language>
    MSVC: /Tc or /Tp
    MWCW: -lang <language>
  @type: string or None
  """
  pdbFile = None
  """Set the path to the program database file.
  
  If set to a string path the program database file will be generated
  at the given path.
  
  If set to None a program database may still be generated with the
  name of the executable and the extension .pdb.
  
  Related compiler options::
    MSVC: /PDB
  @type: string or None
  """
  strippedPdbFile = None
  """Set the path to the stripped program database file.
  
  If set to a string path a stripped version of the PDB file will be
  generated at the given path. The stripped version will only include
  public symbols. It will not contain type information or line number
  information.
  
  If set to None a stripped PDB file will not be generated.

  Related compiler options::
    MSVC: /PDBSTRIPPED   
  @type: string or None
  """
  subSystem = None
  """Set the sub-system.
  
  Set the sub-system for a Windows executable build. Possible values
  are CONSOLE, NATIVE, POSIX, WINDOWS, WINDOWSCE. The optional values
  [,major[.minor]] can be appended that specify the minimum required
  version of the sub-system.
  
  If set to None and WinMain or wWinMain is defined, WINDOWS will
  be the default.
  If set to None and main or wmain is defined, CONSOLE will be the
  default.
    
  Related compiler options::
    MSVC: /SUBSYSTEM
  @type: string or None
  """
  embedManifest = None
  """Embed the manifest in the executable.
  
  If True the manifest file is embedded within the executable, otherwise
  no manifest file is generated.

  Related compiler options::
    MSVC: /MANIFESTFILE
  @type: bool
  """
  useSse = None
  """Use Streaming SIMD Extensions.
  
  If SSE if turned on the compiler may choose to optimise scalar floating
  point math by using SSE instructions and registers that can perform
  multiple operations in parallel.
  
  Note that if this value is turned on it is up to you to make sure the
  architecture you are compiling for supports SSE instructions.

  Related compiler options::
    GCC: -msse
  @type: bool
  """
  cSuffixes = frozenset(['.c'])
  """A collection of valid c file suffixes.
  
  @type: set of string
  """
  cppSuffixes = frozenset(['.C', '.cc', '.cp', '.cpp', '.CPP', '.cxx', '.c++'])
  """A collection of valid c++ file suffixes.
  
  @type: set of string
  """
  mSuffixes = frozenset(['.m'])
  """A collection of valid objective c file suffixes.
  
  @type: set of string
  """
  mmSuffixes = frozenset(['.M', '.mm'])
  """A collection of valid objective c++ file suffixes.
  
  @type: set of string
  """
  sSuffixes = frozenset(['.s'])
  """A collection of valid assembler file suffixes.
  
  @type: set of string
  """
  objectSuffix = '.o'
  """The suffix to use for object files.
  
  @type: string
  """
  libraryPrefixSuffixes = [('lib', '.a')]
  """A collection of valid library file prefixes and suffixes.
  
  The first prefix and suffix in the collection will be used as the
  default prefix/suffix.
  
  @type: list of tuple(string, string)
  """
  modulePrefixSuffixes = [('lib', '.so')]
  """The suffix to use for module files.

  @type: string
  """
  programSuffix = ''
  """The suffix to use for program files.

  @type: string
  """
  pchSuffix = '.gch'
  """The suffix to use for precompiled header files.

  @type: string
  """
  pchObjectSuffix = None
  """The suffix to use for precompiled header object files.

  @type: string or None
  """
  manifestSuffix = None
  """The suffix to use for manifest files.

  @type: string or None
  """
  resourceSuffix = '.o'
  """The suffix to use for resource files.

  @type: string or None
  """
  
  # The name of this compiler
  _name = 'unknown'

  # Map of engine to map of library path to list of object paths
  __libraryObjects = weakref.WeakKeyDictionary()
  
  def __init__(
    self,
    configuration,
    binPaths=None,
    includePaths=None,
    libraryPaths=None,
    ):
    super(Compiler, self).__init__(configuration)
    self.cFlags = []
    self.cppFlags = []
    self.mFlags = []
    self.mmFlags = []
    self.libraryFlags = []
    self.moduleFlags = []
    self.programFlags = []
    self.resourceFlags = []
    if includePaths is None:
      self.includePaths = []
    else:
      self.includePaths = includePaths
    self.defines = []
    self.forcedIncludes = []
    if libraryPaths is None:
      self.libraryPaths = []
    else:
      self.libraryPaths = libraryPaths
    self.libraries = []
    self.modules = []
    self.objectPrerequisites = []
    self.__binPaths = binPaths

  @property
  def name(self):
    """Get the name of the compiler, eg. 'gcc' or 'msvc'.
    """
    return self._name

  @property
  def libraryPrefix(self):
    """The prefix to use for library files.
    """
    return self.libraryPrefixSuffixes[0][0]

  @property
  def librarySuffix(self):
    """The suffix to use for library files.
    """
    return self.libraryPrefixSuffixes[0][1]
    
  def addCFlag(self, flag):
    """Add a flag to be used during .c compilation.
    
    @param flag: The flag to add.
    @type flag: string
    """
    self.cFlags.append(flag)
    self._clearCache()
    
  def addCppFlag(self, flag):
    """Add a flag to be used during .cpp compilation.
    
    @param flag: The flag to add.
    @type flag: string
    """
    self.cppFlags.append(flag)
    self._clearCache()

  def addMFlag(self, flag):
    """Add a flag to be used during Objective C compilation.
    
    @param flag: The flag to add.
    @type flag: string
    """
    self.mFlags.append(flag)
    self._clearCache()

  def addMmFlag(self, flag):
    """Add a flag to be used during Objective C++ compilation.
    
    @param flag: The flag to add.
    @type flag: string
    """
    self.mmFlags.append(flag)
    self._clearCache()
    
  def addLibraryFlag(self, flag):
    """Add a flag to be used during library compilation.
    
    @param flag: The flag to add.
    @type flag: string
    """
    self.libraryFlags.append(flag)
    self._clearCache()
    
  def addModuleFlag(self, flag):
    """Add a flag to be used during linking of modules.
    
    @param flag: The flag to add.
    @type flag: string
    """
    self.moduleFlags.append(flag)
    self._clearCache()
    
  def addProgramFlag(self, flag):
    """Add a flag to be used during linking of programs.

    @param flag: The flag to add.
    @type flag: string
    """
    self.programFlags.append(flag)
    self._clearCache()

  def addResourceFlag(self, flag):
    """Add a flag to be used during resource compilation.
    
    @param flag: The flag to add.
    @type flag: string
    """
    self.resourceFlags.append(flag)
    self._clearCache()
    
  def addIncludePath(self, path):
    """Add an include path to the preprocessor search path.
    
    The newly added path will have search precedence over any
    existing paths.
    
    @param path: The path to add.
    @type path: string
    """
    self.includePaths.append(self.configuration.basePath(path))
    self._clearCache()
    
  def insertIncludePath(self, index, path):
    """Insert an include path into the preprocessor search paths.
    
    Include paths inserted at the back will have precedence over
    those inserted at the front.
    
    @param index: The index to insert at.
    @type index: int
    @param path: The path to add.
    @type path: string
    """
    self.includePaths.insert(index, self.configuration.basePath(path))
    self._clearCache()
        
  def getIncludePaths(self):
    """Get an iterator for include paths.
    
    The iterator will return include paths in the order they
    should be searched. 
    """
    return self.includePaths

  def addDefine(self, name, value=None):
    """Add a define to the preprocessor command-line.

    The newly added define will have precedence over any
    existing defines with the same name.
    
    @param name: The name of the define to set.
    @type name: string
    @param value: An optional value for the define.
    @type value: string or None
    """
    if value is None:
      self.defines.append(name)
    else:
      self.defines.append("%s=%s" % (name, value))
    self._clearCache()
    
  def insertDefine(self, index, name, value=None):
    """Insert a define into the preprocessor command-line.
    
    Defines inserted at the back will have precedence over those
    inserted at the front.
    
    @param index: The index to insert at.
    @type index: int
    @param name: The name of the define to set.
    @type name: string
    @param value: An optional value for the define.
    @type value: string or None
    """
    if value is None:
      self.defines.insert(index, name)
    else:
      self.defines.insert(index, "%s=%s" % (name, value))
    self._clearCache()

  def getDefines(self):
    """Get an iterator for preprocessor defines.
    
    The iterator will return defines in the order they should be
    set. Defines set later should have precedence over those set
    first.
    """
    return self.defines

  def addForcedInclude(self, path):
    """Add a file to be forcibly included on the command-line.

    The newly added forced include will be included after any
    previous forced includes.

    @param path: The path to the forced include file. This may need
    to be relative to a previously defined includePath. 
    @type path: string
    """
    self.forcedIncludes.append(self.configuration.basePath(path))
    self._clearCache()
  
  def insertForcedInclude(self, index, path):
    """Insert a forcibly included file into the command-line.
    
    Forced includes will be included in order. 
    
    @param index: The index to insert at.
    @type index: int
    @param path: The path to the forced include file. This may need
    to be relative to a previously defined includePath. 
    @type path: string
    """
    self.forcedIncludes.insert(index, self.configuration.basePath(path))
    self._clearCache()
    
  def getForcedIncludes(self):
    """Get an iterator for forced includes.
    
    The iterator will return forced includes in the order they
    should be included.
    """
    return self.forcedIncludes
  
  def addObjectPrerequisites(self, prerequisites):
    """Add a prerequisite that must complete before building object files.
    
    Use this for defining prerequisites such as generated headers that are
    required to be built before attempting to compile C/C++ source files.
    
    Cake is not able to determine such dependencies on generated headers
    automatically and so adding a prerequisite is required to ensure
    correct compilation order.
    
    @param prerequisites: A Task/FileTarget/AsyncResult or sequence of these.
    The object file will not be built before all of the tasks associated with
    these have completed successfully.
    """
    self.objectPrerequisites.append(prerequisites)
  
  def addLibrary(self, name):
    """Add a library to the list of libraries to link with.
    
    The newly added library will have search precedence over any
    existing libraries.

    @param name: Name/path of the library to link with.
    @type name: string
    """
    self.libraries.append(name)
    self._clearCache()

  def insertLibrary(self, index, name):
    """Insert a library into the list of libraries to link with.
    
    Libraries inserted at the back will have precedence over those
    inserted at the front. 
    
    @param index: The index to insert at.
    @type index: int
    @param name: Name/path of the library to link with.
    @type name: string
    """
    self.libraries.insert(index, name)
    self._clearCache()
    
  def getLibraries(self):
    """Get an iterator for libraries.
    
    The iterator will return libraries in the order they
    should be searched.
    """
    return self.libraries
  
  def addLibraryPath(self, path):
    """Add a path to the list of library search paths.
    
    The newly added path will have search precedence over any
    existing paths.
    
    @param path: The path to add.
    @type path: string
    """
    self.libraryPaths.append(self.configuration.basePath(path))
    self._clearCache()

  def insertLibraryPath(self, index, path):
    """Insert a path into the list of library search paths.
    
    Library paths inserted at the back will have precedence over
    those inserted at the front.
    
    @param index: The index to insert at.
    @type index: int
    @param path: The path to add.
    @type path: string
    """
    self.libraryPaths.insert(index, self.configuration.basePath(path))
    self._clearCache()
      
  def getLibraryPaths(self):
    """Get an iterator for library paths.
    
    The iterator will return library paths in the order they
    should be searched.
    """
    return self.libraryPaths

  def addModule(self, path):
    """Add a module to the list of modules to copy.
    
    @param path: Path of the module to copy.
    @type path: string
    """
    self.modules.append(self.configuration.basePath(path))
    self._clearCache()
    
  def copyModulesTo(self, targetDir, **kwargs):
    """Copy modules to the given target directory.
    
    The modules copied are those previously specified by the
    addModule() function.
    
    @param targetDir: The directory to copy modules to.
    @type targetDir: string

    @return: A list of FileTarget objects, one for each module being
    copied.
    @rtype: list of L{FileTarget}
    """
    compiler = self.clone()
    for k, v in kwargs.iteritems():
      setattr(compiler, k, v)
      
    return compiler._copyModulesTo(self.configuration.basePath(targetDir))

  def _copyModulesTo(self, targetDir):
    
    def doCopy(source, target):
      
      abspath = self.configuration.abspath
      engine = self.engine
      
      targetAbsPath = abspath(target)
      sourceAbsPath = abspath(source) 
      
      if engine.forceBuild:
        reasonToBuild = "rebuild has been forced"
      elif not cake.filesys.isFile(targetAbsPath):
        reasonToBuild = "it doesn't exist"
      elif engine.getTimestamp(sourceAbsPath) > engine.getTimestamp(targetAbsPath):
        reasonToBuild = "'%s' has been changed" % source
      else:
        # up-to-date
        return

      engine.logger.outputDebug(
        "reason",
        "Rebuilding '%s' because %s.\n" % (target, reasonToBuild),
        )
      engine.logger.outputInfo("Copying %s to %s\n" % (source, target))
      
      try:
        cake.filesys.makeDirs(cake.path.dirName(targetAbsPath))
        cake.filesys.copyFile(sourceAbsPath, targetAbsPath)
      except EnvironmentError, e:
        engine.raiseError("%s: %s\n" % (target, str(e)))

      engine.notifyFileChanged(targetAbsPath)
    
    @waitForAsyncResult
    def run(sources, targetDir):
      results = []
      
      for source in sources:
        sourcePath = getPath(source)
        targetPath = os.path.join(targetDir, os.path.basename(sourcePath))
        
        if self.enabled:  
          sourceTask = getTask(source)
          copyTask = self.engine.createTask(lambda s=sourcePath, t=targetPath: doCopy(s, t))
          copyTask.lazyStartAfter(sourceTask)
        else:
          copyTask = None

        results.append(FileTarget(path=targetPath, task=copyTask))

      Script.getCurrent().getDefaultTarget().addTargets(results)

      return results
    
    # TODO: Handle copying .manifest files if present for MSVC
    # built DLLs.

    return run(flatten(self.modules), targetDir)

  def pch(self, target, source, header, prerequisites=[],
          forceExtension=True, **kwargs):
    """Compile an individual header to a pch file.
    
    @param target: Path to the target pch file.
    @type target: string
    
    @param header: Path to the header as it would be included
    by other source files.
    @type header: string.

    @param prerequisites: An optional list of extra prerequisites that should
    complete building before building this pch.
    @type prerequisites: list of Task or FileTarget
    
    @param forceExtension: If true then the target path will have
    the default pch file extension appended if it doesn't already
    have it.
    @type forceExtension: bool
    
    @return: A PchTarget containing the path of the pch file
    that will be built and the task that will build it.
    @rtype: L{PchTarget}
    """
     
    # Take a snapshot of the build settings at this point and use that.
    compiler = self.clone()
    for k, v in kwargs.iteritems():
      setattr(compiler, k, v)
      
    basePath = self.configuration.basePath
    
    return compiler._pch(basePath(target), basePath(source), header, prerequisites, forceExtension)
  
  def pchMessage(self, target, source, header, cached=False):
    """Returns the message to display when compiling a precompiled header file.
    
    Override this function to display a different message when compiling
    a precompiled header file.
    
    @param target: Path of the target object file.
    @type target: string
    
    @param source: Path of the source file.
    @type source: string
    
    @param header: Path to the header as it would be included
    by other source files.
    @type header: string.
    
    @param cached: True if the target will be copied from the cache instead
    of being compiled.
    @type cached: bool
    
    @return: The message to display.
    @rtype: string    
    """
    if cached:
      return "Cached %s\n" % os.path.normpath(source)
    else:
      return "Compiling %s\n" % os.path.normpath(source)
    
  def _pch(self, target, source, header, prerequisites=[],
           forceExtension=True):
    
    @waitForAsyncResult
    def run(target, source, header, prerequisites):
      if forceExtension:
        target = cake.path.forceExtension(target, self.pchSuffix)
      
      if self.pchObjectSuffix is None:
        object = None
      else:
        object = cake.path.stripExtension(target) + self.pchObjectSuffix
      
      if self.enabled:
        tasks = getTasks(prerequisites + [source, header])
        pchTask = self.engine.createTask(
          lambda t=target, s=source, h=header, o=object, c=self:
            c.buildPch(t, getPath(s), h, o)
          )
        pchTask.lazyStartAfter(tasks, threadPool=self.engine.scriptThreadPool)
      else:
        pchTask = None
      
      pchTarget = PchTarget(
        path=target,
        task=pchTask,
        compiler=self,
        header=header,
        object=object,
        )
      currentScript = Script.getCurrent()
      currentScript.getDefaultTarget().addTarget(pchTarget)
      currentScript.getTarget(cake.path.baseName(target)).addTarget(pchTarget)
      currentScript.getTarget("pch").addTarget(pchTarget)
      return pchTarget
      
    allPrerequisites = flatten([
      prerequisites,
      self.objectPrerequisites,
      self._getObjectPrerequisiteTasks(),
      ])
      
    return run(target, source, header, allPrerequisites)

  def object(self, target, source, pch=None, prerequisites=[],
             forceExtension=True, **kwargs):
    """Compile an individual source to an object file.
    
    @param target: Path of the target object file.
    @type target: string
    
    @param source: Path of the source file.
    @type source: string or FileTarget.
    
    @param pch: A precompiled header file to use. This file can be built
    with the pch() function.
    @type pch: L{PchTarget}

    @param prerequisites: An optional list of extra prerequisites that should
    complete building before building this object.
    @type prerequisites: list of Task or FileTarget
    
    @param forceExtension: If true then the target path will have
    the default object file extension appended if it doesn't already
    have it.
    @type forceExtension: bool
    
    @return: A FileTarget containing the path of the object file
    that will be built and the task that will build it.
    @rtype: L{ObjectTarget}
    """
     
    # Take a snapshot of the build settings at this point and use that.
    compiler = self.clone()
    for k, v in kwargs.iteritems():
      setattr(compiler, k, v)

    basePath = self.configuration.basePath
      
    return compiler._object(basePath(target), basePath(source), pch, prerequisites, forceExtension)
  
  def objectMessage(self, target, source, pch=None, shared=False, cached=False):
    """Returns the message to display when compiling an object file.
    
    Override this function to display a different message when compiling
    an object file.
    
    @param target: Path of the target object file.
    @type target: string
    
    @param source: Path of the source file.
    @type source: string
    
    @param pch: Path of a precompiled header file to use or None.
    @type pch: string or None
    
    @param shared: True if this object file is being built for use in a
    shared library/module.
    @type shared: bool
    
    @param cached: True if the target will be copied from the cache instead
    of being compiled.
    @type cached: bool
    
    @return: The message to display.
    @rtype: string    
    """
    if cached:
      return "Cached %s\n" % os.path.normpath(source)
    else:
      return "Compiling %s\n" % os.path.normpath(source)
        
  def _object(self, target, source, pch=None, prerequisites=[],
              forceExtension=True, shared=False):
    
    @waitForAsyncResult
    def run(target, source, pch, prerequisites):
      if forceExtension:
        target = cake.path.forceExtension(target, self.objectSuffix)

      sourcePath = getPath(source)

      if self.enabled:
        tasks = getTasks((source, pch, prerequisites))
        objectTask = self.engine.createTask(
          lambda t=target, s=sourcePath, p=pch, h=shared, c=self:
            c.buildObject(t, s, p, h)
          )
        objectTask.lazyStartAfter(tasks, threadPool=self.engine.scriptThreadPool)
      else:
        objectTask = None
      
      objectTarget = ObjectTarget(
        path=target,
        task=objectTask,
        compiler=self,
        )
      currentScript = Script.getCurrent()
      currentScript.getDefaultTarget().addTarget(objectTarget)
      currentScript.getTarget("objects").addTarget(objectTarget)
      currentScript.getTarget(cake.path.baseName(target)).addTarget(objectTarget)
      currentScript.getTarget(cake.path.baseName(sourcePath)).addTarget(objectTarget)
      return objectTarget
      
    allPrerequisites = flatten([
      prerequisites,
      self.objectPrerequisites,
      self._getObjectPrerequisiteTasks(),
      ])
      
    return run(target, source, pch, allPrerequisites)
    
  @memoise
  def _getObjectPrerequisiteTasks(self):
    """Return a list of the tasks that are prerequisites for
    building an object file.
    """
    return getTasks(self.forcedIncludes)
    
  def objects(self, targetDir, sources, pch=None, prerequisites=[], **kwargs):
    """Build a collection of objects to a target directory.
    
    @param targetDir: Path to the target directory where the built objects
    will be placed.
    @type targetDir: string
    
    @param sources: A list of source files to compile to object files.
    @type sources: sequence of string or FileTarget objects
    
    @param pch: A precompiled header file to use. This file can be built
    with the pch() function.
    @type pch: L{PchTarget}

    @param prerequisites: An optional list of extra prerequisites that should
    complete building before building these objects.
    @type prerequisites: list of Task or FileTarget
    
    @return: A list of FileTarget objects, one for each object being
    built.
    """
    compiler = self.clone()
    for k, v in kwargs.iteritems():
      setattr(compiler, k, v)
    
    @waitForAsyncResult
    def run(targetDir, sources, prerequisites):
      results = []
      for source in sources:
        sourcePath = getPath(source)
        sourceName = cake.path.baseNameWithoutExtension(sourcePath)
        targetPath = cake.path.join(targetDir, sourceName)
        results.append(compiler._object(targetPath, source,
                                        pch=pch, prerequisites=prerequisites))
      return results

    basePath = self.configuration.basePath
    
    return run(basePath(targetDir), basePath(flatten(sources)), prerequisites)

  def sharedObjects(self, targetDir, sources, pch=None, prerequisites=[],
                    **kwargs):
    """Build a collection of objects used by a shared library/module to a target directory.

    @param targetDir: Path to the target directory where the built objects
    will be placed.
    @type targetDir: string

    @param sources: A list of source files to compile to object files.
    @type sources: sequence of string or FileTarget objects

    @param pch: A precompiled header file to use. This file can be built
    with the pch() function.
    @type pch: L{PchTarget}

    @param prerequisites: An optional list of extra prerequisites that should
    complete building before building these objects.
    @type prerequisites: list of Task or FileTarget
    
    @return: A list of FileTarget objects, one for each object being
    built.
    """
    compiler = self.clone()
    for k, v in kwargs.iteritems():
      setattr(compiler, k, v)

    @waitForAsyncResult
    def run(targetDir, sources, prerequisites):
      results = []
      for source in sources:
        sourcePath = getPath(source)
        sourceName = cake.path.baseNameWithoutExtension(sourcePath)
        targetPath = cake.path.join(targetDir, sourceName)
        results.append(compiler._object(
          targetPath,
          source,
          pch=pch,
          prerequisites=prerequisites,
          shared=True
          ))
      return results
    
    basePath = self.configuration.basePath
    
    return run(basePath(targetDir), basePath(sources), prerequisites)
    
  def library(self, target, sources, prerequisites=[], forceExtension=True, **kwargs):
    """Build a library from a collection of objects.
    
    @param target: Path of the library file to build.
    @type target: string
    
    @param sources: A list of object files to archive.
    @type sources: list of string or FileTarget
    
    @param prerequisites: An optional list of extra prerequisites that should
    complete building before building these objects.
    @type prerequisites: list of Task or FileTarget
     
    @param forceExtension: If True then the target path will have
    the default library extension appended to it if it not already
    present.
    
    @return: A FileTarget object representing the library that will
    be built and the task that will build it.
    @rtype: L{LibraryTarget}
    """

    # Take a snapshot of the current compiler settings
    compiler = self.clone()
    for k, v in kwargs.iteritems():
      setattr(compiler, k, v)

    basePath = self.configuration.basePath

    return compiler._library(
      basePath(target),
      basePath(sources),
      prerequisites,
      forceExtension
      )
    
  def libraryMessage(self, target, sources, cached=False):
    """Returns the message to display when compiling a library file.
    
    Override this function to display a different message when compiling
    a library file.
    
    @param target: Path of the target library file.
    @type target: string
    
    @param sources: Paths to the source files.
    @type sources: list(string)
    
    @param cached: True if the target has been copied from the cache instead
    of being compiled.
    @type cached: bool
    
    @return: The message to display.
    @rtype: string    
    """
    if cached:
      return "Cached %s\n" % os.path.normpath(target)
    else:
      return "Archiving %s\n" % os.path.normpath(target)
      
  def _library(self, target, sources, prerequisites=[], forceExtension=True):
    
    @waitForAsyncResult
    def run(target, sources, prerequisites):
      if forceExtension:
        prefix, suffix = self.libraryPrefix, self.librarySuffix
        target = cake.path.forcePrefixSuffix(target, prefix, suffix)
  
      if self.enabled:
        def build():
          paths = getLinkPaths(sources)
          self._setObjectsInLibrary(target, paths)
          self.buildLibrary(target, paths)
        
        tasks = getTasks(sources)
        tasks.extend(getTasks(prerequisites))
        libraryTask = self.engine.createTask(build)
        libraryTask.lazyStartAfter(tasks, threadPool=self.engine.scriptThreadPool)
      else:
        libraryTask = None
      
      libraryTarget = LibraryTarget(
        path=target,
        task=libraryTask,
        compiler=self,
        )
      currentScript = Script.getCurrent()
      currentScript.getDefaultTarget().addTarget(libraryTarget)
      currentScript.getTarget("libs").addTarget(libraryTarget)
      currentScript.getTarget(cake.path.baseName(target)).addTarget(libraryTarget)
      return libraryTarget

    return run(target, flatten(sources), flatten(prerequisites))
    
  def module(self, target, sources, importLibrary=None, installName=None, prerequisites=[], forceExtension=True, **kwargs):
    """Build a module/dynamic-library.
    
    Modules are executable code that can be dynamically loaded at
    runtime. On some platforms they are referred to as shared-libraries
    or dynamically-linked-libraries (DLLs).
    
    @param target: Path of the module file to build.
    @type target: string
    
    @param sources: A list of source objects/libraries to be linked
    into the module.
    @type sources: sequence of string/FileTarget

    @param importLibrary: Optional path to an import library that should be
    built. Programs can link against the import library to use the modules
    functions. 

    Related compiler options::
      GCC (MinGW only):  --out-implib
      MSVC: /IMPLIB
    @type importLibrary: string or None
    
    @param installName: Optional dyld install_name for a shared library.
    @type installName: string or None

    @param prerequisites: An optional list of extra prerequisites that should
    complete building before building these objects.
    @type prerequisites: list of Task or FileTarget
     
    @param forceExtension: If True then the target path will have
    the default module extension appended to it if it not already
    present.
    
    @return: A FileTarget object representing the module that will
    be built and the task that will build it.   
    @rtype: L{ModuleTarget}
    """
    
    # Take a snapshot of the current compiler settings
    compiler = self.clone()
    for k, v in kwargs.iteritems():
      setattr(compiler, k, v)

    basePath = self.configuration.basePath

    return compiler._module(
      basePath(target),
      basePath(sources),
      basePath(importLibrary),
      installName,
      prerequisites,
      forceExtension,
      )
    
  def moduleMessage(self, target, sources, cached=False):
    """Returns the message to display when compiling a module file.
    
    Override this function to display a different message when compiling
    a module file.
    
    @param target: Path of the target module file.
    @type target: string
    
    @param sources: Paths to the source files.
    @type sources: list(string)
    
    @param cached: True if the target has been copied from the cache instead
    of being compiled.
    @type cached: bool
    
    @return: The message to display.
    @rtype: string    
    """
    if cached:
      return "Cached %s\n" % os.path.normpath(target)
    else:
      return "Linking %s\n" % os.path.normpath(target)
      
  def _module(self, target, sources, importLibrary=None, installName=None, prerequisites=[], forceExtension=True):
    
    @waitForAsyncResult
    def run(target, sources, importLibrary, installName, prerequisites):
      if forceExtension:
        prefix, suffix = self.modulePrefixSuffixes[0]
        target = cake.path.forcePrefixSuffix(target, prefix, suffix)
        if importLibrary:
          prefix, suffix = self.libraryPrefix, self.librarySuffix
          importLibrary = cake.path.forcePrefixSuffix(
            importLibrary,
            prefix,
            suffix,
            )
        if installName:
          prefix, suffix = self.modulePrefixSuffixes[0]
          installName = cake.path.forcePrefixSuffix(
            installName,
            prefix,
            suffix,
            )
  
      if self.manifestSuffix is None:
        manifest = None
      else:
        manifest = target + self.manifestSuffix
  
      if self.enabled:
        def build():
          paths = getLinkPaths(sources)
          self.buildModule(target, paths, importLibrary, installName)
        
        tasks = getTasks(sources)
        tasks.extend(getTasks(prerequisites))
        tasks.extend(getTasks(self.getLibraries()))
        moduleTask = self.engine.createTask(build)
        moduleTask.lazyStartAfter(tasks, threadPool=self.engine.scriptThreadPool)
      else:
        moduleTask = None
     
      moduleTarget = ModuleTarget(
        path=target,
        task=moduleTask,
        compiler=self,
        library=importLibrary,
        manifest=manifest,
        )

      currentScript = Script.getCurrent()
      currentScript.getDefaultTarget().addTarget(moduleTarget)
      currentScript.getTarget(cake.path.baseName(target)).addTarget(moduleTarget)
      currentScript.getTarget("modules").addTarget(moduleTarget)
      if moduleTarget.library:
        currentScript.getTarget("libs").addTarget(moduleTarget.library)

      return moduleTarget

    return run(target, flatten(sources), importLibrary, installName, flatten(prerequisites))

  def program(self, target, sources, prerequisites=[], forceExtension=True, **kwargs):
    """Build an executable program.

    @param target: Path to the target executable.
    @type target: string
    
    @param sources: A list of source objects/libraries to be linked
    into the executable.
    @type sources: sequence of string/FileTarget
    
    @param prerequisites: An optional list of extra prerequisites that should
    complete building before building these objects.
    @type prerequisites: list of Task or FileTarget
    
    @param forceExtension: If True then target path will have the
    default executable extension appended if it doesn't already have
    it.
    
    @return: A FileTarget object representing the executable that will
    be built and the task that will build it.
    @rtype: L{ProgramTarget}
    
    """
    
    # Take a snapshot of the current compiler settings
    compiler = self.clone()
    for name, value in kwargs.iteritems():
      setattr(compiler, name, value)
  
    basePath = self.configuration.basePath
  
    return compiler._program(basePath(target), basePath(sources), prerequisites, forceExtension)
  
  def programMessage(self, target, sources, cached=False):
    """Returns the message to display when compiling a program file.
    
    Override this function to display a different message when compiling
    a program file.
    
    @param target: Path of the target program file.
    @type target: string
    
    @param sources: Paths to the source files.
    @type sources: list(string)
    
    @param cached: True if the target has been copied from the cache instead
    of being compiled.
    @type cached: bool
    
    @return: The message to display.
    @rtype: string    
    """
    if cached:
      return "Cached %s\n" % os.path.normpath(target)
    else:
      return "Linking %s\n" % os.path.normpath(target)
    
  def _program(self, target, sources, prerequisites=[], forceExtension=True, **kwargs):

    @waitForAsyncResult
    def run(target, sources, prerequisites, libraries):
    
      if forceExtension:
        target = cake.path.forceExtension(target, self.programSuffix)
    
      if self.manifestSuffix is None:
        manifest = None
      else:
        manifest = target + self.manifestSuffix
    
      if self.enabled:
        def build():
          paths = getLinkPaths(sources)
          self.buildProgram(target, paths)

        tasks = getTasks(sources)
        tasks.extend(getTasks(prerequisites))
        tasks.extend(getTasks(libraries))
        programTask = self.engine.createTask(build)
        programTask.lazyStartAfter(tasks, threadPool=self.engine.scriptThreadPool)
      else:
        programTask = None
    
      programTarget = ProgramTarget(
        path=target,
        task=programTask,
        compiler=self,
        manifest=manifest,
        )

      currentScript = Script.getCurrent()
      currentScript.getDefaultTarget().addTarget(programTarget)
      currentScript.getTarget("programs").addTarget(programTarget)
      currentScript.getTarget(cake.path.baseName(target)).addTarget(programTarget)

      return programTarget
      
    return run(
      target,
      flatten(sources),
      flatten(prerequisites),
      flatten(self.getLibraries()))

  def resource(self, target, source, prerequisites=[], forceExtension=True, **kwargs):
    """Build a resource from a collection of sources.
    
    @param target: Path of the resource file to build.
    @type target: string
    
    @param source: Path of the source file to compile.
    @type source: string

    @param prerequisites: An optional list of extra prerequisites that should
    complete building before building these objects.
    @type prerequisites: list of Task or FileTarget
    
    @param forceExtension: If True then the target path will have
    the default resource extension appended to it if it not already
    present.
    
    @return: A FileTarget object representing the resource that will
    be built and the task that will build it.
    @rtype: L{ResourceTarget}
    """

    # Take a snapshot of the current compiler settings
    compiler = self.clone()
    for k, v in kwargs.iteritems():
      setattr(compiler, k, v)

    basePath = self.configuration.basePath
  
    return compiler._resource(basePath(target), basePath(source), prerequisites, forceExtension)
  
  def resourceMessage(self, target, source, cached=False):
    """Returns the message to display when compiling a resource file.
    
    Override this function to display a different message when compiling
    a resource file.
    
    @param target: Path of the target resource file.
    @type target: string
    
    @param source: Path of the source file.
    @type source: string
    
    @param cached: True if the target has been copied from the cache instead
    of being compiled.
    @type cached: bool
    
    @return: The message to display.
    @rtype: string    
    """
    if cached:
      return "Cached %s\n" % os.path.normpath(source)
    else:
      return "Compiling %s\n" % os.path.normpath(source)
    
  def _resource(self, target, source, prerequisites=[], forceExtension=True):
    
    @waitForAsyncResult
    def run(target, source, prerequisites):
      if forceExtension:
        target = cake.path.forceExtension(target, self.resourceSuffix)
  
      if self.enabled:
        def build():
          path = getPath(source)
          self.buildResource(target, path)
  
        tasks = getTasks([source])
        tasks.extend(getTasks(prerequisites))
        resourceTask = self.engine.createTask(build)
        resourceTask.lazyStartAfter(tasks, threadPool=self.engine.scriptThreadPool)
      else:
        resourceTask = None
      
      resourceTarget = ResourceTarget(
        path=target,
        task=resourceTask,
        compiler=self,
        )

      currentScript = Script.getCurrent()
      currentScript.getDefaultTarget().addTarget(resourceTarget)
      currentScript.getTarget(cake.path.baseName(target)).addTarget(resourceTarget)

      return resourceTarget
      
    return run(target, source, flatten(prerequisites))

  def resources(self, targetDir, sources, prerequisites=[], **kwargs):
    """Build a collection of resources to a target directory.
    
    @param targetDir: Path to the target directory where the built resources
    will be placed.
    @type targetDir: string
    
    @param sources: A list of source files to compile to resource files.
    @type sources: sequence of string or FileTarget objects
    
    @param prerequisites: An optional list of extra prerequisites that should
    complete building before building these objects.
    @type prerequisites: list of Task or FileTarget
    
    @return: A list of FileTarget objects, one for each resource being
    built.
    """
    compiler = self.clone()
    for k, v in kwargs.iteritems():
      setattr(compiler, k, v)
    
    @waitForAsyncResult
    def run(targetDir, sources, prerequisites):
      results = []
      for source in sources:
        sourcePath = getPath(source)
        sourceName = cake.path.baseNameWithoutExtension(sourcePath)
        targetPath = cake.path.join(targetDir, sourceName)
        results.append(compiler._resource(
          targetPath,
          source,
          prerequisites,
          ))
      return results

    basePath = self.configuration.basePath

    return run(basePath(targetDir), basePath(sources), prerequisites)

  ###########################
  # Internal methods not part of public API
  
  def _generateDependencyFile(self, target):
    if self.keepDependencyFile:
      depPath = cake.path.stripExtension(target) + '.d'
      depPath = self.configuration.abspath(depPath)
    else:
      fd, depPath = tempfile.mkstemp(prefix='CakeGccDep')
      os.close(fd)
    return depPath

  def _getObjectsInLibrary(self, path):
    """Get a list of the paths of object files in the specified library.
    
    @param path: Path of the library previously built by a call to library().
    
    @return: A tuple of the paths of objects in the library.
    """
    path = os.path.normcase(os.path.normpath(path))
    libraryObjects = self.__libraryObjects.get(self.configuration, None)
    if libraryObjects:
      return libraryObjects.get(path, None)
    else:
      return None
        
  @memoise
  def _getProcessEnv(self):
    temp = os.environ.get('TMP', os.environ.get('TEMP', os.getcwd()))
    env = {
      'COMSPEC' : os.environ.get('COMSPEC', ''),
      'PATH' : '.',
      'PATHEXT' : ".COM;.EXE;.BAT;.CMD",
      'SYSTEMROOT' : os.environ.get('SYSTEMROOT', ''),
      'TEMP' : temp,
      'TMP' : temp,
      'TMPDIR' : temp,
      }
    
    if self.__binPaths is not None:
      env['PATH'] = os.path.pathsep.join(
        [env['PATH']] + self.__binPaths
        )
    
    if env['SYSTEMROOT']:
      env['PATH'] = os.path.pathsep.join([
        env['PATH'],
        os.path.join(env['SYSTEMROOT'], 'System32'),
        env['SYSTEMROOT'],
        ])
      
    return env

  def _outputStderr(self, text):
    text = text.replace("\r\n", "\n")
    self.engine.logger.outputError(text)
        
  def _outputStdout(self, text):
    # Output stdout to stderr as well. Some compilers will output errors
    # to stdout, and all unexpected output should be treated as an error,
    # or handled/output by client code.
    # An example of a compiler outputting errors to stdout is Msvc's link
    # error, "LINK : fatal error LNK1104: cannot open file '<filename>'".
    text = text.replace("\r\n", "\n")
    self.engine.logger.outputError(text)
      
  def _resolveObjects(self):
    """Resolve the list of library names to object file paths.
    
    @return: A tuple containing a list of paths to resolved objects,
    followed by a list of unresolved libraries.
    @rtype: tuple of (list of string, list of string)
    """
    objects = []
    libraries = getLibraryPaths(self.getLibraries())

    if not self.linkObjectsInLibrary:
      return objects, libraries

    paths = self._scanForLibraries(libraries, True)
    newLibraries = []
      
    for i, path in enumerate(paths):
      if path is not None:
        objectsInLib = self._getObjectsInLibrary(path)
        if objectsInLib is not None:
          objects.extend(objectsInLib)
          continue
      newLibraries.append(libraries[i])
        
    return objects, newLibraries
  
  def _runProcess(
    self,
    args,
    target=None,
    processStdout=None,
    processStderr=None,
    processExitCode=None,
    allowResponseFile=True,
    ):

    if target is not None:
      absTarget = self.configuration.abspath(target)
      try:
        cake.filesys.makeDirs(cake.path.dirName(absTarget))
      except Exception, e:
        msg = "cake: Error creating target directory %s: %s\n" % (
          cake.path.dirName(target), str(e))
        self.engine.raiseError(msg, targets=[target])

    stdout = None
    stderr = None
    argsPath = None
    try:
      stdout = tempfile.TemporaryFile(mode="w+t")
      stderr = tempfile.TemporaryFile(mode="w+t")
      
      if allowResponseFile and self.useResponseFile:
        argsTemp, argsPath = tempfile.mkstemp(text=True)
        argsFileString = "\n".join(_escapeArgs(args[1:]))
        argsFile = os.fdopen(argsTemp, "wt")
        argsFile.write(argsFileString)
        argsFile.close()
        args = [args[0], '@' + argsPath]
      
      argsString = " ".join(_escapeArgs(args))
      
      debugString = "run: %s\n" % argsString
      if argsPath is not None:
        debugString += "contents of %s: %s\n" % (argsPath, argsFileString)
        
      self.engine.logger.outputDebug(
        "run",
        debugString,
        )

      isTiming = self.engine.logger.debugEnabled("time")
      if isTiming:
        start = datetime.datetime.utcnow()
        
      if cake.system.isWindows():
        # Use shell=False to avoid command line length limits.
        executable = self.configuration.abspath(args[0])
        shell = False
      else:
        # Use shell=True to allow arguments to be escaped exactly as they
        # would be on the command line.
        executable = None
        shell = True
      
      try:
        p = subprocess.Popen(
          args=argsString,
          executable=executable,
          shell=shell,
          cwd=self.configuration.baseDir,
          env=self._getProcessEnv(),
          stdin=subprocess.PIPE,
          stdout=stdout,
          stderr=stderr,
          )
      except EnvironmentError, e:
        self.engine.raiseError(
          "cake: failed to launch %s: %s\n" % (args[0], str(e)),
          targets=[target],
          )
      p.stdin.close()
  
      exitCode = p.wait()
  
      if isTiming:
        elapsed = (datetime.datetime.utcnow() - start)
        totalSeconds = _totalSeconds(elapsed)
        self.engine.logger.outputDebug(
          "time",
          "time: %.3fs %s\n" % (totalSeconds, debugString[5:]),
          )
  
      stdout.seek(0)
      stderr.seek(0)
  
      stdoutText = stdout.read() 
      stderrText = stderr.read()
    finally:
      if stdout is not None:
        stdout.close()
      if stderr is not None:
        stderr.close()
      if argsPath is not None:
        os.remove(argsPath)
    
    if stdoutText:
      if processStdout is not None:
        processStdout(stdoutText)
      else:
        self._outputStdout(stdoutText)
    
    if stderrText:
      if processStderr is not None:
        processStderr(stderrText)
      else:
        self._outputStderr(stderrText)
      
    if processExitCode is not None:
      processExitCode(exitCode)
    elif exitCode != 0:
      self.engine.raiseError(
        "%s: failed with exit code %i\n" % (args[0], exitCode),
        targets=[target],
        )
      
    # TODO: Return DLL's/EXE's used by gcc.exe or MSVC as well.
    return [args[0]]
  
  def _scanDependencyFile(self, depPath, target):
    self.engine.logger.outputDebug(
      "scan",
      "scan: %s\n" % depPath,
      )
        
    dependencies = parseDependencyFile(
        depPath,
        cake.path.extension(target),
        )
    
    if not self.keepDependencyFile:
      # Sometimes file removal will fail, perhaps because the compiler
      # or a file watcher has the file open. Because it's a temp file
      # this is OK, just let the system delete it later.
      try:
        os.remove(depPath)
      except Exception:
        self.engine.logger.outputDebug(
          "scan",
          "Unable to remove dependency file: %s\n" % depPath,
          )
      
    return dependencies

  def _scanForLibraries(self, libraries, flagMissing=False):
    paths = []
    for library in libraries:
      fileNames = [library]

      libraryExtension = os.path.normcase(cake.path.extension(library))
      for prefix, suffix in self.libraryPrefixSuffixes:
        if libraryExtension != os.path.normcase(suffix):
          fileNames.append(cake.path.addPrefix(library, prefix) + suffix)

      # Add [""] so we search for the full path first
      libraryPaths = itertools.chain([""], self.getLibraryPaths()) 
      for candidate in cake.path.join(libraryPaths, fileNames):
        absCandidate = self.configuration.abspath(candidate)
        if cake.filesys.isFile(absCandidate):
          paths.append(candidate)
          break
      else:
        if flagMissing:
          paths.append(None)
        else:
          self.engine.logger.outputDebug(
            "scan",
            "scan: Ignoring missing library '" + library + "'\n",
            )
    return paths
  
  def _setObjectsInLibrary(self, path, objectPaths):
    """Set the list of paths of object files in the specified library.
    
    @param path: Path of the library previously built by a call to library().
    @type path: string
    
    @param objectPaths: A list of the objects built by a call to library().
    @type objectPaths: list of strings
    """
    path = os.path.normcase(os.path.normpath(path))
    libraryObjects = self.__libraryObjects.setdefault(self.configuration, {})
    libraryObjects[path] = tuple(objectPaths)
  
  def buildPch(self, target, source, header, object):
    compile, args, _ = self.getPchCommands(
      target,
      source,
      header,
      object,
      )
    
    # Check if the target needs building
    _, reasonToBuild = self.configuration.checkDependencyInfo(target, args)
    if not reasonToBuild:
      return # Target is up to date
    self.engine.logger.outputDebug(
      "reason",
      "Rebuilding '" + target + "' because " + reasonToBuild + ".\n",
      )

    targets = [target]
    if object is not None:
      targets.append(object)

    def command():
      message = self.pchMessage(target, source, header=header, cached=False)
      self.engine.logger.outputInfo(message)
      return compile()

    compileTask = self.engine.createTask(command)
    compileTask.parent.completeAfter(compileTask)
    compileTask.start(immediate=True)

    def storeDependencyInfo():
      abspath = self.configuration.abspath
      normpath = os.path.normpath
      dependencies = [
          normpath(abspath(p))
          for p in compileTask.result
          ]
      newDependencyInfo = self.configuration.createDependencyInfo(
        targets=[target],
        args=args,
        dependencies=dependencies,
        calculateDigests=False,
        )
      self.configuration.storeDependencyInfo(newDependencyInfo)
        
    storeDependencyTask = self.engine.createTask(storeDependencyInfo)
    storeDependencyTask.parent.completeAfter(storeDependencyTask)
    storeDependencyTask.startAfter(compileTask, immediate=True)

  def buildObject(self, target, source, pch, shared):
    """Perform the actual build of an object.
    
    @param target: Path of the target object file.
    @type target: string
    
    @param source: Path of the source file.
    @type source: string
    """
    compile, args, canBeCached = self.getObjectCommands(
      target,
      source,
      pch,
      shared
      )

    configuration = self.configuration
    
    # Check if the target needs building
    oldDependencyInfo, reasonToBuild = configuration.checkDependencyInfo(target, args)
    if reasonToBuild is None:
      return # Target is up to date
    self.engine.logger.outputDebug(
      "reason",
      "Rebuilding '" + target + "' because " + reasonToBuild + ".\n",
      )

    useCacheForThisObject = canBeCached and self.objectCachePath is not None
    cacheDepMagic = "CKCH" 
    
    if useCacheForThisObject:
      #######################
      # USING OBJECT CACHE
      #######################
      
      # Prime the file digest cache from previous run so we don't have
      # to recalculate file digests for files that haven't changed.
      if oldDependencyInfo is not None:
        configuration.primeFileDigestCache(oldDependencyInfo)
      
      # We either need to make all paths that form the cache digest relative
      # to the workspace root or all of them absolute.
      targetDigestPath = configuration.abspath(target)
      if self.objectCacheWorkspaceRoot is not None:
        workspaceRoot = configuration.abspath(self.objectCacheWorkspaceRoot)
        workspaceRoot = os.path.normcase(workspaceRoot)
        targetDigestPathNorm = os.path.normcase(targetDigestPath)
        if cake.path.commonPath(targetDigestPathNorm, workspaceRoot) == workspaceRoot:
          targetDigestPath = targetDigestPath[len(workspaceRoot)+1:]
          
      # Find the directory that will contain all cached dependency
      # entries for this particular target object file.
      targetDigest = cake.hash.sha1(targetDigestPath.encode("utf8")).digest()
      targetDigestStr = cake.hash.hexlify(targetDigest)
      targetCacheDir = cake.path.join(
        self.objectCachePath,
        targetDigestStr[0],
        targetDigestStr[1],
        targetDigestStr
        )
      targetCacheDir = configuration.abspath(targetCacheDir)
      
      # Find all entries in the directory
      entries = set()
      
      # If doing a force build, pretend the cache is empty
      if not self.engine.forceBuild:
        try:
          entries.update(os.listdir(targetCacheDir))
        except EnvironmentError:
          # Target cache dir doesn't exist, treat as if no entries
          pass
      
      hexChars = "0123456789abcdefABCDEF"
      
      # Try to find the dependency files
      for entry in entries:
        # Skip any entry that's not a SHA-1 hash
        if len(entry) != 40:
          continue
        skip = False
        for c in entry:
          if c not in hexChars:
            skip = True
            break
        if skip:
          continue

        cacheDepPath = cake.path.join(targetCacheDir, entry)
        
        try:
          cacheDepContents = cake.filesys.readFile(cacheDepPath)
        except EnvironmentError:
          continue
        
        # Check for the correct signature to make sure the file isn't corrupt
        cacheDepMagicLen = len(cacheDepMagic)
        cacheDepSignature = cacheDepContents[-cacheDepMagicLen:]
        cacheDepContents = cacheDepContents[:-cacheDepMagicLen]
        
        if cacheDepSignature != cacheDepMagic:
          # Invalid signature
          continue
        
        try:
          candidateDependencies = pickle.loads(cacheDepContents)
        except Exception:
          # Invalid dependency file for this entry
          continue
        
        if not isinstance(candidateDependencies, list):
          # Data format change
          continue
        
        try:
          newDependencyInfo = configuration.createDependencyInfo(
            targets=[target],
            args=args,
            dependencies=candidateDependencies,
            )
        except EnvironmentError:
          # One of the dependencies didn't exist
          continue
        
        # Check if the state of our files matches that of a cached object file.
        cachedObjectDigest = configuration.calculateDigest(newDependencyInfo)
        cachedObjectDigestStr = cake.hash.hexlify(cachedObjectDigest)
        cachedObjectPath = cake.path.join(
          self.objectCachePath,
          cachedObjectDigestStr[0],
          cachedObjectDigestStr[1],
          cachedObjectDigestStr
          )
        cachedObjectPath = configuration.abspath(cachedObjectPath)
        if cake.filesys.isFile(cachedObjectPath):
          message = self.objectMessage(target, source, pch=getPath(pch), shared=shared, cached=True)
          self.engine.logger.outputInfo(message)
          try:
            cake.zipping.decompressFile(cachedObjectPath, configuration.abspath(target))
          except EnvironmentError:
            continue # Invalid cache file
          configuration.storeDependencyInfo(newDependencyInfo)
          # Successfully restored object file and saved new dependency info file.
          return

    # Else, if we get here we didn't find the object in the cache so we need
    # to actually execute the build.
    def command():
      message = self.objectMessage(target, source, pch=getPath(pch), shared=shared, cached=False)
      self.engine.logger.outputInfo(message)
      return compile()
    
    def storeDependencyInfoAndCache():
      # Since we are sharing this object in the object cache we need to
      # make any paths in this workspace relative to the current workspace.
      abspath = configuration.abspath
      normpath = os.path.normpath
      dependencies = []
      if self.objectCacheWorkspaceRoot is None:
        dependencies = [
          normpath(abspath(p))
          for p in compileTask.result
          ]
      else:
        workspaceRoot = os.path.normcase(
          configuration.abspath(self.objectCacheWorkspaceRoot)
          ) + os.path.sep
        workspaceRootLen = len(workspaceRoot)
        for path in compileTask.result:
          path = normpath(abspath(path))
          pathNorm = os.path.normcase(path)
          if pathNorm.startswith(workspaceRoot):
            path = path[workspaceRootLen:]
          dependencies.append(path)
      
      newDependencyInfo = configuration.createDependencyInfo(
        targets=[target],
        args=args,
        dependencies=dependencies,
        calculateDigests=useCacheForThisObject,
        )
      configuration.storeDependencyInfo(newDependencyInfo)

      # Finally update the cache if necessary
      if useCacheForThisObject:
        try:
          objectDigest = configuration.calculateDigest(newDependencyInfo)
          objectDigestStr = cake.hash.hexlify(objectDigest)
          
          dependencyDigest = cake.hash.sha1()
          for dep in dependencies:
            dependencyDigest.update(dep.encode("utf8"))
          dependencyDigest = dependencyDigest.digest()
          dependencyDigestStr = cake.hash.hexlify(dependencyDigest)
          
          cacheDepPath = cake.path.join(
            targetCacheDir,
            dependencyDigestStr
            )
          cacheObjectPath = cake.path.join(
            self.objectCachePath,
            objectDigestStr[0],
            objectDigestStr[1],
            objectDigestStr,
            )
          cacheObjectPath = configuration.abspath(cacheObjectPath)

          # Copy the object file first, then the dependency file
          # so that other processes won't find the dependency until
          # the object file is ready.
          cake.zipping.compressFile(configuration.abspath(target), cacheObjectPath)
          
          if not cake.filesys.isFile(cacheDepPath):
            dependencyString = pickle.dumps(dependencies, pickle.HIGHEST_PROTOCOL)       
            cake.filesys.writeFile(cacheDepPath, dependencyString + cacheDepMagic)
            
        except EnvironmentError:
          # Don't worry if we can't put the object in the cache
          # The build shouldn't fail.
          pass
    
    compileTask = self.engine.createTask(command)
    compileTask.parent.completeAfter(compileTask)
    compileTask.start(immediate=True)

    storeDependencyTask = self.engine.createTask(storeDependencyInfoAndCache)
    storeDependencyTask.parent.completeAfter(storeDependencyTask)
    storeDependencyTask.startAfter(compileTask, immediate=True)
  
  def getPchCommands(self, target, source, header, object):
    """Get the command-lines for compiling a precompiled header.
    
    @return: A (compile, args, canCache) tuple where 'compile' is a function that
    takes no arguments returns a task that completes with the list of paths of
    dependencies when the compilation succeeds. 'args' is a value that indicates
    the parameters of the command, if the args changes then the target will
    need to be rebuilt; typically args includes the compiler's command-line.
    'canCache' is a boolean value that indicates whether the built object
    file can be safely cached or not.
    """
    self.engine.raiseError("Don't know how to compile %s\n" % source, targets=[target])

  def getObjectCommands(self, target, source, pch, shared):
    """Get the command-lines for compiling a source to a target.
    
    @return: A (compile, args, canCache) tuple where 'compile' is a function that
    takes no arguments returns a task that completes with the list of paths of
    dependencies when the compilation succeeds. 'args' is a value that indicates
    the parameters of the command, if the args changes then the target will
    need to be rebuilt; typically args includes the compiler's command-line.
    'canCache' is a boolean value that indicates whether the built object
    file can be safely cached or not.
    """
    self.engine.raiseError("Don't know how to compile %s\n" % source, targets=[target])
  
  def buildLibrary(self, target, sources):
    """Perform the actual build of a library.
    
    @param target: Path of the target library file.
    @type target: string
    
    @param sources: List of source object files.
    @type sources: list of string
    
    @param configuration: The Configuration object to use for dependency checking
    etc.
    """

    archive, scan = self.getLibraryCommand(target, sources)
    
    args = repr(archive)
    
    # Check if the target needs building
    _, reasonToBuild = self.configuration.checkDependencyInfo(target, args)
    if not reasonToBuild:
      return # Target is up to date
    self.engine.logger.outputDebug(
      "reason",
      "Rebuilding '" + target + "' because " + reasonToBuild + ".\n",
      )

    def command():
      message = self.libraryMessage(target, sources, cached=False)
      self.engine.logger.outputInfo(message)
      
      archive()
      
      targets, dependencies = scan()
      
      newDependencyInfo = self.configuration.createDependencyInfo(
        targets=targets,
        args=args,
        dependencies=dependencies,
        )
      
      self.configuration.storeDependencyInfo(newDependencyInfo)

    archiveTask = self.engine.createTask(command)
    archiveTask.parent.completeAfter(archiveTask)
    archiveTask.start(immediate=True)
  
  def getLibraryCommand(self, target, sources):
    """Get the command for constructing a library.
    
    @return: A tuple (build, scan) where build is the function to call to
    build the library, scan is a function that when called returns a
    (targets, dependencies) tuple. 
    """
    self.engine.raiseError("Don't know how to archive %s\n" % target, targets=[target])
  
  def buildModule(self, target, sources, importLibrary, installName):
    """Perform the actual build of a module.
    """
    link, scan = self.getModuleCommands(target, sources, importLibrary, installName)

    args = [repr(link), repr(scan)]
    
    # Check if the target needs building
    _, reasonToBuild = self.configuration.checkDependencyInfo(target, args)
    if not reasonToBuild:
      return # Target is up to date
    self.engine.logger.outputDebug(
      "reason",
      "Rebuilding '" + target + "' because " + reasonToBuild + ".\n",
      )

    def command():
      message = self.moduleMessage(target, sources, cached=False)
      self.engine.logger.outputInfo(message)
      
      link()
    
      targets, dependencies = scan()
      
      newDependencyInfo = self.configuration.createDependencyInfo(
        targets=targets,
        args=args,
        dependencies=dependencies,
        )
      
      self.configuration.storeDependencyInfo(newDependencyInfo)
  
    moduleTask = self.engine.createTask(command)
    moduleTask.parent.completeAfter(moduleTask)
    moduleTask.start(immediate=True)
  
  def getModuleCommands(self, target, sources, importLibrary, installName):
    """Get the commands for linking a module.
    
    @return: A tuple (link, scan) representing the commands that perform
    the link and scan for dependencies respectively. The scan command
    returns a tuple of (targets, dependencies). 
    """
    self.engine.raiseError("Don't know how to link %s\n" % target, targets=[target])
  
  def buildProgram(self, target, sources):
    """Perform the actual build of a module.
    
    @param target: Path of the target module file.
    @type target: string
    
    @param sources: Paths of the source object files and
    libraries to link.
    @type sources: list of string
    
    @param configuration: The Configuration object to use for dependency checking
    etc.
    """

    link, scan = self.getProgramCommands(target, sources)

    args = [repr(link), repr(scan)]
    
    # Check if the target needs building
    _, reasonToBuild = self.configuration.checkDependencyInfo(target, args)
    if not reasonToBuild:
      return # Target is up to date
    self.engine.logger.outputDebug(
      "reason",
      "Rebuilding '" + target + "' because " + reasonToBuild + ".\n",
      )

    def command():
      message = self.programMessage(target, sources, cached=False)
      self.engine.logger.outputInfo(message)
          
      link()
    
      targets, dependencies = scan()
      
      newDependencyInfo = self.configuration.createDependencyInfo(
        targets=targets,
        args=args,
        dependencies=dependencies,
        )
      
      self.configuration.storeDependencyInfo(newDependencyInfo)

    programTask = self.engine.createTask(command)
    programTask.parent.completeAfter(programTask)
    programTask.start(immediate=True)

  def getProgramCommands(self, target, sources):
    """Get the commands for linking a program.
    
    @param target: path to the target file
    @type target: string
    
    @param sources: list of the object/library file paths to link into the
    program.
    @type sources: list of string
    
    @return: A tuple (link, scan) representing the commands that perform
    the link and scan for dependencies respectively. The scan command
    returns the tuple (targets, dependencies). 
    """
    self.engine.raiseError("Don't know how to link %s\n" % target, targets=[target])
    
  def buildResource(self, target, source):
    """Perform the actual build of a resource.
    
    @param target: Path of the target resource file.
    @type target: string
    
    @param source: Path of the source file.
    @type source: string
    """

    compile, scan = self.getResourceCommand(target, source)
    
    args = repr(compile)
    
    # Check if the target needs building
    _, reasonToBuild = self.configuration.checkDependencyInfo(target, args)
    if not reasonToBuild:
      return # Target is up to date
    self.engine.logger.outputDebug(
      "reason",
      "Rebuilding '" + target + "' because " + reasonToBuild + ".\n",
      )

    def command():
      message = self.resourceMessage(target, source, cached=False)
      self.engine.logger.outputInfo(message)
      
      compile()
      
      targets, dependencies = scan()
      
      newDependencyInfo = self.configuration.createDependencyInfo(
        targets=targets,
        args=args,
        dependencies=dependencies,
        )
      
      self.configuration.storeDependencyInfo(newDependencyInfo)

    resourceTask = self.engine.createTask(command)
    resourceTask.parent.completeAfter(resourceTask)
    resourceTask.start(immediate=True)
  
  def getResourceCommand(self, target, sources):
    """Get the command for constructing a resource.
    
    @return: A tuple (build, scan) where build is the function to call to
    build the resource, scan is a function that when called returns a
    (targets, dependencies) tuple. 
    """
    self.engine.raiseError("Don't know how to compile %s\n" % target, targets=[target])
