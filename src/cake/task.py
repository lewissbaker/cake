"""A module for managing tasks with dependencies.
"""

import threading

def _runDependent(function):
  """Runs a dependent function, making sure an exception does not halt the build
  of other dependents.
  
  @param function: The dependent function to run.
  """
  try:
    function()
  except Exception:
    pass # Do not halt the build of remaining dependents
    
class Task:
  """A class that wraps callable functions to allow dependencies
  between them.
  """  
  def __init__(self, function):
    """Construct a task to wrap a callable function.
    
    @param function: The callable function to run when run() is called.
    """    
    self.__semaphore = threading.Semaphore(0)
    self.__lock = threading.Lock()
    self.__function = function
    self.__dependents = []
  
  def __call__(self):
    """Call this task.
    
    The task will run if all dependencies have completed successfully.
    """
    self.run()
  
  def run(self):
    """Run this task.
    
    Note that the task may not actually run until all dependencies have
    completed. The task may not run at all if any of the dependencies
    failed.
    """
    if not self.__semaphore.acquire(False):
      # Execute the callable function
      # If the function throws an exception dependents will not be built
      self.__function()

      with self.__lock:
        self.__function = None # Signal success

      # Execute dependents
      for function in self.__dependents:
        _runDependent(function)
     
  def dependsOn(self, otherTask):
    """Add a dependency to this task.
    
    This task will not run until 'otherTask' task has completed successfully.
    
    @param otherTask: The task to be dependent on.
    """
    self.__semaphore.release()    
    otherTask.addDependent(self.run)
    
  def addDependent(self, function):
    """Registers a callable function to be run when this task has completed.
    
    @param function: A callable function to run when this task has completed.
    """    
    with self.__lock:
      if self.__function is not None:
        # Task has not completed, so wait until it has
        # Note we must hold the lock while appending in case another thread
        # is halfway through run()
        self.__dependents.append(function)
        return
        
    # Already completed successfully, run the function now
    _runDependent(function)
