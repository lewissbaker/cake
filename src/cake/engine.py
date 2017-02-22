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
import cake.task
import cake.path
import cake.hash
import cake.filesys
import cake.threadpool

from cake.script import Script as _Script

class BuildError(Exception):
  """Exception raised when a build fails.
  
  This exception is treated as expected by the Cake build system as it won't
  output the stack-trace if raised by a task.
  """
  pass

class DependencyInfoError(Exception):
  """Exception raised when a dependency info file fails to load.
  """
  pass

class Variant(object):
  """A container for build configuration information.
  
  @ivar tools: The available tools for this variant.
  @type tools: dict
  """

  constructionScriptPath = None
  """Path to the script used to construct this variant before it is used for the first time.
  
  @type: string or None
  """
  
  def __init__(self, **keywords):
    """Construct an empty variant.
    """
    self.keywords = keywords
    self.tools = {}
    self._constructionLock = threading.Lock()
    self._isConstructed = False
  
  def __repr__(self):
    keywords = ", ".join('%s=%r' % (k, v) for k, v in self.keywords.iteritems())
    return "Variant(%s)" % keywords 
  
  def __getitem__(self, key):
    """Return a keywords value given its key.
    
    @param key:  The key of the keyword variable to get.
    @return: The value of the keyword variable.
    """
    return self.keywords[key]
  
  def _construct(self, configuration):
    # Do an initial check without acquiring the lock (which is slow).
    if self._isConstructed:
      return
    
    self._constructionLock.acquire()
    try:
      # Check again in case someone else got here first.
      if not self._isConstructed:
        if self.constructionScriptPath is not None:
          script = _Script(
            path=self.constructionScriptPath,
            configuration=configuration,
            variant=self,
            task=None,
            engine=configuration.engine,
            )
          script.execute()
        self._isConstructed = True
    finally:
      self._constructionLock.release()

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
  @type scriptThreadPool: L{ThreadPool}

  @ivar logger: The object used to output build messages.
  @type logger: L{Logger}

  @ivar parser: The object used to parse command line arguments.
  @type parser: L{OptionParser}

  @ivar args: The command line arguments.
  @type args: list of string

  @ivar options: The options found after parsing command line arguments.
  @type options: L{Option}

  @ivar oscwd: The initial working directory when Cake was first started.
  @type oscwd: string
  """
  
  scriptCachePath = None
  """Path to the script cache files.
  
  The absolute path to the directory that should store
  script cache files. If None the script cache files will be put next to the
  script files themselves with a different extension (usually .cakec).
  @type: string or None
  """
  dependencyInfoPath = None
  """Path to store dependency info files.
  
  The absolute path to the directory that should store
  dependency info files. If None the dependency info files will be put next to the
  target files themselves with a different extension (usually .dep).
  @type: string or None
  """
  
  forceBuild = False
  defaultConfigScriptName = "config.cake"
  maximumErrorCount = None
  
  def __init__(self, logger, parser, args):
    """Default Constructor.
    """
    self._byteCodeCache = {}
    self._timestampCache = {}
    self._digestCache = {}
    self._searchUpCache = {}
    self._configurations = {}
    self.scriptThreadPool = cake.threadpool.ThreadPool(1)
    self.errors = []
    self.warnings = []
    self.failedTargets = []
    self.logger = logger
    self.parser = parser
    self.args = args
    self.options = None
    self.oscwd = os.getcwd() # Save original cwd in case someone changes it.
    self.buildSuccessCallbacks = []
    self.buildFailureCallbacks = []

  @property
  def errorCount(self):
    return len(self.errors)

  @property
  def warningCount(self):
    return len(self.warnings)
  
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
  
  def findConfigScriptPath(self, path, configScriptName=None):
    """Attempt to find the path of the config script to use for building
    a particular path.
    
    @param path: Absolute path to start searching for the config script file.
    @type path: string
    
    @param configScriptName: Name of the config script file to search for
    or None to use the default configScriptName.
    @type configScriptName: string or None
    
    @return: Path to the config script file if found otherwise None.
    @rtype: string or None
    """
    if configScriptName is None:
      configScriptName = self.defaultConfigScriptName

    return self.searchUpForFile(path, configScriptName)
  
  def getConfiguration(self, path):
    """Get the configuration for a specified config script path.
    
    Executes the config script if not already executed.
    
    @param path: Absolute path of the config script used to
    populate the configuration.
    @type path: string
    
    @return: The Configuration that has been configured with the
    specified config script.
    @rtype: L{Configuration}
    """
    configuration = self._configurations.get(path, None)
    if configuration is None:
      # Note that we are potentially executing the configuration
      # script multiple times, but will only keep the Configuration
      # object that is registered first in self._configurations
      # dictionary below. This avoids needing a separate mutex
      # for configuration execution.
      configuration = Configuration(path=path, engine=self)
      script = _Script(
        path=cake.path.baseName(path),
        configuration=configuration,
        variant=None,
        engine=self,
        task=None,
        parent=None,
        )
      script.execute()
      configuration = self._configurations.setdefault(path, configuration)
    return configuration
  
  def findConfiguration(self, path, configScriptName=None):
    """Find the configuration for a particular path.
    
    @param path: Absolute path to start searching for a config script.
    @type path: string
    
    @param configScriptName: Name of the config script to search for.
    If not supplied then self.defaultConfigScriptName is used.
    @type configScriptName: string or None

    @return: The initialised Configuration object corresponding
    to the found config script.
    @rtype: L{Configuration}

    @raise BuildError: If the config script could not be found.
    """
    configScript = self.findConfigScriptPath(path, configScriptName)
    # Fall back on the default config script in this files path
    if configScript is None:
      configScript = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "config.py",
        )
    return self.getConfiguration(configScript)
  
  def execute(self, path, configScript=None, configScriptName=None, keywords={}):
    """Execute a script at specified path with all matching variants.
    
    The variants the script is executed with are determined by the
    keywords specified here.
    
    @param path: Absolute path of the script to execute.
    @type path: string.
    
    @param configScript: Absolute path of the config script to execute the
    script with, pass None to search for the config script.
    @type configScript: string or None
    
    @param configScriptName: Name of the config script file to search for
    if configScript was passed as None. If None then use the engine's
    default config script name.
    @type configScriptName: string or None
    
    @param keywords: Keywords used to filter the set of variants the
    script will be executed with.
    @type keywords: dictionary of string -> string or list of string

    @return: A task that will complete when the script and any tasks
    it spawns finishes executing.
    @rtype: L{Task}
    """
    if configScript is None:
      configuration = self.findConfiguration(path, configScriptName)
    else:
      configuration = self.getConfiguration(configScript)

    path = cake.path.relativePath(path, configuration.baseDir)

    tasks = []
    for variant in configuration.findAllVariants(keywords):
      task = configuration.execute(path, variant).task
      tasks.append(task)
      
    if not tasks:
      if keywords:
        args = " ".join("%s=%s" % (k, ",".join(v)) for k, v in keywords.items())
        self.raiseError(
          "No build variants found in '%s' that match the keywords '%s'.\n" % (configuration.path, args)
          )
      else:
        self.raiseError(
          "No build variants found in '%s'.\n" % configuration.path
          )
    elif len(tasks) > 1:
      task = self.createTask()
      task.completeAfter(tasks)
      task.lazyStart()
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
    
    # Save the script that created the task so that the task
    # inherits that same script when executed.
    currentScript = _Script.getCurrent()
    
    def _wrapper():
      if self.maximumErrorCount and self.errorCount >= self.maximumErrorCount:
        # TODO: Output some sort of message saying the build is being terminated
        # because of too many errors. But only output it once. Perhaps just set
        # a flag and check that in the runner.
        raise BuildError()
      
      try:
        # Restore the old script
        oldScript = _Script.getCurrent()
        _Script._current.value = currentScript
        try:
          return func()
        finally:
          _Script._current.value = oldScript
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
          message += "Pass '--debug=stack' if you require a more complete stack trace.\n"
        self.logger.outputError(message)
        self.errors.append(message)
        raise

    task = cake.task.Task(_wrapper)

    # Set a traceback for the parent script task
    if self.logger.debugEnabled("stack"):    
      if currentScript is not None:
        task.traceback = traceback.extract_stack()[:-1]

    return task
    
  def raiseError(self, message, targets=None):
    """Log an error and raise the BuildError exception.
    
    @param message: The error message to output.
    @type message: string
    
    @raise BuildError: Raises a build error that should cause the current
    task to fail.
    """
    self.logger.outputError(message)
    self.errors.append(message)
    if targets:
      append = self.failedTargets.append
      for t in targets:
        append(t)
    raise BuildError(message)
    
  def getByteCode(self, path, cached=True):
    """Load a python file and return the compiled byte-code.
    
    @param path: The path of the python file to load.
    @type path: string
    
    @param cached: True if the byte code should be cached to a separate
    file for quicker loading next time.
    @type cached: bool

    @return: A code object that can be executed with the python 'exec'
    statement.
    @rtype: C{types.CodeType}
    """
    byteCode = self._byteCodeCache.get(path, None)
    if byteCode is None:
      # Cache the code in a user-supplied directory if provided.
      if self.scriptCachePath is not None:
        assert cake.path.isAbs(path) # Need an absolute path to get a unique hash.
        pathDigest = cake.hash.sha1(path.encode("utf8")).digest()
        pathDigestStr = cake.hash.hexlify(pathDigest)
        cacheFilePath = cake.path.join(
          self.scriptCachePath,
          pathDigestStr[0],
          pathDigestStr[1],
          pathDigestStr[2],
          pathDigestStr
          )
        cake.filesys.makeDirs(cake.path.dirName(cacheFilePath))
      else:
        cacheFilePath = None
      byteCode = cake.bytecode.loadCode(path, cfile=cacheFilePath, cached=cached)
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
      # Assuming here that os.stat() returns the modification time in
      # seconds since the unix time epoch (Jan 1 1970 UTC).
      stat = os.stat(path)
      timestamp = stat.st_mtime
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
    
    @raise DependencyInfoError: if the dependency info could not be retrieved.
    """
    depPath = self.getDependencyInfoPath(target)
    
    # Read entire file at once otherwise thread-switching will kill performance.
    try:
      fileContents = cake.filesys.readFile(depPath)
    except EnvironmentError:
      raise DependencyInfoError("doesn't exist")
    
    # Split magic signature from the pickled dependency info.
    magicLength = len(DependencyInfo.MAGIC)
    dependencyString = fileContents[:-magicLength]
    dependencyMagic = fileContents[-magicLength:]
    
    if dependencyMagic != DependencyInfo.MAGIC:
      raise DependencyInfoError("has an invalid signature")

    try:      
      dependencyInfo = pickle.loads(dependencyString)
    except:
      raise DependencyInfoError("could not be understood")
    
    # Check that the dependency info is valid  
    if not isinstance(dependencyInfo, DependencyInfo):
      raise DependencyInfoError("has an invalid instance")

    if dependencyInfo.version != DependencyInfo.VERSION:
      raise DependencyInfoError("version has changed")

    return dependencyInfo
  
  def getDependencyInfoPath(self, target):
    """Get the path of a dependency info file given it's associated target.
    """
    # We need an absolute path to generate a unique hash.
    assert cake.path.isAbs(target)
    if self.dependencyInfoPath is not None:
      pathDigest = cake.hash.sha1(target.encode("utf8")).digest()
      pathDigestStr = cake.hash.hexlify(pathDigest)
      return cake.path.join(
        self.dependencyInfoPath,
        pathDigestStr[0],
        pathDigestStr[1],
        pathDigestStr[2],
        pathDigestStr[3],
        pathDigestStr
        )      
    else:
      return target + '.dep'
    
  def storeDependencyInfo(self, target, dependencyInfo):
    """Store dependency info for the specified target.
    
    @param target: Absolute path of the target.
    @type target: string
    
    @param dependencyInfo: The dependency info object to store.
    @type dependencyInfo: L{DependencyInfo}
    """
    depPath = self.getDependencyInfoPath(target)

    dependencyString = pickle.dumps(dependencyInfo, pickle.HIGHEST_PROTOCOL)
 
    try:
      cake.filesys.writeFile(depPath, dependencyString + DependencyInfo.MAGIC)
    except Exception, e:
      msg = "cake: Error writing dependency info to %s: %s" % (depPath, e)
      self.raiseError(msg, targets=dependencyInfo.targets)
  
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
  """The most recent DependencyInfo version.

  @type: int
  """
  
  MAGIC = "CKDP".encode('latin-1') # We need bytes for Python 3.x
  """A magic value stored in dependency files to ensure they are valid.
  
  This value is written to the end of the dependency file. If the power goes
  off or the computer stops while the dependency file is being written it will
  be regarded as invalid unless this value has been written.
  @type: string
  """
  
  def __init__(self, targets, args):
    self.version = self.VERSION
    self.targets = targets
    self.args = args
    self.depPaths = None
    self.depTimestamps = None
    self.depDigests = None

