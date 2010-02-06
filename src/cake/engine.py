"""Engine-Level Classes and Utilities.
"""

import hashlib
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

import cake.logging
import cake.bytecode
import cake.tools
import cake.task
import cake.path

class BuildError(Exception):
  """Exception raised when a build fails.
  
  This exception is treated as expected by the Cake build system as it won't
  output the stack-trace if raised by a task.
  """
  pass

class Variant(object):
  """A container for build configuration information.
  
  @ivar name: The name of this configuration.
  @type name: string or None
  @ivar tools: The available tools for this variant.
  @type tools: dict
  """
  
  def __init__(self, name=None):
    """Construct an empty variant.
    
    @param name: The name of the new variant.
    @type name: string or None
    """
    self.name = name
    self.tools = {}
  
  def clone(self, name=None):
    """Create an independent copy of this variant.
    
    @param name: The name of the new variant.
    @type name: string or None
    
    @return: The new Variant.
    """
    v = Variant(name=name)
    v.tools = dict((name, tool.clone()) for name, tool in self.tools.iteritems())
    return v

class Engine(object):
  """Main object that holds all of the singleton resources for a build.
  """
  
  def __init__(self):
    self._variants = set()
    self._defaultVariant = None
    self._byteCodeCache = {}
    self._timestampCache = {}
    self._digestCache = {}
    self._dependencyInfoCache = {}
    self._executed = {}
    self.logger = cake.logging.Logger()
      
  def addVariant(self, variant, default=False):
    """Register a new variant with this engine.
    
    @param variant: The Variant object to register.
    @type variant: L{Variant}
    
    @param default: If True then make this newly added variant the default
    build variant.
    @type default: C{bool}
    """
    self._variants.add(variant)
    if default:
      self._defaultVariant = variant
    
  def createTask(self, func):
    """Construct a new task that will call the specified function.
    
    This function wraps the function in an exception handler that prints out
    the stacktrace and exception details if an exception is raised by the
    function.
    
    @param func: The function that will be called with no args by the task once
    the task has been started.
    @type func: any callable
    
    @return: The newly created Task.
    @rtype: L{cake.task.Task}
    """
    def _wrapper():
      try:
        func()
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
        exceptionString = ''.join(traceback.format_exception_only(type(e), e))
        message = 'Unhandled Task Exception:\n%s%s' % (tracebackString, exceptionString)
        self.logger.outputError(message)
        raise

    task = cake.task.Task(_wrapper)

    # Set a traceback for the parent script task    
    if Script.getCurrent() is not None:
      task.traceback = traceback.extract_stack()[:-1]

    return task
    
  def raiseError(self, message):
    """Log an error and raise the BuildError exception.
    """
    self.logger.outputError(message)
    raise BuildError(message)
    
  def execute(self, path, variant=None):
    """Execute the script with the specified variant.
    
    @param path: Path of the Cake script file to execute.
    @type path: string

    @param variant: The build variant to execute this script with.
    @type variant: L{Variant} 

    @return: A Task object that completes when the script and any
    tasks it starts finish executing.
    @rtype: L{cake.task.Task}
    """
    if variant is None:
      variant = self._defaultVariant
    
    # TODO: Locks in here
    
    key = (path, variant)
    
    if key in self._executed:
      script = self._executed[key]
    else:
      def execute():
        cake.tools.__dict__.clear()
        for name, tool in variant.tools.items():
          setattr(cake.tools, name, tool.clone())
        self.logger.outputInfo("Executing %s\n" % script.path)
        script.execute()
      task = self.createTask(execute)
      script = Script(
        path=path,
        variant=variant,
        task=task,
        engine=self,
        )
      self._executed[key] = script
      task.addCallback(
        lambda: self.logger.outputInfo("Finished %s\n" % script.path)
        )
      task.start()

    return task

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
      hasher = hashlib.sha1()
      with open(path, 'rb') as f:
        blockSize = 512 * 1024
        data = f.read(blockSize)
        while data:
          hasher.update(data)
          data = f.read(blockSize)
      digest = hasher.digest()
      self._digestCache[key] = digest
      
    return digest
    
  def getDependencyInfo(self, targetPath):
    """Load the dependency info for the specified target.
    
    The dependency info contains information about the parameters and
    dependencies of a target at the time it was last built.
    
    @param targetPath: The path of the target.
    @type targetPath: string 
    
    @return: A DependencyInfo object for the target.
    
    @raise EnvironmentError: if the dependency info could not be retrieved.
    """
    dependencyInfo = self._dependencyInfoCache.get(targetPath, None)
    if dependencyInfo is None:
      depPath = targetPath + '.dep'
      
      with open(depPath, 'rb') as f:
        dependencyInfo = pickle.load(f)
      
      # Check that the dependency info is valid  
      if not isinstance(dependencyInfo, DependencyInfo):
        raise EnvironmentError("invalid dependency file")
      elif dependencyInfo.version != DependencyInfo.VERSION:
        raise EnvironmentError("wrong dependency file version")

      self._dependencyInfoCache[targetPath] = dependencyInfo
      
    return dependencyInfo
    
  def storeDependencyInfo(self, dependencyInfo):
    """Call this method after a target was built to save the
    dependencies of the target.
    """
    depPath = dependencyInfo.targets[0].path + '.dep'
    for target in dependencyInfo.targets:
      self._dependencyInfoCache[target.path] = dependencyInfo
    
    cake.filesys.makeDirs(cake.path.dirName(depPath))
    with open(depPath, 'wb') as f:
      pickle.dump(dependencyInfo, f, pickle.HIGHEST_PROTOCOL)
    
