"""Task Utilities.
"""

import sys
import threading

from cake.threadpool import ThreadPool, getProcessorCount

_threadPool = ThreadPool(numWorkers=getProcessorCount())

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
    return value

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
    self._parent = Task.getCurrent()
    self._state = Task.State.NEW
    self._lock = threading.Lock()
    self._startAfterCount = 0
    self._startAfterFailures = False
    self._completeAfterCount = 0
    self._completeAfterFailures = False
    self._callbacks = []

    if self._parent is not None:
      self._parent.completeAfter(self)

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
    """
    return self._parent
  
  @property
  def started(self):
    """True if this task has been started.
    
    A task is started if start(), startAfter() or cancel() has been
    called on it.
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
        
  def start(self):
    """Start this task now.
    
    @raise TaskError: If this task has already been started or
    cancelled.
    """
    self.startAfter(None)

  def startAfter(self, other):
    """Start this task after other tasks have completed.
    
    This task is cancelled (transition to Task.State.FAILED state) if any of the
    other tasks fail.
    
    @param other: The task or a list of tasks to start after.
    @type other: L{Task} or C{list}(L{Task})
    
    @raise TaskError: If this task has already been started or
    cancelled.
    """
    otherTasks = _makeTasks(other)
    
    with self._lock:
      if self._state is not Task.State.NEW:
        raise TaskError("task already started")
      self._state = Task.State.WAITING_FOR_START
      self._startAfterCount = len(otherTasks) + 1
    
    for t in otherTasks:
      t.addCallback(lambda t=t: self._startAfterCallback(t))
      
    self._startAfterCallback(self)

  def _startAfterCallback(self, task):
    """Callback that is called by each task we must start after.
    """    
    callbacks = None
    
    with self._lock:
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

    if callbacks is None:
      _threadPool.queueJob(self._execute, front=True)          
    else:
      for callback in callbacks:
        try:
          callback()
        except Exception:
          pass
              
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
        
      with self._lock:
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
        
    except Exception, e:
      trace = sys.exc_info()[2]
      with self._lock:
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
     
    if callbacks:
      for callback in callbacks:
        try:
          callback()
        except Exception:
          # TODO: Warning/Error here?
          pass

  def completeAfter(self, other):
    """Make sure this task doesn't complete until other tasks have completed.
    
    @param other: The Task or list of Tasks to wait for.
    @type other: L{Task} or C{list}(L{Task})
    
    @raise TaskError: If this task has already finished executing.
    """
    otherTasks = _makeTasks(other)

    with self._lock:
      if self.completed:
        raise TaskError("Task function has already finished executing.")
      self._completeAfterCount += len(otherTasks)
      
    for t in otherTasks:      
      t.addCallback(lambda t=t: self._completeAfterCallback(t))

  def _completeAfterCallback(self, task):
    """Callback that is called by each task we must complete after.
    """
    callbacks = None
    
    with self._lock:
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
        
    if callbacks:
      for callback in callbacks:
        try:
          callback()
        except Exception:
          # TODO: Log failed callback error
          pass

  def cancel(self):
    """Cancel this task if it hasn't already started.
    
    Completes the task, setting its state to Task.State.FAILED.
    
    @raise TaskError: if the task has already completed.
    """
    with self._lock:
      if self.completed:
        raise TaskError("Task already completed")
      
      self._state = Task.State.FAILED
      callbacks = self._callbacks
      self._callbacks = None
    
    for callback in callbacks:
      try:
        callback()
      except Exception:
        pass
  
  def addCallback(self, callback):
    """Register a callback to be run when this task is complete.
    
    @param callback: The callback to add.
    @type callback: any callable
    """
    with self._lock:
      if self._callbacks is not None:
        self._callbacks.append(callback)
      else:
        try:
          callback()
        except Exception:
          pass
