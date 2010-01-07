"""Cake Task Utilities
"""

import sys
import threading

NEW = "new"
WAITING_FOR_START = "waiting for start"
RUNNING = "running"
WAITING_FOR_COMPLETE = "waiting for complete"
SUCCEEDED = "succeeded"
FAILED = "failed"

class TaskError(Exception):
  pass

def _makeTask(value):
  if value is None:
    return TaskGroup(())
  elif isinstance(value, (Task, TaskGroup)):
    return value
  else:
    return TaskGroup(value)

class Task(object):
  """A task is an operation that is performed on a background thread.
  
  A task must be started before it can
  """
  
  _current = threading.local()
  
  def __init__(self, func, name=None):
    self.name = name
    self._func = func
    self._state = NEW
    self._lock = threading.Lock()
    self._completeAfterCount = 0
    self._completeAfterFailures = False
    self._callbacks = []
        
  @staticmethod
  def getCurrent():
    """Get the currently executing task.
    
    @return: The currently executing Task or None if no current task.
    """
    return getattr(Task._current, "value", None)

  @property
  def state(self):
    return self._state

  @property
  def started(self):
    """True if this task has been started.
    
    A task is started if either start(), startAfter() or cancel() has been
    called on it.
    """
    return self._state is not NEW
        
  @property
  def completed(self):
    """True if this task has finished execution or has been cancelled.
    """
    s = self._state
    return s is SUCCEEDED or s is FAILED
  
  @property
  def succeeded(self):
    """True if this task successfully finished execution.
    """
    return self._state is SUCCEEDED
  
  @property
  def failed(self):
    """True if this task terminated execution with an exception.
    """
    return self._state is FAILED
        
  def start(self):
    """Start this task now.
    
    Fails if the task has already been started or has been cancelled.
    """
    
    with self._lock:
      if self._state is not NEW:
        raise TaskError("task already started")
      self._state = RUNNING
    
    # TODO: Put call in thread-pool
    self._execute()
      
  def _execute(self):
    """Actually execute this task.
    
    This should typically be run on a background thread.
    """
    
    if self._state is not RUNNING:
      assert self._state is FAILED, "should have been cancelled"
      return
    
    callbacks = None
    
    try:
      old = self.getCurrent()
      self._current.value = self
      try:
        result = self._func()
      finally:
        self._current.value = old
        
      with self._lock:
        self._result = result
        if self._state is RUNNING:
          if not self._completeAfterCount:
            callbacks = self._callbacks
            self._callbacks = None
            if not self._completeAfterFailures:
              self._state = SUCCEEDED
            else:
              self._state = FAILED
          else:
            self._state = WAITING_FOR_COMPLETE
        else:
          assert self._state is FAILED, "should have been cancelled"
        
    except Exception, e:
      trace = sys.exc_info()[2]
      with self._lock:
        self._exception = e
        self._trace = trace
        if self._state is RUNNING:
          if not self._completeAfterCount:
            callbacks = self._callbacks
            self._callbacks = None
            self._state = FAILED
          else:
            self._state = WAITING_FOR_COMPLETE
        else:
          assert self._state is FAILED, "should have been cancelled"
        
    if callbacks:
      for callback in callbacks:
        try:
          callback()
        except Exception:
          # TODO: Warning/Error here?
          pass

  def startAfter(self, other):
    """Start this task after other tasks have completed.
    
    This task is cancelled (transition to FAILED state) if any of the
    other tasks fail.
    
    @param other: the other task or a list of other tasks to start
    after.
    @type other: L{Task} or C{list} of L{Task}
    
    @raise TaskError: If this task has already been started or
    cancelled.
    """
    other = _makeTask(other)
    
    with self._lock:
      if self._state is not NEW:
        raise TaskError("task already started")
      self._state = WAITING_FOR_START
    
    def callback():
      
      callbacks = None
      
      with self._lock:
        if self._state is WAITING_FOR_START:
          if other.failed:
            self._state = FAILED
            callbacks = self._callbacks
            self._callbacks = None
          else:
            self._state = RUNNING
        else:
          return

      if callbacks is None:
        # TODO: Put call to self._execute() on thread-pool          
        self._execute()
      else:
        for callback in callbacks:
          try:
            callback()
          except Exception:
            pass
    
    other.addCallback(callback)

  def completeAfter(self, other):
    """Make sure this task doesn't complete until other tasks have completed.
    
    @param other: The Task or list of Tasks to wait for.
    """
    other = _makeTask(other)
    
    with self._lock:
      if self.completed:
        raise TaskError("Task function has already finished executing.")
      self._completeAfterCount += 1
      
    other.addCallback(lambda: self._completeAfterCallback(other))

  def _completeAfterCallback(self, task):
    
    callbacks = None
    with self._lock:
      self._completeAfterCount -= 1
      if task.failed:
        self._completeAfterFailures = True
        
      if self._state is WAITING_FOR_COMPLETE and self._completeAfterCount == 0:
        if hasattr(self, "_result") and not self._completeAfterFailures:
          self._state = SUCCEEDED
        else:
          self._state = FAILED
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
    
    Completes the task, setting its state to FAILED.
    
    @raise TaskError: if the task has already completed.
    """
    with self._lock:
      if self.completed:
        raise TaskError("Task already completed")
      
      self._state = FAILED
      callbacks = self._callbacks
      self._callbacks = None
    
    for callback in callbacks:
      try:
        callback()
      except Exception:
        pass
  
  def addCallback(self, callback):
    """Register a callback to be run when this task is complete.
    """
    with self._lock:
      if self._callbacks is not None:
        self._callbacks.append(callback)
      else:
        try:
          callback()
        except Exception:
          pass
    
class TaskGroup:
  """A task that completes when all of a collection of tasks have completed.
  """
  
  def __init__(self, tasks):
    self._tasks = tuple(t for t in tasks if t is not None)
    self._unfinishedCount = len(self._tasks)
    
    if self._unfinishedCount:
      self._lock = threading.Lock()
      self._callbacks = []
    else:
      self._callbacks = None
      
    for task in self._tasks:
      task.addCallback(self._childFinished)

  @property
  def started(self):
    """True if all tasks have started, False otherwise.
    """
    for task in self._tasks:
      if not task.started:
        return False
    else:
      return True

  @property
  def completed(self):
    """True if this task group has completed, False otherwise.
    """
    for task in self._tasks:
      if not task.completed:
        return False 
    else:
      return True

  @property
  def failed(self):
    """True if all tasks have completed and some of them have failed,
    otherwise False.
    """
    # This is effectively calculating (completed and not succeeded)
    failed = False
    for task in self._tasks:
      s = task.state
      if s is FAILED:
        failed = True
      elif s is not SUCCEEDED:
        # Not completed yet
        return False
    else:
      return failed

  @property
  def succeeded(self):
    """True if all tasks have completed with success.
    """
    for task in self._tasks:
      if not task.succeeded:
        return False
    else:
      return True

  def cancel(self):
    """Cancel all child tasks.
    """
    for task in self._tasks:
      task.cancel()

  def addCallback(self, callback):
    """Add a callback to be called when all tasks in the task group
    have completed.
    """
    if self._callbacks is not None:
      with self._lock:
        if self._callbacks is not None:
          self._callbacks.append(callback)
          return
    
    try:
      callback()
    except Exception:
      # TODO: Log an error here - a callback failed
      pass

  def _childFinished(self):
    """Method called when a child task completes.
    """
    if self._callbacks is not None:
      with self._lock:
        self._unfinishedCount -= 1
        if self._unfinishedCount == 0:
          callbacks = self._callbacks
          self._callbacks = None
        else:
          return
      
    for callback in callbacks:
      try:
        callback()
      except Exception:
        # TODO: Log an error here - a callback failed
        pass
