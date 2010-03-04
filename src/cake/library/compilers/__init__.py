"""Base Class and Utilities for C/C++ Compiler Tools.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

__all__ = ["Compiler"]

import weakref
import os.path

import cake.path
import cake.filesys
from cake.engine import Script, DependencyInfo, FileInfo, BuildError
from cake.library import Tool, FileTarget, getPathsAndTasks, getPathAndTask
from cake.task import Task

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

class Compiler(Tool):
  """Base class for C/C++ compiler tools.
  
  @ivar debugSymbols: If true then the compiler will output debug symbols.
  @type debugSymbols: boolean
  """
  
  NO_OPTIMISATION = 0
  PARTIAL_OPTIMISATION = 1
  FULL_OPTIMISATION = 2

  # Map of engine to map of library path to list of object paths
  __libraryObjects = weakref.WeakKeyDictionary()

  ###
  # Default settings
  ###
  
  debugSymbols = False
  optimisation = NO_OPTIMISATION
  
  enableRtti = True
  enableExceptions = True
  
  warningLevel = None
  warningsAsErrors = False
  
  objectSuffix = '.o'
  libraryPrefixSuffixes = [('lib', '.a')]
  moduleSuffix = '.so'
  programSuffix = ''
  
  linkObjectsInLibrary = False
  outputMapFile = False
  useIncrementalLinking = False
  useFunctionLevelLinking = False
  stackSize = None
  heapSize = None

  linkerScript = None
    
  objectCachePath = None

  language = None
 
  # This is defined here so that .cake scripts don't have to
  # check if the compiler is msvc before setting it. Compilers
  # that don't use them can just ignore them. 
  pdbFile = None
  strippedPdbFile = None
  subSystem = None
  importLibrary = None
  embedManifest = False
  useSse = False
  
  def __init__(self):
    super(Compiler, self).__init__()
    self.includePaths = []
    self.defines = []
    self.forceIncludes = []
    self.libraryScripts = []
    self.libraryPaths = []
    self.libraries = []

  @classmethod
  def _getObjectsInLibrary(cls, engine, path):
    """Get a list of the paths of object files in the specified library.
    
    @param engine: The Engine that is looking up the results.
    @type engine: cake.engine.Engine
    
    @param path: Path of the library previously built by a call to library().
    
    @return: A tuple of the paths of objects in the library.
    """
    path = os.path.normcase(os.path.normpath(path))
    libraryObjects = cls.__libraryObjects.get(engine, None)
    if libraryObjects:
      return libraryObjects.get(path, None)
    else:
      return None

  @classmethod
  def _setObjectsInLibrary(cls, engine, path, objectPaths):
    """Set the list of paths of object files in the specified library.
    
    @param engine: The Engine that is looking up the results.
    @type engine: cake.engine.Engine
    
    @param path: Path of the library previously built by a call to library().
    @type path: string
    
    @param objectPaths: A list of the objects built by a call to library().
    @type objectPaths: list of strings
    """
    path = os.path.normcase(os.path.normpath(path))
    libraryObjects = cls.__libraryObjects.setdefault(engine, {})
    libraryObjects[path] = tuple(objectPaths)

  def addIncludePath(self, path):
    """Add an include path to the preprocessor search path.
    
    Include paths added later in the list are searched earlier
    by the preprocessor.
    """
    self.includePaths.append(path)
    self._clearCache()
    
  def addDefine(self, define, value=None):
    """Add a define to the preprocessor command-line.
    """
    if value is None:
      self.defines.append(define)
    else:
      self.defines.append("{0}={1}".format(define, value))
    self._clearCache()
    
  def addForceInclude(self, path):
    """Add a file to be forcibly included on the command-line.
    """
    self.forceIncludes.append(path)
    self._clearCache()
    
  def addLibrary(self, name):
    """Add a library to the list of libraries to link with.
    
    @param name: Name/path of the library to link with.
    """
    self.libraries.append(name)
    self._clearCache()

  def addLibraryPath(self, path):
    """Add a path to the library search path.
    """
    self.libraryPaths.append(path)
    self._clearCache()
    
  def addLibraryScript(self, path):
    """Add a script to be executed before performing a link.
    
    The script will be executed prior to any subsequent
    program() or module() targets being built.
    
    @param path: Path of the script to execute.
    @type path: string
    """
    self.libraryScripts.append(path)
    self._clearCache()
    
  def object(self, target, source, forceExtension=True, **kwargs):
    """Compile an individual source to an object file.
    
    @param target: Path of the target object file.
    @type target: string
    
    @param source: Path of the source file.
    @type source: string or FileTarget.
    
    @param forceExtension: If true then the target path will have
    the default object file extension appended if it doesn't already
    have it.
    
    @return: A FileTarget containing the path of the object file
    that will be built and the task that will build it.
    """
     
    # Take a snapshot of the build settings at this point and use that.
    compiler = self.clone()
    for k, v in kwargs.iteritems():
      setattr(compiler, k, v)
      
    return compiler._object(target, source, forceExtension)
    
  def _object(self, target, source, forceExtension=True):
    
    # Make note of which build engine we're using too
    engine = Script.getCurrent().engine
    
    if forceExtension:
      target = cake.path.forceExtension(target, self.objectSuffix)
    
    source, sourceTask = getPathAndTask(source)
    
    objectTask = engine.createTask(
      lambda t=target, s=source, e=engine, c=self:
        c.buildObject(t, s, e)
      )
    objectTask.startAfter(sourceTask)
    
    return FileTarget(path=target, task=objectTask)
    
  def objects(self, targetDir, sources, **kwargs):
    """Build a collection of objects to a target directory.
    
    @param targetDir: Path to the target directory where the built objects
    will be placed.
    @type targetDir: string
    
    @param sources: A list of source files to compile to object files.
    @type sources: sequence of string or FileTarget objects
    
    @return: A list of FileTarget objects, one for each object being
    built.
    """
    compiler = self.clone()
    for k, v in kwargs.iteritems():
      setattr(compiler, k, v)
    
    results = []
    for source in sources:
      sourcePath, _ = getPathAndTask(source)
      sourceName = cake.path.baseNameWithoutExtension(sourcePath)
      targetPath = cake.path.join(targetDir, sourceName)
      results.append(compiler._object(targetPath, source, forceExtension=True))
    return results
    
  def library(self, target, sources, forceExtension=True, **kwargs):
    """Build a library from a collection of objects.
    
    @param target: Path of the library file to build.
    @type target: string
    
    @param sources: A list of object files to archive.
    @type sources: list of string or FileTarget
    
    @param forceExtension: If True then the target path will have
    the default library extension appended to it if it not already
    present.
    
    @return: A FileTarget object representing the library that will
    be built and the task that will build it.
    """

    # Take a snapshot of the current compiler settings
    compiler = self.clone()
    for k, v in kwargs.iteritems():
      setattr(compiler, k, v)
  
    # And a copy of the current build engine
    engine = Script.getCurrent().engine

    paths, tasks = getPathsAndTasks(sources)
    
    if forceExtension:
      prefix, suffix = self.libraryPrefixSuffixes[0]
      target = cake.path.forcePrefixSuffix(target, prefix, suffix)
    
    self._setObjectsInLibrary(engine, target, paths)
    
    libraryTask = engine.createTask(
      lambda t=target, s=paths, e=engine, c=compiler:
        c.buildLibrary(t, s, e)
      )
    libraryTask.startAfter(tasks)
    
    return FileTarget(path=target, task=libraryTask)
    
  def module(self, target, sources, forceExtension=True, **kwargs):
    """Build a module/dynamic-library.
    
    Modules are executable code that can be dynamically loaded at
    runtime. On some platforms they are referred to as shared-libraries
    or dynamically-linked-libraries (DLLs).
    """
    
    # Take a snapshot of the current compiler settings
    compiler = self.clone()
    for k, v in kwargs.iteritems():
      setattr(compiler, k, v)
  
    # And a copy of the current build engine
    
    script = Script.getCurrent()
    engine = script.engine

    paths, tasks = getPathsAndTasks(sources)

    for libraryScript in compiler.libraryScripts:
      tasks.append(engine.execute(libraryScript, script.variant))
    
    if forceExtension:
      target = cake.path.forceExtension(target, compiler.moduleSuffix)
      if compiler.importLibrary:
        prefix, suffix = self.libraryPrefixSuffixes[0]
        compiler.importLibrary = cake.path.forcePrefixSuffix(
          compiler.importLibrary,
          prefix,
          suffix,
          )
    
    moduleTask = engine.createTask(
      lambda t=target, s=paths, e=engine, c=compiler:
        c.buildModule(t, s, e)
      )
    moduleTask.startAfter(tasks)
    
    # XXX: What about returning paths to import libraries?
    
    return FileTarget(path=target, task=moduleTask)
    
  def program(self, target, sources, forceExtension=True, **kwargs):
    """Build an executable program.

    @param target: Path to the target executable.
    @type target: string
    
    @param sources: A list of source objects/libraries to be linked
    into the executable.
    @type sources: sequence of string/FileTarget
    
    @param forceExtension: If True then target path will have the
    default executable extension appended if it doesn't already have
    it.
    """
    
    # Take a snapshot of the current compiler settings
    compiler = self.clone()
    for name, value in kwargs.iteritems():
      setattr(compiler, name, value)
  
    # And a copy of the current build engine
    script = Script.getCurrent()
    engine = script.engine

    paths, tasks = getPathsAndTasks(sources)
    
    for libraryScript in compiler.libraryScripts:
      tasks.append(engine.execute(libraryScript, script.variant))
    
    if forceExtension:
      target = cake.path.forceExtension(target, compiler.programSuffix)
    
    programTask = engine.createTask(
      lambda t=target, s=paths, e=engine, c=compiler:
        c.buildProgram(t, s, e)
      )
    programTask.startAfter(tasks)
    
    return FileTarget(path=target, task=programTask)
        
  ###########################
  # Internal methods not part of public API
  
  def _resolveLibraries(self, engine):
    """Resolve the list of library names to library paths.
    
    Searches for each library in the libraryPaths.
    If self.linkObjectsInLibrary is True then returns the paths of object files
    that comprise the library instead of the library path.
    
    @param engine: The engine to use for logging error messages.
    @type engine: cake.engine.Engine
    
    @return: A tuple containing a list of paths to resolved
    libraries/objects, followed by a list of unresolved libraries.
    @rtype: tuple of (list of string, list of string)
    """
    libraryPaths = []
    unresolvedLibs = []
    for library in reversed(self.libraries):
      if not cake.path.dirName(library):

        fileNames = [library]

        libraryExtension = os.path.normcase(cake.path.extension(library))
        for prefix, suffix in self.libraryPrefixSuffixes:
          if libraryExtension != os.path.normcase(suffix):
            fileNames.append(cake.path.addPrefix(library, prefix) + suffix)
                  
        for candidate in cake.path.join(reversed(self.libraryPaths), fileNames):
          if cake.filesys.isFile(candidate):
            libraryPaths.append(candidate)
            break
        else:
          engine.logger.outputDebug(
            "scan",
            "scan: Ignoring missing library '" + library + "'\n",
            )
          unresolvedLibs.append(library)
      else:
        if not cake.filesys.isFile(library):
          engine.raiseError(
            "cake: library '%s' does not exist.\n" % library
            )
        libraryPaths.append(library)
      
    if self.linkObjectsInLibrary:
      results = []
      for libraryPath in libraryPaths:
        objects = self._getObjectsInLibrary(engine, libraryPath)
        if objects is None:
          results.append(libraryPath)
        else:
          results.extend(objects)
      return results, unresolvedLibs
    else:
      return libraryPaths, unresolvedLibs
  
  def buildObject(self, target, source, engine):
    """Perform the actual build of an object.
    
    @param target: Path of the target object file.
    @type target: string
    
    @param source: Path of the source file.
    @type source: string
    
    @param engine: The build Engine to use when building this object.
    """
    preprocess, scan, compile, canBeCached = self.getObjectCommands(target, source, engine)
    
    args = [repr(preprocess), repr(scan), repr(compile)]
    
    # Check if the target needs building
    oldDependencyInfo, reasonToBuild = engine.checkDependencyInfo(target, args)
    if not reasonToBuild:
      return # Target is up to date
    engine.logger.outputDebug(
      "reason",
      "Rebuilding '" + target + "' because " + reasonToBuild + ".\n",
      )

    engine.logger.outputInfo("Compiling %s\n" % source)
      
    if canBeCached and self.objectCachePath is not None:
      #
      # Building the object using the object cache
      #
      def getCacheEntryPath(digest):
        d = "".join("%02x" % ord(c) for c in digest)
        return cake.path.join(self.objectCachePath, d[0], d[1], d)

      if oldDependencyInfo is not None:
        # Try to calculate the current hash using the old dependencies
        # list. If this is found in the cache then we can just use it
        # without having to determine the new dependency list.
        newDependencyInfo = DependencyInfo(
          targets=[FileInfo(path=target)],
          args=args,
          dependencies=oldDependencyInfo.dependencies,
          )
        newDigest = newDependencyInfo.calculateDigest(engine)
        
        cacheEntryPath = getCacheEntryPath(newDigest)
        if cake.filesys.isFile(cacheEntryPath):
          engine.logger.outputInfo("from cache: %s\n" % target)
          cake.filesys.copyFile(cacheEntryPath, target)
          engine.storeDependencyInfo(newDependencyInfo)
          return
      else:
        newDependencyInfo = DependencyInfo(
          targets=[FileInfo(path=target)],
          args=args,
          dependencies=None,
          )

      # Need to preprocess and scan the source file to get the new
      # list of dependencies.
      preprocess()
      newDependencies = scan()
      
      newDependencyInfo.dependencies = [
        FileInfo(
          path=path,
          timestamp=engine.getTimestamp(path),
          digest=engine.getFileDigest(path),
          )
        for path in newDependencies
        ]
      newDigest = newDependencyInfo.calculateDigest(engine)
      
      # Check if the hash of all dependencies using the new dependency
      # list has a cache entry.
      cacheEntryPath = getCacheEntryPath(newDigest)
      if cake.filesys.isFile(cacheEntryPath):
        engine.logger.outputInfo("from cache: %s\n" % target)
        cake.filesys.copyFile(cacheEntryPath, target)
        engine.storeDependencyInfo(newDependencyInfo)
        return

      # Finally, we need to do the compilation
      compile()
      
      # and save info on the dependencies of the newly built target
      engine.storeDependencyInfo(newDependencyInfo)
      
      # Try to update the cache with our newly built object file
      # but don't sweat if we can't write to the cache.
      try:
        cake.filesys.copyFile(target, cacheEntryPath)
      except EnvironmentError:
        pass
      
    else:
      #
      # Building the object without the object cache
      #
      
      # Need to run preprocessor first
      preprocess()
  
      newDependencies = []

      def storeDependencyInfo():
        newDependencyInfo = DependencyInfo(
          targets=[FileInfo(target)],
          args=args,
          dependencies=[
            FileInfo(
              path=path,
              timestamp=engine.getTimestamp(path),
              #digest=engine.getFileDigest(path),
              )
            for path in newDependencies
            ],
          )
        engine.storeDependencyInfo(newDependencyInfo)
      
      scanTask = engine.createTask(lambda: newDependencies.extend(scan()))
      scanTask.start(immediate=True)
      
      compileTask = engine.createTask(compile)
      compileTask.start(immediate=True)
      
      storeDependencyInfoTask = engine.createTask(storeDependencyInfo)
      storeDependencyInfoTask.startAfter(
        [scanTask, compileTask],
        immediate=True,
        )
  
  def getObjectCommands(self, target, source, engine):
    """Get the command-lines for compiling a source to a target.
    
    @return: A (preprocess, scan, compile, cache) tuple of the commands
    to execute for preprocessing, dependency scanning, compiling the source
    file and a flag indicating whether the compile result can be cached
    respectively.
    """
    engine.raiseError("Don't know how to compile %s\n" % source)
  
  def buildLibrary(self, target, sources, engine):
    """Perform the actual build of a library.
    
    @param target: Path of the target library file.
    @type target: string
    
    @param sources: List of source object files.
    @type sources: list of string
    
    @param engine: The Engine object to use for dependency checking
    etc.
    """

    archive, scan = self.getLibraryCommand(target, sources, engine)
    
    args = repr(archive)
    
    # Check if the target needs building
    _, reasonToBuild = engine.checkDependencyInfo(target, args)
    if not reasonToBuild:
      return # Target is up to date
    engine.logger.outputDebug(
      "reason",
      "Rebuilding '" + target + "' because " + reasonToBuild + ".\n",
      )

    engine.logger.outputInfo("Archiving %s\n" % target)
    
    cake.filesys.makeDirs(cake.path.dirName(target))
    
    archive()
    
    dependencies = scan()
    
    newDependencyInfo = DependencyInfo(
      targets=[FileInfo(target)],
      args=args,
      dependencies=[
        FileInfo(path=path, timestamp=engine.getTimestamp(path))
        for path in dependencies
        ],
      )
    
    engine.storeDependencyInfo(newDependencyInfo)
  
  def getLibraryCommand(self, target, sources, engine):
    """Get the command for constructing a library.
    """
    engine.raiseError("Don't know how to archive %s\n" % target)
  
  def buildModule(self, target, sources, engine):
    """Perform the actual build of a module.
    
    @param target: Path of the target module file.
    @type target: string
    
    @param sources: Paths of the source object files and
    libraries to link.
    @type sources: list of string
    
    @param engine: The Engine object to use for dependency checking
    etc.
    """
    link, scan = self.getModuleCommands(target, sources, engine)

    args = [repr(link), repr(scan)]
    
    # Check if the target needs building
    _, reasonToBuild = engine.checkDependencyInfo(target, args)
    if not reasonToBuild:
      return # Target is up to date
    engine.logger.outputDebug(
      "reason",
      "Rebuilding '" + target + "' because " + reasonToBuild + ".\n",
      )

    engine.logger.outputInfo("Linking %s\n" % target)
  
    link()
  
    dependencies = scan()
    
    newDependencyInfo = DependencyInfo(
      targets=[FileInfo(target)],
      args=args,
      dependencies=[
        FileInfo(path=path, timestamp=engine.getTimestamp(path))
        for path in dependencies
        ],
      )
    
    engine.storeDependencyInfo(newDependencyInfo)
  
  def getModuleCommands(self, target, sources, engine):
    """Get the commands for linking a module.
    
    @param target: path to the target file
    @type target: string
    
    @param sources: list of the object/library file paths to link into the
    module.
    @type sources: list of string
    
    @param engine: The cake Engine being used for the build.
    @type engine: cake.engine.Engine
    
    @return: A tuple (link, scan) representing the commands that perform
    the link and scan for dependencies respectively. The scan command
    returns the list of dependencies. 
    """
    engine.raiseError("Don't know how to link %s\n" % target)
  
  def buildProgram(self, target, sources, engine):
    """Perform the actual build of a module.
    
    @param target: Path of the target module file.
    @type target: string
    
    @param sources: Paths of the source object files and
    libraries to link.
    @type sources: list of string
    
    @param engine: The Engine object to use for dependency checking
    etc.
    """

    link, scan = self.getProgramCommands(target, sources, engine)

    args = [repr(link), repr(scan)]
    
    # Check if the target needs building
    _, reasonToBuild = engine.checkDependencyInfo(target, args)
    if not reasonToBuild:
      return # Target is up to date
    engine.logger.outputDebug(
      "reason",
      "Rebuilding '" + target + "' because " + reasonToBuild + ".\n",
      )

    engine.logger.outputInfo("Linking %s\n" % target)
  
    link()
  
    dependencies = scan()
    
    newDependencyInfo = DependencyInfo(
      targets=[FileInfo(target)],
      args=args,
      dependencies=[
        FileInfo(path=path, timestamp=engine.getTimestamp(path))
        for path in dependencies
        ],
      )
    
    engine.storeDependencyInfo(newDependencyInfo)

  def getProgramCommands(self, target, sources, engine):
    """Get the commands for linking a program.
    
    @param target: path to the target file
    @type target: string
    
    @param sources: list of the object/library file paths to link into the
    program.
    @type sources: list of string
    
    @param engine: The cake Engine being used for the build.
    @type engine: cake.engine.Engine
    
    @return: A tuple (link, scan) representing the commands that perform
    the link and scan for dependencies respectively. The scan command
    returns the list of dependencies. 
    """
    engine.raiseError("Don't know how to link %s\n" % target)