class DependencyInfo(object):
  """Object that holds the dependency info for a target.
  
  @ivar version: The current version of the dependency info.
  """
  
  VERSION = 1
  
  def __init__(self, targets, args, dependencies):
    self.version = self.VERSION
    self.targets = targets
    self.args = args
    self.dependencies = dependencies

  def isUpToDate(self, engine, args):
    """Query if the targets are up to date.
    """
    if args != self.args:
      return False
    
    for target in self.targets:
      if not target.exists(engine):
        return False
    
    for dependency in self.dependencies:
      if dependency.hasChanged(engine):
        return False
      
    return True

  def calculateDigest(self, engine):
    """Calculate the digest of the sources/dependencies.
    """
    hasher = hashlib.sha1()
    
    # Include the paths of the targets in the digest
    for t in self.targets:
      hasher.update(t.path.encode("utf8"))
      
    # Include parameters of the build    
    hasher.update(repr(self.args).encode("utf8"))
    
    for d in self.dependencies:
      
      # Let the engine know of any cached file digests from a
      # previous run.
      if d.timestamp is not None and d.digest is not None:
        engine.updateFileDigestCache(d.path, d.timestamp, d.digest)
      
      # Include the dependency file's path and content digest in
      # this digest.
      hasher.update(d.path.encode("utf8"))
      hasher.update(engine.getFileDigest(d.path))
      
    return hasher.digest()

class FileInfo(object):
  """A container for file information.
  """
  
  VERSION = 1
  
  def __init__(self, path, timestamp=None, digest=None):
    self.version = self.VERSION
    self.path = path
    self.timestamp = timestamp
    self.digest = digest
    
  def exists(self, engine):
    return os.path.isfile(self.path)
    
  def hasChanged(self, engine):
    if self.version != FileInfo.VERSION:
      return True
    
    try:
      currentTimestamp = engine.getTimestamp(self.path)
    except EnvironmentError:
      # File doesn't exist any more?
      return True 
    
    return currentTimestamp != self.timestamp

class Script(object):
  """A class that represents an instance of a Cake script. 
  """
  
  _current = threading.local()
  
  def __init__(self, path, variant, engine, task, parent=None):
    self.path = path
    self.dir = os.path.dirname(path)
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
    """
    if path in self._included:
      return
      
    includedScript = Script(
      path=path,
      variant=self.variant,
      engine=self.engine,
      task=self.task,
      parent=self,
      )
    self._included[path] = includedScript
    includedScript.execute()
    
  def execute(self):
    """Execute this script.
    """
    byteCode = self.engine.getByteCode(self.path)
    old = Script.getCurrent()
    Script._current.value = self
    try:
      exec byteCode
    finally:
      Script._current.value = old
