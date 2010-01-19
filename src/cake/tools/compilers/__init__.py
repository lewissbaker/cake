"""Base class for all C/C++ compiler tools.
"""

__all__ = ["Compiler"]

import cake.path
import cake.filesys
import cake.tools
from cake.engine import Script, DependencyInfo, FileInfo, BuildError
from cake.tools import Tool, FileTarget, getPathsAndTasks, getPathAndTask
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
  """class.
  
  @ivar debugSymbols: If true then the compiler will output debug symbols.
  @type debugSymbols: boolean
  """
  
  NO_OPTIMISATION = 0
  PARTIAL_OPTIMISATION = 1
  FULL_OPTIMISATION = 2

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
  librarySuffix = '.a'
  moduleSuffix = '.so'
  programSuffix = ''
  
  objectCachePath = None
  
  def __init__(self):
    super(Compiler, self).__init__()
    self.includePaths = []
    self.defines = []
    self.forceIncludes = []

  def addIncludePath(self, path):
    """Add an include path to the preprocessor search path.
    
    Include paths added later in the list are searched earlier
    by the preprocessor.
    """
    self.includePaths.append(path)
    
  def addDefine(self, define, value=None):
    """Add a define to the preprocessor command-line.
    """
    if value is None:
      self.defines.append(define)
    else:
      self.defines.append("{0}={1}".format(define, value))
    
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
    
  def library(self, target, sources, forceExtension=True):
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
  
    # And a copy of the current build engine
    engine = Script.getCurrent().engine

    paths, tasks = getPathsAndTasks(sources)
    
    if forceExtension:
      target = cake.path.forceExtension(target, compiler.librarySuffix)
    
    libraryTask = engine.createTask(
      lambda t=target, s=paths, e=engine, c=compiler:
        c.buildLibrary(t, s, e)
      )
    libraryTask.startAfter(tasks)
    
    return FileTarget(path=target, task=libraryTask)
    
  def module(self, target, sources, forceExtension=True):
    """Build a module/dynamic-library.
    
    Modules are executable code that can be dynamically loaded at
    runtime. On some platforms they are referred to as shared-libraries
    or dynamically-linked-libraries (DLLs).
    """
    
    # Take a snapshot of the current compiler settings
    compiler = self.clone()
  
    # And a copy of the current build engine
    engine = Script.getCurrent().engine

    paths, tasks = getPathsAndTasks(sources)
    
    if forceExtension:
      target = cake.path.forceExtension(target, compiler.moduleSuffix)
    
    moduleTask = engine.createTask(
      lambda t=target, s=paths, e=engine, c=compiler:
        c.buildModule(t, s, e)
      )
    moduleTask.startAfter(tasks)
    
    # XXX: What about returning paths to import libraries?
    
    return FileTarget(path=target, task=moduleTask)
    
  def program(self, target, sources, forceExtension=True):
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
  
    # And a copy of the current build engine
    engine = Script.getCurrent().engine

    paths, tasks = getPathsAndTasks(sources)
    
    if forceExtension:
      target = cake.path.forceExtension(target, compiler.programSuffix)
    
    programTask = engine.createTask(
      lambda t=target, s=paths, e=engine, c=compiler:
        c.buildProgram(t, s, e)
      )
    programTask.startAfter(tasks)
    
    # XXX: What about returning paths to import libraries?
    
    return FileTarget(path=target, task=programTask)
        
  ###########################
  # Internal methods not part of public API
  
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
    
    # Check if the object file needs building
    try:
      oldDependencyInfo = engine.getDependencyInfo(target)
      if oldDependencyInfo.isUpToDate(engine, args):
        # Target is up to date, no work to do
        return
    except EnvironmentError:
      oldDependencyInfo = None

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
          cake.filesys.copyFile(cacheEntryPath, target)
          engine.storeDependencyInfo(newDependencyInfo)
          return

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
      scanTask.start()
      
      compileTask = engine.createTask(compile)
      compileTask.start()
      
      storeDependencyInfoTask = engine.createTask(storeDependencyInfo)
      storeDependencyInfoTask.startAfter([scanTask, compileTask])
  
  def getObjectCommands(self, target, source):
    """Get the command-lines for compiling a source to a target.
    
    @return: A (preprocess, scan, compile, cache) tuple of the commands
    to execute for preprocessing, dependency scanning, compiling the source
    file and a flag indicating whether the compile result can be cached
    respectively.
    """
    raise BuildError(target, "Don't know how to compile %s" % source)
  
  def buildLibrary(self, target, sources, engine):
    """Perform the actual build of a library.
    
    @param target: Path of the target library file.
    @type target: string
    
    @param sources: List of source object files.
    @type sources: list of string
    
    @param engine: The Engine object to use for dependency checking
    etc.
    """
    
    args = sources
    
    if cake.filesys.isFile(target):
      try:
        oldDependencyInfo = engine.getDependencyInfo(target)
        if oldDependencyInfo.isUpToDate(engine, args):
          return
      except EnvironmentError:
        pass
  
    print "Archiving %s" % target
    cake.filesys.makeDirs(cake.path.directory(target))
    with open(target, 'wb'):
      pass
    
    newDependencyInfo = DependencyInfo(
      targets=[FileInfo(target)],
      args=args,
      dependencies=[
        FileInfo(path=path, timestamp=engine.getTimestamp(path))
        for path in sources
        ],
      )
    
    engine.storeDependencyInfo(newDependencyInfo)
  
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
    args = sources
    
    if cake.filesys.isFile(target):
      try:
        oldDependencyInfo = engine.getDependencyInfo(target)
        if oldDependencyInfo.isUpToDate(engine, args):
          return
      except EnvironmentError:
        pass
  
    print "Linking %s" % target
    cake.filesys.makeDirs(cake.path.directory(target))
    with open(target, 'wb'):
      pass
    
    newDependencyInfo = DependencyInfo(
      targets=[FileInfo(target)],
      args=args,
      dependencies=[
        FileInfo(path=path, timestamp=engine.getTimestamp(path))
        for path in sources
        ],
      )
    
    engine.storeDependencyInfo(newDependencyInfo)
  
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
    args = sources
    
    if cake.filesys.isFile(target):
      try:
        oldDependencyInfo = engine.getDependencyInfo(target)
        if oldDependencyInfo.isUpToDate(engine, args):
          return
      except EnvironmentError:
        pass
  
    print "Linking %s" % target
    
    cake.filesys.makeDirs(cake.path.directory(target))
    with open(target, 'wb'):
      pass
    
    newDependencyInfo = DependencyInfo(
      targets=[FileInfo(target)],
      args=args,
      dependencies=[
        FileInfo(path=path, timestamp=engine.getTimestamp(path))
        for path in sources
        ],
      )
    
    engine.storeDependencyInfo(newDependencyInfo)
