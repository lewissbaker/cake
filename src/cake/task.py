"""Task Utilities.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import sys
import threading

_threadPool = None
_threadPoolLock = threading.Lock()

def setThreadPool(threadPool):
  """Set the default thread pool to use for executing new tasks.

  @param threadPool: The new default thread pool.

  @return: The previous default thread pool. This is intially None.
  """

  global _threadPool, _threadPoolLock

  _threadPoolLock.acquire()
  try:
    oldThreadPool = _threadPool
    _threadPool = threadPool
  finally:
    _threadPoolLock.release()

  return oldThreadPool

def getDefaultThreadPool():
  """Get the current default thread pool for new tasks.

  If no default thread pool exists then one will be created automatically.
  """

  global _threadPool, _threadPoolLock
  if _threadPool is None:
    import cake.threadpool
    processorCount = cake.threadpool.getProcessorCount()
    _threadPoolLock.acquire()
    try:
      if _threadPool is None:
        _threadPool = cake.threadpool.ThreadPool(numWorkers=processorCount)
    finally:
      _threadPoolLock.release()
  return _threadPool
  
class TaskError(Exception):
  """An exception type raised by the L{Task} class.
  """
  pass
  
def _makeTasks(value):
  if value is None:
    return []
  elif isinstance(value, Task):
    return [value]
  else:
    return list(value)

class Task(object):
  """An operation that is performed on a background thread.
  """

  class State(object):
    """A class that represents the state of a L{Task}.
    """
    NEW = "new"
    """The task is in an uninitialised state."""
    WAITING_FOR_START = "waiting for start"
    """The task is waiting to be started."""
    RUNNING = "running"
    """The task is running."""
    WAITING_FOR_COMPLETE = "waiting for complete"
    """The task is waiting to complete."""
    SUCCEEDED = "succeeded"
    """The task has succeeded."""
    FAILED = "failed"
    """The task has failed."""
    
  _current = threading.local()
  
  def __init__(self, func=None):
    """Construct a task given a function.
    
    @param func: The function this task should run.
    @type func: any callable
    """
    self._func = func
    self._immediate = None
    self._threadPool = None
    self._required = False
    self._parent = Task.getCurrent()
    self._state = Task.State.NEW
    self._lock = threading.Lock()
    self._startAfterCount = 0
    self._startAfterFailures = False
    self._startAfterDependencies = None
    self._completeAfterCount = 0
    self._completeAfterFailures = False
    self._completeAfterDependencies = None
    self._callbacks = []

  @staticmethod
  def getCurrent():
    """Get the currently executing task.
    
    @return: The currently executing Task or None if no current task.
    @rtype: Task or None
    """
    return getattr(Task._current, "value", None)

  @property
  def state(self):
    """Get the state of this task.
    """
    return self._state
  
  @property
  def parent(self):
    """Get the parent of this task.

    The parent task is the task that created this task.
    """
    return self._parent
  
  @property
  def required(self):
    """True if this task is required to execute, False if it
    has not yet been required to execute.
    """
    return self._required

  @property
  def started(self):
    """True if this task has been started.
    
    A task is started if start(), startAfter(), lazyStart(),
    lazyStartAfter() or cancel() has been called on it.
    """
    return self._state is not Task.State.NEW

  @property
  def completed(self):
    """True if this task has finished execution or has been cancelled.
    """
    s = self._state
    return s is Task.State.SUCCEEDED or s is Task.State.FAILED
  
  @property
  def succeeded(self):
    """True if this task successfully finished execution.
    """
    return self._state is Task.State.SUCCEEDED
  
  @property
  def failed(self):
    """True if this task failed or was cancelled.
    """
    return self._state is Task.State.FAILED
        
  @property
  def result(self):
    """If the task has completed successfully then holds the
    return value of the task, otherwise raises AttributeError.
    """
    if self.succeeded:
      task = self
      while isinstance(task._result, Task):
        task = task._result
      return task._result
    else:
      raise AttributeError("result only available on successful tasks")

  def lazyStart(self, threadPool=None):
    """Start this task only if required as a dependency of another 'required' task.

    A 'required' task is a task that is started eagerly using L{start()} or L{startAfter()}
    or a task that is a dependency of a 'required' task.

    If no other required tasks have this task as a dependency then this task will never
    be executed. i.e. it is a lazy task.
    """
    self._start(other=None, immediate=False, required=False, threadPool=threadPool)

  def lazyStartAfter(self, other, threadPool=None):
    """Start this task only if required as a dependency of another 'required' task.

    But do not start this task until the 'other' tasks have completed.
    If any of the other tasks complete with failure then this task will complete
    with failure without being executed.
    """
    self._start(other=other, immediate=False, required=False, threadPool=threadPool)

  def start(self, immediate=False, threadPool=None):
    """Start this task now.
    
    @param immediate: If True the task is pushed ahead of any other (waiting)
    tasks on the task queue.
    @type immediate: bool

    @param threadPool: If specified then the task will be queued up to be
    executed on the specified thread-pool. If not specified then the task
    will be queued for execution on the default thread-pool.
    @type threadPool: L{ThreadPool} or C{None}
        
    @raise TaskError: If this task has already been started or
    cancelled.
    """
    self._start(other=None, immediate=immediate, required=True, threadPool=threadPool)

  def startAfter(self, other, immediate=False, threadPool=None):
    """Start this task after other tasks have completed.
    
    This task is cancelled (transition to Task.State.FAILED state) if any of the
    other tasks fail.
    
    @param other: The task or a list of tasks to start after.
    @type other: L{Task} or C{list}(L{Task})

    @param immediate: If True the task is pushed ahead of any other (waiting)
    tasks on the task queue.
    @type immediate: bool

    @param threadPool: An optional thread pool to start this task on.
    If not specified then the task is queued to the default thread-pool.
    @type threadPool: L{ThreadPool} or None
    
    @raise TaskError: If this task has already been started or
    cancelled.
    """
    self._start(other=other, immediate=immediate, required=True, threadPool=threadPool)

  def _start(self, other, immediate, required, threadPool):
    immediate = bool(immediate)
    required = bool(required)
    otherTasks = _makeTasks(other)
    if threadPool is None:
      threadPool = getDefaultThreadPool()

    self._lock.acquire()
    try:
      if self._state is not Task.State.NEW:
        raise TaskError("task already started")
      self._state = Task.State.WAITING_FOR_START
      self._startAfterCount = len(otherTasks) + 1
      self._immediate = immediate
      self._threadPool = threadPool
      if required:
        self._required = True
      else:
        required = self._required
      
      if required:
        completeAfterDependencies = self._completeAfterDependencies
        self._completeAfterDependencies = None
      else:
        self._startAfterDependencies = otherTasks
    finally:
      self._lock.release()
    
    if required:
      for t in otherTasks:
        t._require()
        t.addCallback(lambda t=t: self._startAfterCallback(t))
      
      if completeAfterDependencies:
        for t in completeAfterDependencies:
          t._require()
          t.addCallback(lambda t=t: self._completeAfterCallback(t))

      self._startAfterCallback(self)

  def _require(self):
    """Flag this task as required.

    If this task was started with a call to lazyStart/lazyStartAfter()
    and has not yet been required by some other Task then this will
    cause this task and all of it's dependencies to become required.
    """

    if self.required:
      return
    
    startAfterDependencies = None
    completeAfterDependencies = None

    self._lock.acquire()
    try:
      alreadyRequired = self.required
      if not alreadyRequired:
        startAfterDependencies = self._startAfterDependencies
        completeAfterDependencies = self._completeAfterDependencies
        self._startAfterDependencies = None
        self._completeAfterDependencies = None
        self._required = True
    finally:
      self._lock.release()

    if not alreadyRequired:
      if startAfterDependencies:
        for t in startAfterDependencies:
          t._require()
          t.addCallback(lambda t=t: self._startAfterCallback(t))

      if completeAfterDependencies:
        for t in completeAfterDependencies:
          t._require()
          t.addCallback(lambda t=t: self._completeAfterCallback(t))

      self._startAfterCallback(self)

  def _startAfterCallback(self, task):
    """Callback that is called by each task we must start after.
    """
    callbacks = None
    
    self._lock.acquire()
    try:
      # If one task fails we should fail too
      if task.failed:
        self._startAfterFailures = True

      # Wait for all other tasks to complete 
      self._startAfterCount -= 1
      if self._startAfterCount > 0:
        return
      
      # Someone may have eg. cancelled us already
      if self._state is not Task.State.WAITING_FOR_START:
        return

      if self._startAfterFailures:
        self._state = Task.State.FAILED
        callbacks = self._callbacks
        self._callbacks = None
      else:
        self._state = Task.State.RUNNING
    finally:
      self._lock.release()

    if callbacks is None:
      # Task is ready to start executing, queue to thread-pool.
      self._threadPool.queueJob(self._execute, front=self._immediate)          
    else:
      # Task was cancelled, call callbacks now
      for callback in callbacks:
        callback()
              
  def _execute(self):
    """Actually execute this task.
    
    This should typically be run on a background thread.
    """
    if self._state is not Task.State.RUNNING:
      assert self._state is Task.State.FAILED, "should have been cancelled"
      return
    
    callbacks = None
    
    try:
      old = self.getCurrent()
      self._current.value = self
      # Don't hold onto the func after it has been executed so it can
      # be garbage collected.
      func = self._func
      self._func = None
      try:
        if func is not None:
          result = func()
        else:
          result = None
      finally:
        self._current.value = old

      # If the result of the task was another task
      # then our result will be the same as that other
      # task's result. So make sure we don't complete
      # before the other task does.
      if isinstance(result, Task):
        self.completeAfter(result)
        
      self._lock.acquire()
      try:
        self._result = result
        if self._state is Task.State.RUNNING:
          if not self._completeAfterCount:
            callbacks = self._callbacks
            self._callbacks = None
            if not self._completeAfterFailures:
              self._state = Task.State.SUCCEEDED
            else:
              self._state = Task.State.FAILED
          else:
            self._state = Task.State.WAITING_FOR_COMPLETE
        else:
          assert self._state is Task.State.FAILED, "should have been cancelled"
      finally:
        self._lock.release()
        
    except Exception, e:
      trace = sys.exc_info()[2]
      self._lock.acquire()
      try:
        self._exception = e
        self._trace = trace
        if self._state is Task.State.RUNNING:
          if not self._completeAfterCount:
            callbacks = self._callbacks
            self._callbacks = None
            self._state = Task.State.FAILED
          else:
            self._state = Task.State.WAITING_FOR_COMPLETE
        else:
          assert self._state is Task.State.FAILED, "should have been cancelled"
      finally:
        self._lock.release()
     
    if callbacks:
      for callback in callbacks:
        callback()

  def completeAfter(self, other):
    """Make sure this task doesn't complete until other tasks have completed.
    
    @param other: The Task or list of Tasks to wait for.
    @type other: L{Task} or C{list}(L{Task})
    
    @raise TaskError: If this task has already finished executing.
    """
    otherTasks = _makeTasks(other)

    self._lock.acquire()
    try:
      if self.completed:
        raise TaskError("Task function has already finished executing.")

      required = self.required
      if not required:
        # This task not yet required
        # Record it's dependencies in case it later becomes required
        dependencies = self._completeAfterDependencies
        if dependencies is None:
          self._completeAfterDependencies = otherTasks
        else:
          dependencies.extend(otherTasks)

      self._completeAfterCount += len(otherTasks)
    finally:
      self._lock.release()

    if required:
      # This task was already required so we'll require the new
      # dependencies immediately.
      for t in otherTasks:
        t._require()
        t.addCallback(lambda t=t: self._completeAfterCallback(t))

  def _completeAfterCallback(self, task):
    """Callback that is called by each task we must complete after.
    """
    callbacks = None
    
    self._lock.acquire()
    try:
      self._completeAfterCount -= 1
      if task.failed:
        self._completeAfterFailures = True
        
      if self._state is Task.State.WAITING_FOR_COMPLETE and self._completeAfterCount == 0:
        if hasattr(self, "_result") and not self._completeAfterFailures:
          self._state = Task.State.SUCCEEDED
        else:
          self._state = Task.State.FAILED
        callbacks = self._callbacks
        self._callbacks = None
    finally:
      self._lock.release()
        
    if callbacks:
      for callback in callbacks:
        callback()

  def cancel(self):
    """Cancel this task if it hasn't already started.
    
    Completes the task, setting its state to Task.State.FAILED.
    
    @raise TaskError: if the task has already completed.
    """
    self._lock.acquire()
    try:
      if self.completed:
        raise TaskError("Task already completed")
      
      self._state = Task.State.FAILED
      callbacks = self._callbacks
      self._callbacks = None
    finally:
      self._lock.release()
    
    for callback in callbacks:
      callback()
  
  def addCallback(self, callback):
    """Register a callback to be run when this task is complete.
    
    @param callback: The callback to add.
    @type callback: any callable
    """
    if not self.completed:
      self._lock.acquire()
      try:
        callbacks = self._callbacks
        if callbacks is not None:
          # Task is not yet complete, queue up callback to execute later.
          callbacks.append(callback)
          return
      finally:
        self._lock.release()

    callback()
