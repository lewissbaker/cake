"""Defines some utilities for writing functions that return asynchronously.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

from cake.task import Task

class AsyncResult(object):
  """Base class for asynchronous results.
  
  @ivar task: A Task that will complete when the result is available.
  @ivar result: The result of the asynchronous operation.
  """

class DeferredResult(AsyncResult):
  """An AsyncResult where the result is the return value of the task's function.
  """
  
  def __init__(self, task):
    self.task = task

  @property
  def result(self):
    return self.task.result

def _findAsyncResults(value):
  """Return a sequence of AsyncResult objects found in the specified value.

  Recursively searches builtin types 'list', 'tuple', 'set', 'frozenset' and 'dict'.
  """
  if isinstance(value, AsyncResult):
    yield value
  elif isinstance(value, (list, tuple, set, frozenset)):
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

  if isinstance(value, (tuple, list, set, frozenset)):
    return type(value)(_resolveAsyncResults(x) for x in value)
  elif isinstance(value, dict):
    return type(value)(
      (_resolveAsyncResults(k), _resolveAsyncResults(v)) for k, v in value.iteritems()
      )
  else:
    return value

def _getWaitTasks(asyncResults, taskFactory):
  waitTasks = []
  for asyncResult in asyncResults:
    task = asyncResult.task
    if task:
      waitTask = taskFactory(lambda r=asyncResult: _onAsyncResultReady(r, taskFactory))
      waitTask.startAfter(task)
      waitTasks.append(waitTask)
  return waitTasks

def _onAsyncResultReady(asyncResult, taskFactory):
  """Called when an AsyncResult is ready.

  Recurse on the result to see if it contains any nested AsyncResult objects.
  If so then the task for this callback will only complete after those nested
  AsyncResult values are available.
  """
  waitTasks = _getWaitTasks(_findAsyncResults(asyncResult.result), taskFactory)
  if waitTasks:
    parentTask = Task.getCurrent()
    if parentTask:
      parentTask.completeAfter(waitTasks)

def _getTaskFactory():
  # If called from within a Script we use Engine.createTask
  # so that the Script.getCurrent() context is flowed across
  # sub-tasks from the creator of the task.
  from cake.script import Script
  currentScript = Script.getCurrent()
  if currentScript is not None:
    return currentScript.engine.createTask
  else:
    return Task

def waitForAsyncResult(func):
  """Decorator to be used with functions that need to
  wait for its argument values to become available before
  calling the function.
  
  eg.
  @waitForAsyncResult
  def someFunction(source):
    return source + '.obj'

  Calling above someFunction() with an AsyncResult will return an AsyncResult
  whose result is the return value of the function applied to the unwrapped
  AsyncResult results.
  """
  def call(*args, **kwargs):

    asyncResults = list(_findAsyncResults(args))
    asyncResults.extend(_findAsyncResults(kwargs))

    if not asyncResults:
      return func(*args, **kwargs)

    def run():
      newArgs = _resolveAsyncResults(args)
      newKwargs = _resolveAsyncResults(kwargs)
      return func(*newArgs, **newKwargs)
    
    taskFactory = _getTaskFactory()

    runTask = taskFactory(run)
    runTask.startAfter(_getWaitTasks(asyncResults, taskFactory))

    parentTask = Task.getCurrent()
    if parentTask:
      parentTask.completeAfter(runTask)

    return DeferredResult(runTask)
  
  return call

def getResult(value):
  """Get the result of a value that may be an AsyncResult.
  """
  while isinstance(value, AsyncResult):
    value = value.result
  return value

def getResults(values):
  """Get the results of a list of values that may be an AsyncResult
  objects.
  """
  for value in values: 
    yield getResult(value)

@waitForAsyncResult
def flatten(value):
  """Flattens lists/tuples/sets recursively to a single flat list of items.

  @param value: A potentially nested list of items, potentially containing
  AsyncResult values.

  @return: The flattened list or if any of the items are AsyncResult values then
  an AsyncResult value that results in the flattened items.
  """
  sequenceTypes = (list, tuple, set, frozenset)
  
  def _flatten(value):
    if isinstance(value, sequenceTypes):
      for item in value:
        for x in _flatten(item):
          yield x
    else:
      yield value

  return list(_flatten(value))