class Configuration(object):
  """A configuration is a collection of related Variants.
  
  It is typically populated by a config.cake script.
  
  @ivar engine: The Engine this configuration object belongs to.
  @type engine: L{Engine}
  
  @ivar path: The absolute path of the config script that was used to
  initialise this configuration.
  @type path: string
  
  @ivar dir: The absolute path of the directory containing the config
  script.
  @type dir: string
  
  @ivar baseDir: The absolute path of the directory that all relative
  paths will be assumed to be relative to. Defaults to the directory
  of the config script but may be overridden by the config script.
  @type baseDir: string

  @ivar scriptGlobals: A dictionary that will provide the initial
  values of each scripts global variables.
  @type scriptGlobals: dict
  """
  
  defaultBuildScriptName = 'build.cake'
  """The name of the build script to execute if the user asked to
  build a directory.
  """
  
  def __init__(self, path, engine):
    """Construct a new Configuration.
    
    @param path: Absolute path of the config script that will be 
    used to initialise this configuration.
    @type path: string
    
    @param engine: The Engine object this configuration belongs to.
    @type engine: L{Engine}
    """
    self.engine = engine
    self.path = path
    self.dir = cake.path.dirName(path)
    self.baseDir = self.dir
    self.scriptGlobals = {}
    self._variants = {}
    self._executed = {}
    self._executedLock = threading.Lock()
  
  def basePath(self, path):
    """Allows user-supplied conversion of a path passed to a Tool.
    
    @param path: The path to convert.
    @type path: string
    
    @return: The path converted via a user-supplied function. If this
    function hasn't been overriden by a user-supplied function the path
    is returned as is.
    @rtype: string
    """
    return path

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
    """
    key = frozenset(variant.keywords.iteritems())
    if key in self._variants:
      raise KeyError("Already added variant with these keywords: %r" % variant)
    
    self._variants[key] = variant

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
    
    @return: The Script object representing the script that will
    be executed. Use the returned script's .task to wait for the
    script to finish executing.
    """
    absPath = self.abspath(path)

    if cake.filesys.isDir(absPath):
      absPath = cake.path.join(absPath, self.defaultBuildScriptName)

    absPath = os.path.normpath(absPath)

    path = cake.path.relativePath(absPath, self.baseDir)

    key = (os.path.normcase(path), variant)

    currentScript = _Script.getCurrent()
    if currentScript:
      currentVariant = currentScript.variant
      currentConfiguration = currentScript.configuration
    else:
      currentVariant = None
      currentConfiguration = None
    
    # Make sure the variant is constructed and ready for use.  
    variant._construct(self)
    
    self._executedLock.acquire()
    try:
      script = self._executed.get(key, None)
      if script is None:
        tools = {}
        for name, tool in variant.tools.items():
          tools[name] = tool.clone()

        def execute():
          if self is not currentConfiguration:
            self.engine.logger.outputInfo("Building with %s - %s\n" % (self.path, variant))
          elif variant is not currentVariant:
            self.engine.logger.outputInfo("Building with %s\n" % str(variant))
          self.engine.logger.outputDebug(
            "script",
            "Executing %s\n" % script.path,
            )
          script.execute()
        task = self.engine.createTask(execute)
        script = _Script(
          path=path,
          configuration=self,
          variant=variant,
          task=task,
          tools=tools,
          engine=self.engine,
          )
        self._executed[key] = script
        task.addCallback(
          lambda: self.engine.logger.outputDebug(
            "script",
            "Finished %s\n" % script.path,
            )
          )
        task.lazyStart(threadPool=self.engine.scriptThreadPool)
    finally:
      self._executedLock.release()

    return script

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
    except DependencyInfoError, e:
      return None, "'" + targetPath + ".dep' " + str(e)

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
