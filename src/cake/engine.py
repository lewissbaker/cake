"""Engine-Level Classes and Utilities.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import codecs
import threading
import traceback
import sys
import os
import os.path
import time

import math
try:
  import cPickle as pickle
except ImportError:
  import pickle

import cake.bytecode
import cake.tools
import cake.task
import cake.path
import cake.hash
import cake.filesys
import cake.threadpool

class BuildError(Exception):
  """Exception raised when a build fails.
  
  This exception is treated as expected by the Cake build system as it won't
  output the stack-trace if raised by a task.
  """
  pass

class Variant(object):
  """A container for build configuration information.

  @ivar tools: The available tools for this variant.
  @type tools: dict
  """
  
  def __init__(self, **keywords):
    """Construct an empty variant.
    """
    self.keywords = keywords
    self.tools = {}
  
  def __repr__(self):
    keywords = ", ".join('%s=%r' % (k, v) for k, v in self.keywords.iteritems())
    return "Variant(%s)" % keywords 
  
  def matches(*args, **keywords):
    """Query if this variant matches the specified keywords.
    """
    # Don't use self in signature in case the user wants a keyword of
    # self.
    self, = args
    variantKeywords = self.keywords
    for key, value in keywords.iteritems():
      variantValue = variantKeywords.get(key, None)
      if isinstance(value, (list, tuple)):
        for v in value:
          if variantValue == v:
            break
        else:
          return False
      elif value == "all" and variantValue is not None:
        continue
      elif variantValue != value:
        return False
    else:
      return True
  
  def clone(self, **keywords):
    """Create an independent copy of this variant.
    
    @param keywords: The name/value pairs that define the new variant.
    @type keywords: dict of string->string
    
    @return: The new Variant.
    """
    newKeywords = self.keywords.copy()
    newKeywords.update(keywords)
    v = Variant(**newKeywords)
    v.tools = dict((name, tool.clone()) for name, tool in self.tools.iteritems())
    return v

class Engine(object):
  """Main object that holds all of the singleton resources for a build.
  
  @ivar scriptThreadPool: The scriptThreadPool is a single-threaded thread
  pool that is used to speed up incremental builds on multi-core platforms.
  It is used to execute scripts and check dependencies, both of which
  mainly use Python code. Threaded Python code executes under a
  notoriously slow GIL (Global Interpreter Lock). By executing most
  Python code on the same thread we can avoid the expensive GIL locking.  
  """
  
  forceBuild = False
  defaultBootScriptName = "boot.cake"
  
  def __init__(self, logger):
    """Default Constructor.
    """
    self._byteCodeCache = {}
    self._timestampCache = {}
    self._digestCache = {}
    self._dependencyInfoCache = {}
    self.logger = logger
    self.buildSuccessCallbacks = []
    self.buildFailureCallbacks = []
    self._searchUpCache = {}
    self._configurations = {}
    self.scriptThreadPool = cake.threadpool.ThreadPool(1)
  
  def searchUpForFile(self, path, fileName):
    """Attempt to find a file in a particular path or any of its parent
    directories.
    
    Caches previous search results for efficiency.
    
    @param path: The path to search for the file.
    @type path: string
    
    @param fileName: The name of the file to search for.
    @type path: string
    
    @return: Absolute path of the file found in the path or its nearest
    ancestor that contains the file, otherwise None if the file wasn't
    found.
    @rtype: string or None
    """
    
    searchUpCache = self._searchUpCache.get(fileName, None)
    if searchUpCache is None:
      searchUpCache = self._searchUpCache.setdefault(fileName, {})
    
    undefined = object()
    undefinedPaths = []
    path = os.path.normcase(os.path.abspath(path))
    while True:
      configPath = searchUpCache.get(path, undefined)
      if configPath is not undefined:
        break
      
      undefinedPaths.append(path)
      
      candidate = cake.path.join(path, fileName)
      if cake.filesys.isFile(candidate):
        configPath = cake.path.fileSystemPath(candidate)
        break
      
      parent = cake.path.dirName(path)
      if parent == path:
        configPath = None
        break
      
      path = parent

    for undefinedPath in undefinedPaths:
      searchUpCache[undefinedPath] = configPath

    return configPath
  
  def findBootScriptPath(self, path, bootScriptName=None):
    """Attempt to find the path of the boot script to use for building
    a particular path.
    
    @param path: Absolute path to start searching for the boot script file.
    @type path: string
    
    @param bootScriptName: Name of the boot script file to search for
    or None to use the default bootScriptName.
    @type bootScriptName: string or None
    
    @return: Path to the boot script file if found otherwise None.
    @rtype: string or None
    """
    if bootScriptName is None:
      bootScriptName = self.defaultBootScriptName

    return self.searchUpForFile(path, bootScriptName)
  
  def getConfiguration(self, path, keywords):
    """Get the configuration for a specified boot script path.
    
    Executes the boot script if not already executed.
    
    @param path: Absolute path of the boot script used to
    populate the configuration.
    @type path: string
    
    @param keywords: Keywords used to filter the set of variants the
    configuration will be executed with.
    @type keywords: dictionary of string -> string or list of string
    
    @return: The Configuration that has been configured with the
    specified boot script.
    @rtype: L{Configuration}
    """
    configuration = self._configurations.get(path, None)
    if configuration is None:
      configuration = Configuration(path=path, engine=self, keywords=keywords)
      script = Script(
        path=path,
        configuration=configuration,
        variant=None,
        engine=self,
        task=None,
        parent=None,
        )
      script.execute()
      configuration = self._configurations.setdefault(path, configuration)
    return configuration
  
  def findConfiguration(self, path, bootScriptName=None, keywords={}):
    """Find the configuration for a particular path.
    
    @param path: Absolute path to start searching for a boot script.
    @type path: string
    
    @param bootScriptName: Name of the boot script to search for.
    If not supplied then self.defaultBootScriptName is used.
    @type bootScriptName: string or None

    @param keywords: Keywords used to filter the set of variants the
    configuration will be executed with.
    @type keywords: dictionary of string -> string or list of string

    @return: The initialised Configuration object corresponding
    to the found boot script.
    @rtype: L{Configuration}
    """
    # TODO: Handle boot script not found error
    bootScript = self.findBootScriptPath(path, bootScriptName)
    return self.getConfiguration(bootScript, keywords)
  
  def execute(self, path, bootScript=None, bootScriptName=None, keywords={}):
    """Execute a script at specified path with all matching variants.
    
    The variants the script is executed with are determined by the
    defaultKeywords set by the boot script and the keywords specified
    here.
    
    @param path: Absolute path of the script to execute.
    @type path: string.
    
    @param bootScript: Absolute path of the boot script to execute the
    script with, pass None to search for the boot script.
    @type bootScript: string or None
    
    @param bootScriptName: Name of the boot script file to search for
    if bootScript was passed as None. If None then use the engine's
    default boot script name.
    @type bootScriptName: string or None
    
    @param keywords: Keywords used to filter the set of variants the
    script will be executed with. Any keywords specified here may
    be overridden by the boot script.
    @type keywords: dictionary of string -> string or list of string

    @return: A task that will complete when the script and any tasks
    it spawns finishes executing.
    @rtype: L{Task}
    """
    if bootScript is None:
      configuration = self.findConfiguration(path, bootScriptName, keywords)
    else:
      configuration = self.getConfiguration(bootScript, keywords)

    path = cake.path.relativePath(path, configuration.baseDir)

    tasks = []
    for variant in configuration.findDefaultVariants():
      task = configuration.execute(path, variant)
      tasks.append(task)
      
    if not tasks:
      self.raiseError("No build variants for %s" % path)
    elif len(tasks) > 1:
      task = self.createTask()
      task.completeAfter(tasks)
      task.start()
      return task
    else:
      return tasks[0]
  
  def addBuildSuccessCallback(self, callback):
    """Register a callback to be run if the build completes successfully.
    
    @param callback: The callback to run when the build completes
    successfully.
    @type callback: any callable
    """    
    self.buildSuccessCallbacks.append(callback)
  
  def addBuildFailureCallback(self, callback):
    """Register a callback to be run if the build fails.
    
    @param callback: The callback to run when the build fails.
    @type callback: any callable
    """    
    self.buildFailureCallbacks.append(callback)

  def onBuildSucceeded(self):
    """Execute build success callbacks.
    """    
    for callback in self.buildSuccessCallbacks:
      callback()
         
  def onBuildFailed(self):
    """Execute build failure callbacks.
    """    
    for callback in self.buildFailureCallbacks:
      callback()

  def createTask(self, func=None):
    """Construct a new task that will call the specified function.
    
    This function wraps the function in an exception handler that prints out
    the stacktrace and exception details if an exception is raised by the
    function.
    
    @param func: The function that will be called with no args by the task once
    the task has been started.
    @type func: any callable
    
    @return: The newly created Task.
    @rtype: L{Task}
    """
    if func is None:
      return cake.task.Task()
    
    def _wrapper():
      try:
        return func()
      except BuildError:
        # Assume build errors have already been reported
        raise
      except Exception, e:
        tbs = [traceback.extract_tb(sys.exc_info()[2])]

        t = task
        while t is not None:
          tb = getattr(t, "traceback", None)
          if tb is not None:
            tbs.append(t.traceback)
          t = t.parent

        tracebackString = ''.join(
          ''.join(traceback.format_list(tb)) for tb in reversed(tbs)
          )
        exceptionString = ''.join(traceback.format_exception_only(e.__class__, e))
        message = 'Unhandled Task Exception:\n%s%s' % (tracebackString, exceptionString)
        if not self.logger.debugEnabled("stack"):
          message += "Pass '-d stack' if you require a more complete stack trace.\n"    
        self.logger.outputError(message)
        raise

    task = cake.task.Task(_wrapper)

    # Set a traceback for the parent script task
    if self.logger.debugEnabled("stack"):    
      if Script.getCurrent() is not None:
        task.traceback = traceback.extract_stack()[:-1]

    return task
    
  def raiseError(self, message):
    """Log an error and raise the BuildError exception.
    
    @param message: The error message to output.
    @type message: string
    
    @raise BuildError: Raises a build error that should cause the current
    task to fail.
    """
    self.logger.outputError(message)
    raise BuildError(message)
    
  def getByteCode(self, path):
    """Load a python file and return the compiled byte-code.
    
    @param path: The path of the python file to load.
    @type path: string
    
    @return: A code object that can be executed with the python 'exec'
    statement.
    @rtype: C{types.CodeType}
    """
    byteCode = self._byteCodeCache.get(path, None)
    if byteCode is None:
      byteCode = cake.bytecode.loadCode(path)
      self._byteCodeCache[path] = byteCode
    return byteCode
    
  def notifyFileChanged(self, path):
    """Let the engine know a file has changed.
    
    This allows the engine to invalidate any information about the file
    it may have previously cached.
    
    @param path: The path of the file that has changed.
    @type path: string
    """
    self._timestampCache.pop(path, None)
    
  def getTimestamp(self, path):
    """Get the timestamp of the file at the specified path.
    
    @param path: Path of the file whose timestamp you want.
    @type path: string
    
    @return: The timestamp in seconds since 1 Jan, 1970 UTC.
    @rtype: float 
    """
    timestamp = self._timestampCache.get(path, None)
    if timestamp is None:
      stat = os.stat(path)
      timestamp = time.mktime(time.gmtime(stat.st_mtime))
      # The above calculation truncates to the nearest second so we need to
      # re-add the fractional part back to the timestamp otherwise 
      timestamp += math.fmod(stat.st_mtime, 1)
      self._timestampCache[path] = timestamp
    return timestamp

  def updateFileDigestCache(self, path, timestamp, digest):
    """Update the internal cache of file digests with a new entry.
    
    @param path: The path of the file.
    @param timestamp: The timestamp of the file at the time the digest
    was calculated.
    @param digest: The digest of the contents of the file.
    """
    key = (path, timestamp)
    self._digestCache[key] = digest

  def getFileDigest(self, path):
    """Get the SHA1 digest of a file's contents.
    
    @param path: Path of the file to digest.
    @type path: string
    
    @return: The SHA1 digest of the file's contents.
    @rtype: string of 20 bytes
    """
    timestamp = self.getTimestamp(path)
    key = (path, timestamp)
    digest = self._digestCache.get(key, None)
    if digest is None:
      hasher = cake.hash.sha1()
      f = open(path, 'rb')
      try:
        blockSize = 512 * 1024
        data = f.read(blockSize)
        while data:
          hasher.update(data)
          data = f.read(blockSize)
      finally:
        f.close()
      digest = hasher.digest()
      self._digestCache[key] = digest
      
    return digest
    
  def getDependencyInfo(self, target):
    """Load the dependency info for the specified target.
    
    The dependency info contains information about the parameters and
    dependencies of a target at the time it was last built.
    
    @param target: The absolute path of the target.
    @type target: string
    
    @return: A DependencyInfo object for the target.
    @rtype: L{DependencyInfo}
    
    @raise EnvironmentError: if the dependency info could not be retrieved.
    """
    dependencyInfo = self._dependencyInfoCache.get(target, None)
    if dependencyInfo is None:
      depPath = target + '.dep'
      
      # Read entire file at once otherwise thread-switching will kill
      # performance
      f = open(depPath, 'rb')
      try:
        dependencyString = f.read()
      finally:
        f.close()
        
      dependencyInfo = pickle.loads(dependencyString) 
      
      # Check that the dependency info is valid  
      if not isinstance(dependencyInfo, DependencyInfo):
        raise EnvironmentError("invalid dependency file")

      self._dependencyInfoCache[target] = dependencyInfo
      
    return dependencyInfo
    
  def storeDependencyInfo(self, target, dependencyInfo):
    """Store dependency info for the specified target.
    
    @param target: Absolute path of the target.
    @type target: string
    
    @param dependencyInfo: The dependency info object to store.
    @type dependencyInfo: L{DependencyInfo}
    """
    depPath = target + '.dep'

    dependencyString = pickle.dumps(dependencyInfo, pickle.HIGHEST_PROTOCOL)
    
    cake.filesys.writeFile(depPath, dependencyString)
      
    self._dependencyInfoCache[target] = dependencyInfo
  
class DependencyInfo(object):
  """Object that holds the dependency info for a target.
  
  @ivar version: The version of this dependency info.
  @type version: int
  @ivar targets: A list of target file paths.
  @type targets: list of strings
  @ivar args: The arguments used for the build.
  @type args: usually a list of string's
  """
  
  VERSION = 3
  """The most recent DependencyInfo version."""
  
  def __init__(self, targets, args):
    self.version = self.VERSION
    self.targets = targets
    self.args = args
    self.depPaths = None
    self.depTimestamps = None
    self.depDigests = None

class Script(object):
  """A class that represents an instance of a Cake script. 
  """
  
  _current = threading.local()
  
  def __init__(self, path, configuration, variant, engine, task, parent=None):
    """Constructor.
    
    @param path: The path to the script file.
    @param configuration: The configuration to build.
    @param variant: The variant to build.
    @param engine: The engine instance.
    @param task: A task that should complete when all tasks within
    the script have completed.
    @param parent: The parent script or None if this is the root script. 
    """
    self.path = path
    self.dir = cake.path.dirName(path)
    self.configuration = configuration
    self.variant = variant
    self.engine = engine
    self.task = task
    if parent is None:
      self.root = self
      self._included = {self.path : self}
    else:
      self.root = parent.root
      self._included = parent._included

  @staticmethod
  def getCurrent():
    """Get the current thread's currently executing script.
    
    @return: The currently executing script.
    @rtype: L{Script}
    """
    return getattr(Script._current, "value", None)
  
  @staticmethod
  def getCurrentRoot():
    """Get the current thread's root script.
    
    This is the top-level script currently being executed.
    A script may not be the top-level script if it is executed due
    to inclusion from another script.
    """
    current = Script.getCurrent()
    if current is not None:
      return current.root
    else:
      return None

  def cwd(self, *args):
    """Return the path prefixed with the current script's directory.
    """
    return cake.path.join(self.dir, *args)

  def include(self, path):
    """Include another script for execution within this script's context.
    
    A script will only be included once within a given context.
    
    @param path: The path of the file to include.
    @type path: string
    """
    if path in self._included:
      return
      
    includedScript = Script(
      path=path,
      variant=self.variant,
      engine=self.engine,
      configuration=self.configuration,
      task=self.task,
      parent=self,
      )
    self._included[path] = includedScript
    includedScript.execute()
    
  def execute(self):
    """Execute this script.
    """
    # Use an absolute path so an absolute path is embedded in the .pyc file.
    # This will make exceptions clickable in Eclipse, but it means copying
    # your .pyc files may cause their embedded paths to be incorrect.
    absPath = self.configuration.abspath(self.path)
    byteCode = self.engine.getByteCode(absPath)
    old = Script.getCurrent()
    Script._current.value = self
    try:
      exec byteCode in {}
    finally:
      Script._current.value = old

class Configuration(object):
  """A configuration is a collection of related Variants.
  
  It is typically populated by a boot.cake script.
  
  @ivar engine: The Engine this configuration object belongs to.
  @type engine: L{Engine}
  
  @ivar path: The absolute path of the boot script that was used to
  initialise this configuration.
  @type path: string
  
  @ivar dir: The absolute path of the directory containing the boot
  script.
  @type dir: string
  
  @ivar baseDir: The absolute path of the directory that all relative
  paths will be assumed to be relative to. Defaults to the directory
  of the boot script but may be overridden by the boot script.
  @type baseDir: string
  
  @ivar keywords: A dictionary of keyword values used to filter the
  set of variants a script will be built with.
  @type keywords: dict of string -> string or list of string.
  """
  
  defaultBuildScriptName = 'build.cake'
  """The name of the build script to execute if the user asked to
  build a directory.
  """
  
  def __init__(self, path, engine, keywords={}):
    """Construct a new Configuration.
    
    @param path: Absolute path of the boot script that will be 
    used to initialise this configuration.
    @type path: string
    
    @param engine: The Engine object this configuration belongs to.
    @type engine: L{Engine}
    
    @param keywords: A dictionary of keyword values used to filter the
    set of variants a script will be built with.
    @type keywords: dict of string -> string or list of string.    
    """
    self.engine = engine
    self.path = path
    self.keywords = dict(keywords)
    self.dir = cake.path.dirName(path)
    self.baseDir = self.dir
    self._variants = {}
    self._executed = {}
    self._executedLock = threading.Lock()
    
  def abspath(self, path):
    """Convert a path to be absolute.
    
    @param path: The path to convert to an absolute path.
    @type path: string
    
    @return: If the path was a relative path then returns the path
    appended to self.baseDir, otherwise returns the path unchanged.
    @rtype: string
    """
    if not os.path.isabs(path):
      path = os.path.join(self.baseDir, path)
    return path
    
  def addVariant(self, variant):
    """Register a new variant with this engine.
    
    @param variant: The Variant object to register.
    @type variant: L{Variant}
    
    @param default: If True then make this newly added variant the default
    build variant.
    @type default: C{bool}
    """
    key = frozenset(variant.keywords.iteritems())
    if key in self._variants:
      raise KeyError("Already added variant with these keywords: %r" % variant)
    
    self._variants[key] = variant

  def findDefaultVariants(self):
    """Find all variants that match the specified keywords.
    
    Keywords not specified will assume the 'defaultKeywords' values.
    """
    return self.findAllVariants(self.keywords)
    
  def findAllVariants(self, keywords={}):
    """Find all variants that match the specified keywords.
    
    @param keywords: A collection of keywords to match against.
    @type keywords: dictionary of string -> string or list of string
    
    @return: Sequence of Variant objects that match the keywords.
    @rtype: sequence of L{Variant}
    """
    for variant in self._variants.itervalues():
      if variant.matches(**keywords):
        yield variant
  
  def findVariant(self, keywords, baseVariant=None):
    """Find the variant that matches the specified keywords.
    
    @param keywords: A dictionary of key/value pairs the variant needs
    to match. The value can be either a string, "all", a list of
    strings or None.
    
    @param baseVariant: If specified then attempts to find the variant
    that has the same keywords as this variant when the keyword is
    not specified in 'keywords'.
    @type baseVariant: L{Variant} or C{None}
    
    @return: The variant that matches the keywords.
    @rtype: L{Variant}
    
    @raise LookupError: If no variants matched or more than one variant
    matched the criteria.
    """
    if baseVariant is None:
      results = list(self.findAllVariants(keywords))
    else:
      results = []
      getBaseValue = baseVariant.keywords.get
      for variant in self.findAllVariants(keywords):
        for key, value in variant.keywords.iteritems():
          if key not in keywords:
            baseValue = getBaseValue(key, None)
            if value != baseValue:
              break
        else:
          results.append(variant)
    
    if not results:
      raise LookupError("No variants matched criteria.")
    elif len(results) > 1:
      msg = "Found %i variants that matched criteria.\n" % len(results)
      msg += "".join("- %r\n" % v for v in results)
      raise LookupError(msg)

    return results[0]

  def execute(self, path, variant):
    """Execute a build script.
    
    Uses this configuration with specified build variant.
    
    @param path: Path of the build script.
    @param variant: The variant to execute the script with.
    """
    absPath = self.abspath(path)

    if cake.filesys.isDir(absPath):
      absPath = cake.path.join(absPath, self.defaultBuildScriptName)

    absPath = os.path.normpath(absPath)

    path = cake.path.relativePath(absPath, self.baseDir)

    key = (os.path.normcase(path), variant)

    currentScript = Script.getCurrent()
    if currentScript:
      currentVariant = currentScript.variant
      currentConfiguration = currentScript.configuration
    else:
      currentVariant = None
      currentConfiguration = None
    
    self._executedLock.acquire()
    try:
      script = self._executed.get(key, None)
      if script is not None:
        task = script.task
      else:
        def execute():
          cake.tools.__dict__.clear()
          for name, tool in variant.tools.items():
            setattr(cake.tools, name, tool.clone())
          if self is not currentConfiguration:
            self.engine.logger.outputInfo("Building with %s - %s\n" % (self.path, variant))
          elif variant is not currentVariant:
            self.engine.logger.outputInfo("Building with %s\n" % str(variant))
          self.engine.logger.outputInfo("Executing %s\n" % script.path)
          script.execute()
        task = self.engine.createTask(execute)
        script = Script(
          path=path,
          configuration=self,
          variant=variant,
          task=task,
          engine=self.engine,
          )
        self._executed[key] = script
        task.addCallback(
          lambda: self.engine.logger.outputDebug(
            "script",
            "Finished %s\n" % script.path,
            )
          )
        task.start(threadPool=self.engine.scriptThreadPool)
    finally:
      self._executedLock.release()

    return task

  def createDependencyInfo(self, targets, args, dependencies, calculateDigests=False):
    """Construct a new DependencyInfo object.
    
    @param targets: A list of file paths of targets.
    @type targets: list of string
    @param args: A value representing the parameters of the build.
    @type args: object
    @param dependencies: A list of file paths of dependencies.
    @type dependencies: list of string
    @param calculateDigests: Whether or not to store the digests of
    dependencies in the DependencyInfo.
    @type calculateDigests: bool
    
    @return: A DependencyInfo object.
    """
    dependencyInfo = DependencyInfo(targets=list(targets), args=args)
    paths = dependencyInfo.depPaths = list(dependencies)
    abspath = self.abspath
    paths = [abspath(p) for p in paths]
    getTimestamp = self.engine.getTimestamp
    dependencyInfo.depTimestamps = [getTimestamp(p) for p in paths]
    if calculateDigests:
      getFileDigest = self.engine.getFileDigest
      dependencyInfo.depDigests = [getFileDigest(p) for p in paths]
    return dependencyInfo

  def storeDependencyInfo(self, dependencyInfo):
    """Call this method after a target was built to save the
    dependencies of the target.
    
    @param dependencyInfo: The dependency info object to be stored.
    @type dependencyInfo: L{DependencyInfo}  
    """
    absTargetPath = self.abspath(dependencyInfo.targets[0])
    self.engine.storeDependencyInfo(absTargetPath, dependencyInfo)

  def checkDependencyInfo(self, targetPath, args):
    """Check dependency info to see if the target is up to date.
    
    The dependency info contains information about the parameters and
    dependencies of a target at the time it was last built.
    
    @param targetPath: The path of the target.
    @type targetPath: string 
    @param args: The current arguments.
    @type args: list of string 

    @return: A tuple containing the previous DependencyInfo or None if not
    found, and the string reason to build or None if the target is up
    to date.
    @rtype: tuple of (L{DependencyInfo} or None, string or None)
    """
    abspath = self.abspath
    absTargetPath = abspath(targetPath)
    try:
      dependencyInfo = self.engine.getDependencyInfo(absTargetPath)
    except EnvironmentError:
      return None, "'" + targetPath + ".dep' doesn't exist"

    if dependencyInfo.version != DependencyInfo.VERSION:
      return None, "'" + targetPath + ".dep' version has changed"

    if self.engine.forceBuild:
      return dependencyInfo, "rebuild has been forced"

    if args != dependencyInfo.args:
      return dependencyInfo, "'" + repr(args) + "' != '" + repr(dependencyInfo.args) + "'"
    
    isFile = cake.filesys.isFile
    for target in dependencyInfo.targets:
      if not isFile(abspath(target)):
        return dependencyInfo, "'" + target + "' doesn't exist"
    
    getTimestamp = self.engine.getTimestamp
    paths = dependencyInfo.depPaths
    timestamps = dependencyInfo.depTimestamps
    assert len(paths) == len(timestamps)
    for i in xrange(len(paths)):
      path = paths[i]
      try:
        if getTimestamp(abspath(path)) != timestamps[i]:
          return dependencyInfo, "'" + path + "' has been changed"
      except EnvironmentError:
        return dependencyInfo, "'" + path + "' no longer exists" 
    
    return dependencyInfo, None

  def checkReasonToBuild(self, targets, sources):
    """Check for a reason to build given a list of targets and sources.
    
    @param targets: A list of target files.
    @type targets: list of string
    @param sources: A list of source files.
    @type sources: list of string
    
    @return: A reason to build if a rebuild is required, otherwise None.
    @rtype: string or None 
    """
  
    abspath = self.abspath
    
    if self.engine.forceBuild:
      return "rebuild has been forced"

    getTimestamp = self.engine.getTimestamp

    oldestTimestamp = None
    for t in targets:
      try:
        timestamp = getTimestamp(abspath(t))
      except EnvironmentError:
        return "'" + t + "' doesn't exist"
      if oldestTimestamp is None or timestamp < oldestTimestamp:
        oldestTimestamp = timestamp
    
    newestTimestamp = None
    for s in sources:
      try:
        timestamp = getTimestamp(abspath(s))
      except EnvironmentError:
        return "'" + s + "' doesn't exist"
      if newestTimestamp is None or timestamp > newestTimestamp:
        newestTimestamp = timestamp
        newestSource = s

    if newestTimestamp is not None and oldestTimestamp is not None and newestTimestamp > oldestTimestamp:  
      return "'" + newestSource + "' has been changed"
    
    return None
    
  def primeFileDigestCache(self, dependencyInfo):
    """Prime the engine's file-digest cache using any cached
    information stored in this dependency info.
    """
    if dependencyInfo.depDigests and dependencyInfo.depTimestamps:
      paths = dependencyInfo.depPaths
      timestamps = dependencyInfo.depTimestamps
      digests = dependencyInfo.depDigests
      assert len(digests) == len(paths)
      assert len(timestamps) == len(paths)
      updateFileDigestCache = self.engine.updateFileDigestCache
      abspath = self.abspath
      for i in xrange(len(paths)):
        updateFileDigestCache(abspath(paths[i]), timestamps[i], digests[i])

  def calculateDigest(self, dependencyInfo):
    """Calculate the digest of the sources/dependencies.

    @return: The current digest of the dependency info.
    @rtype: string of 20 bytes
    """
    self.primeFileDigestCache(dependencyInfo)
    
    hasher = cake.hash.sha1()
    addToDigest = hasher.update
    
    encodeToUtf8 = lambda value, encode=codecs.utf_8_encode: encode(value)[0]
    getFileDigest = self.engine.getFileDigest
    
    # Include the paths of the targets in the digest
    for target in dependencyInfo.targets:
      addToDigest(encodeToUtf8(target))
      
    # Include parameters of the build    
    addToDigest(encodeToUtf8(repr(dependencyInfo.args)))

    abspath = self.abspath
    for path in dependencyInfo.depPaths:
      # Include the dependency file's path and content digest in
      # this digest.
      addToDigest(encodeToUtf8(path))
      addToDigest(getFileDigest(abspath(path)))
      
    return hasher.digest()
