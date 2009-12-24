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
    self.__dependents = [ function ]
  
  def __call__(self):
    """Call this task.
    
    The task will run if all dependencies have completed.
    """
    self.run()
  
  def run(self):
    """Run this task.
    
    Note that the task may not actually run until all dependencies have
    completed. 
    """
    if not self.__semaphore.acquire(False):
      try:
        function = self.__dependents.pop(0)
      except KeyError:
        return # No more functions to run 
      function()
  
  def dependsOn(self, otherTask):
    """Add a dependency to this task.
    
    This task will not run until 'otherTask' task has completed.
    
    @param otherTask: The task to be dependent on.
    """
    self.__semaphore.release()    
    otherTask.addDependent(self.run)
    
  def addDependent(self, function):
    """Registers a callable function to be run when this task has completed.
    
    @param function: A callable function to run when this task has completed.
    """    
    self.__dependents.append(function)
    self.__semaphore.release()    
    self.run()  
