"""A module for managing tasks with dependencies.
"""

import threading

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
    self.__dependents = [ function ]
  
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
      with self.__lock:
        for function in self.__dependents:
          function()
        self.__dependents = None # Signal success
  
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
      if self.__dependents is None:
        # Already completed successfully, run the function now
        function()
      else:
        # Wait for task to complete 
        self.__dependents.append(function)  
