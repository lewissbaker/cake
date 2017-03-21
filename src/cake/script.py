"""Base script class and utilities.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import threading
import cake.path

from cake.target import Target
from cake.async import AsyncResult, waitForAsyncResult, flatten

_undefined = object()

class ScriptResult(AsyncResult):
  """A placeholder that can be used to reference a result of another
  script that may not be available yet.
  
  The result will be available when the task has completed successfully.
  """
  
  __slots__ = ['__script', '__name', '__default']
  
  def __init__(self, script, name, default=_undefined):
    self.__script = script
    self.__name = name
    self.__default = default
    
  @property
  def script(self):
    """The Script that will be executed.
    """
    return self.__script
    
  @property
  def task(self):
    """The script's task.
    """
    return self.__script.task

  @property
  def result(self):
    """Access the result.
    """
    if not self.task.completed:
      raise AttributeError("ScriptResult.result only available once Script task has completed")

    try:
      return self.__script._getResult(self.__name)
    except KeyError:
      default = self.__default
      if default is not _undefined:
        return default
      else:
        raise

class ScriptTarget(Target):
  """A script target is a named target defined by a script.

  These types of targets can be built from the command-line.

  Every top-level script has a default script-target that is
  built if the user does not specify a particular target to
  build when building that cake script.
  """

  __slots__ = ['script', 'name', 'targets']

  def __init__(self, script, name):
    task = script.engine.createTask(self._finalise)
    task.lazyStartAfter(script.task)

    super(ScriptTarget, self).__init__(task)

    self.name = name
    self.script = script
    self.targets = []

  def __str__(self):
    if self.name is None:
      return self.script.path
    else:
      return self.script.path + "@" + self.name

  @waitForAsyncResult
  def addTarget(self, target):
    if not isinstance(target, Target):
      raise TypeError("Must specify Target object for addTarget not " + str(type(target)))

    self.targets.append(target)
    self.task.completeAfter(target.task)

  @waitForAsyncResult
  def addTargets(self, targets):
    targets = flatten(targets)
    for target in targets:
      if not isinstance(target, Target):
        raise TypeError("Must specify Target object for addTargets")

    self.targets.extend(targets)
    self.task.completeAfter(t.task for t in targets)

  def _finalise(self):
    if not self.targets:
      engine = self.script.engine
      msg = "Warning: No targets defined for named script target %s\n" % str(self)
      engine.logger.outputWarning(msg)
      engine.warnings.append(msg)

class Script(object):
  """A class that represents an instance of a Cake script. 
  """
  
  _current = threading.local()
  
  def __init__(self, path, configuration, variant, engine, task, tools=None, parent=None):
    """Constructor.
    
    @param path: The path to the script file.
    @param configuration: The configuration to build.
    @param variant: The variant to build.
    @param engine: The engine instance.
    @param task: A task that should complete when all tasks within
    the script have completed.
    @param tools: The tools dictionary to use as cake.tools for this script.
    @param parent: The parent script or None if this is the root script. 
    """
    self.path = path
    self.dir = cake.path.dirName(path) or '.'
    self.configuration = configuration
    self.variant = variant
    self.engine = engine
    self.task = task
    self.parent = parent
    if tools is None:
      self.tools = {}
    else:
      self.tools = tools
    self._results = {}
    if parent is None:
      self.root = self
      self._defaultTarget = ScriptTarget(self, None)
      self._targets = {}
    else:
      self.root = parent.root
    self._executionLock = threading.Lock()
    self._executed = False

  def _getResult(self, name):
    # Immediately access the result. Potentially even before the scripts task
    # has completed.
    return self._results[name]

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

  def getAncestors(self):
    """Query the include ancestry of this script.
    
    @return: A sequence of Script objects starting with self and
    ending with the root Script that indicates how this script was
    included from the root script.
    """
    s = self
    while s:
      yield s
      s = s.parent

  def setResult(self, **kwargs):
    """Return a set of named values from the script execution.
    """
    self._results.update(kwargs)

  def getResult(self, name, *args, **kwargs):
    """Get a placeholder for a result defined by this script when it is
    executed.
    
    The script will be executed immediately if the '.result' member is
    accessed.

    @param name: The name of the script result to retrieve.
    @param default: If supplied then the default value to return in case
    the script does not define that result.
    """
    return ScriptResult(self, name, *args, **kwargs)

  def getDefaultTarget(self):
    """Get the default ScriptTarget for this script.

    This is the target that should be built by default when the command-line
    has just specified a script to build.
    """
    return self.root._defaultTarget

  def getTarget(self, name):
    """Get the named script target for this script.

    @param name: The name of the target.
    @type name: C{basestring}

    @return: The ScriptTarget with the specified name.
    @rtype: L{ScriptTarget}
    """
    if name is None:
      return self.getDefaultTarget()

    targets = self.root._targets
    target = targets.get(name, None)
    if target is None:
      target = targets.setdefault(name, ScriptTarget(script=self, name=name))

    return target

  def cwd(self, *args):
    """Return the path prefixed with the current script's directory.
    """
    d = self.dir
    if d == '.' and args:
      return cake.path.join(*args)
    else:
      return cake.path.join(d, *args)

  def execute(self, cached=True):
    """Execute this script if it hasn't already been executed.

    @param cached: True if the byte code should be cached to a separate
    file for quicker loading next time.
    @type cached: bool
    """
    if self._executed:
      return
    
    self._executionLock.acquire()
    try:
      # Must check again in case we have been waiting for another thread to execute.
      if not self._executed:
        try:
          # Use an absolute path so an absolute path is embedded in the .pyc file.
          # This will make exceptions clickable in Eclipse, but it means copying
          # your .pyc files may cause their embedded paths to be incorrect.
          if self.configuration is not None:
            absPath = self.configuration.abspath(self.path)
          else:
            absPath = cake.path.absPath(self.path)
          byteCode = self.engine.getByteCode(absPath, cached=cached)
          scriptGlobals = {'__file__': absPath}
          if self.configuration is not None:
            scriptGlobals.update(self.configuration.scriptGlobals)
          old = Script.getCurrent()
          Script._current.value = self
          try:
            exec byteCode in scriptGlobals
          finally:
            Script._current.value = old
        finally:
          self._executed = True
    finally:
      self._executionLock.release()
