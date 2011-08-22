"""Base Class and Utilities for Cake Tools.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

from cake.engine import Script
from cake.task import Task

class ToolMetaclass(type):
  """This metaclass ensures that new instance variables can only be added to
  an instance during its __init__.
  """
  
  def __init__(cls, name, bases, dct):
    super(ToolMetaclass, cls).__init__(name, bases, dct)
    
    cls._initCount = 0
    
    oldInit = cls.__init__
    def __init__(self, *args, **kwargs):
      self._initCount = self._initCount + 1
      oldInit(self, *args, **kwargs)
      self._initCount = self._initCount - 1
    cls.__init__ = __init__
      
    oldSetattr = cls.__setattr__
    def __setattr__(self, name, value):
      if not self._initCount and not hasattr(self, name):
        raise AttributeError(name)
      oldSetattr(self, name, value)
    cls.__setattr__ = __setattr__

def memoise(func):
  """Decorator that can be placed on Tool methods to memoise the result.
  
  The result cache is invalidated whenever an attribute is set on the
  instance.
  
  @param func: The function to memoise.
  @type func: function
  """
  
  undefined = object()
  def run(*args, **kwargs):
    kwargsTuple = tuple((k,v) for k, v in kwargs.iteritems())
    
    self = args[0]
    key = (func, args[1:], kwargsTuple)

    cache = self._Tool__memoise
    result = cache.get(key, undefined)
    if result is undefined:
      result = func(*args, **kwargs)
      cache[key] = result
    return result
  
  try:
    run.func_name = func.func_name
    run.func_doc = func.func_doc
  except AttributeError:
    pass
  
  return run

class Tool(object):
  """Base class for user-defined Cake tools.
  """
  
  __metaclass__ = ToolMetaclass
  
  enabled = True
  """Enabled/disable this tool.
  
  If the tool is disabled it should not produce any output files but
  it should still return the paths to those potential output files so
  other tools can use them.
  
  @type: bool
  """
  
  def __init__(self, configuration):
    self.__memoise = {}
    self.configuration = configuration
    self.engine = configuration.engine
  
  def __setattr__(self, name, value):
    if name != '_Tool__memoise' and hasattr(self, '_Tool__memoise'):
      self._clearCache()
    super(Tool, self).__setattr__(name, value)
  
  def _clearCache(self):
    """Clear the memoise cache due to some change.
    """
    self.__memoise.clear()
  
  def clone(self):
    """Return an independent clone of this tool.
    
    The default clone behaviour performs a deep copy of any builtin
    types, and a clone of any Tool-derived objects. Everything else
    will be shallow copied. You should override this method if you
    need a more sophisticated clone.
    """
    new = object.__new__(self.__class__)
    new.__dict__ = cloneTools(self.__dict__)
    return new

class FileTarget(object):
  """A class returned by tools that produce a file result.
  
  @ivar path: The path to the target file.
  @type path: string
  @ivar task: A task that completes when the target file has been written. 
  @type task: L{FileTarget}
  """
  
  def __init__(self, path, task):
    """Construct a FileTarget from a path and task.
    """
    self.path = path
    self.task = task

class AsyncResult(object):
  """Base class for asynchronous results.
  
  @ivar task: A Task that will complete when the result is available.
  @ivar result: The result of the asynchronous operation.
  """ 

class DeferredResult(AsyncResult):
  
  def __init__(self, task):
    self.task = task

  @property
  def result(self):
    return self.task.result

_undefined = object()

class ScriptResult(AsyncResult):
  """A placeholder that can be used to reference a result of another
  script that may not be available yet.
  
  The result will be available when the task has completed successfully.
  """
  
  __slots__ = ['__execute', '__script', '__name', '__default']
  
  def __init__(self, execute, name, default=_undefined):
    self.__execute = execute
    self.__script = None
    self.__name = name
    self.__default = default
    
  @property
  def script(self):
    """The Script that will be executed.
    """
    script = self.__script
    if script is None:
      script = self.__script = self.__execute()
      assert isinstance(script, Script)
    return script
    
  @property
  def task(self):
    """The script's task.
    """
    return self.script.task

  @property
  def result(self):
    assert self.task.completed
    try:
      return self.__script.getResult(self.__name)
    except KeyError:
      default = self.__default
      if default is not _undefined:
        return default
      else:
        raise

def _findAsyncResults(value):
  """Return a sequence of AsyncResult objects found in the specified value.

  Recursively searches builtin types 'list', 'tuple' and 'dict'.
  """
  if isinstance(value, AsyncResult):
    yield value
  elif isinstance(value, (list, tuple)):
    for item in value:
      for result in _findAsyncResults(item):
        yield result
  elif isinstance(value, dict):
    for k, v in value.iteritems():
      for result in _findAsyncResults(k):
        yield result
      for result in _findAsyncResults(v):
        yield result

def _resolveAsyncResults(value):
  """Return the equivalent value with all AsyncResults resolved with their
  actual results.

  Caller must ensure that all AsyncResult values have completed before calling this.
  """
  while isinstance(value, AsyncResult):
    assert value.task.completed
    value = value.result

  if isinstance(value, (tuple, list)):
    return type(value)(_resolveAsyncResults(x) for x in value)
  elif isinstance(value, dict):
    return type(value)(
      (_resolveAsyncResults(k), _resolveAsyncResults(v)) for k, v in value.iteritems()
      )
  else:
    return value

def waitForAsyncResult(func):
  """Decorator to be used with functions that need to
  wait for its argument values to become available before
  calling the function.
  
  eg.
  @waitForAsyncResult
  def someFunction(source):
    return source + '.obj'

  Calling above someFunction() with an AsyncResult will return an AsyncResult
  whose result is the return value of the function
  """
  def call(*args, **kwargs):

    asyncResults = list(_findAsyncResults(args))
    asyncResults.extend(_findAsyncResults(kwargs))

    if not asyncResults:
      return func(*args, **kwargs)

    currentScript = Script.getCurrent()
    if currentScript is not None:
      engine = currentScript.engine
      createTask = engine.createTask
    else:
      createTask = Task

    def onAsyncResultReady(asyncResult):
      """Called when an AsyncResult is ready.

      Recurse on the result to see if it contains any nested AsyncResult objects.
      If so then the task for this callback will only complete after those nested
      AsyncResult values are available.
      """
      for result in _findAsyncResults(asyncResult.result):
        waitTask = createTask(lambda r=result: onAsyncResultReady(r))
        waitTask.startAfter(result.task)

    waitTasks = []
    for asyncResult in asyncResults:
      waitTask = createTask(lambda r=asyncResult: onAsyncResultReady(r))
      waitTask.startAfter(asyncResult.task)
      waitTasks.append(waitTask)

    def run():
      newArgs = _resolveAsyncResults(args)
      newKwargs = _resolveAsyncResults(kwargs)
      return func(*newArgs, **newKwargs)
    
    runTask = createTask(run)
    runTask.startAfter(waitTasks)

    return DeferredResult(runTask)
  
  return call

@waitForAsyncResult
def flatten(value):
  """Flattens lists/tuples recursively to a single flat list of items.

  @param value: A potentially nested list of items, potentially containing
  AsyncResult values.

  @return: The flattened list or if any of the items are AsyncResult values then
  an AsyncResult value that results in the flattened items.
  """
  sequenceTypes = (list, tuple, set)
  
  def _flatten(value):
    if isinstance(value, sequenceTypes):
      for item in value:
        for x in _flatten(item):
          yield x
    else:
      yield value

  return list(_flatten(value))

def getTask(value):
  """Get the task that builds this file.
  
  @param value: The ScriptResult, FileTarget, Task or string
  representing the value.
  
  @return: 
  """
  if isinstance(value, (FileTarget, AsyncResult)):
    return value.task
  elif isinstance(value, Task):
    return value
  else:
    return None

def getTasks(files):
  """Get the set of all tasks that build these files.
  
  @param files: A list of ScriptResult, FileTarget, Task or string
  representing the sources of some operation.
  
  @return: A list of the Task that build the
  """
  tasks = []
  for f in files:
    task = getTask(f)
    if task is not None:
      tasks.append(task)
  return tasks

def getResult(value):
  """Get the result of a value that may be a ScriptResult.
  """
  while isinstance(value, AsyncResult):
    value = value.result
  return value

def getResults(values):
  """Get the results of a list of values that may be ScriptResult
  objects.
  """
  for value in values: 
    yield getResult(value)

def getPath(file):
  """Get the set of paths from the build.
  """
  file = getResult(file)
    
  if isinstance(file, FileTarget):
    return file.path
  elif isinstance(file, Task):
    return None
  else:
    return file
  
def getPaths(files):
  paths = []
  for f in files:
    path = getPath(f)
    if path is not None:
      paths.append(path)
  return paths

def cloneTools(obj):
  """Return a deep copy of any Tool-derived objects or builtin types.

  @param obj: The given object to copy.
  @return: A copy of the given object for Tool-dervied or builtin types,
  and references to the same object for user-defined types.
  """
  if isinstance(obj, Tool):
    return obj.clone()
  elif isinstance(obj, dict):
    return dict((cloneTools(k), cloneTools(v)) for k, v in obj.iteritems())
  elif isinstance(obj, (list, tuple, set)):
    return type(obj)(cloneTools(i) for i in obj)
  else:
    return obj
  
def deepCopyBuiltins(obj):
  """Returns a deep copy of only builtin types.
  
  @param obj: The given object to copy.
  @return: A copy of the given object for builtin types, and references to
  the same object for user-defined types.
  """
  if isinstance(obj, dict):
    return dict((deepCopyBuiltins(k), deepCopyBuiltins(v)) for k, v in obj.iteritems())
  elif isinstance(obj, (list, tuple, set)):
    return type(obj)(deepCopyBuiltins(i) for i in obj)
  else:
    return obj
