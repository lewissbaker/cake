import threading

class Task:
  """A class that calls a list of functions.
  """  
  def __init__(self, name):
    """Constructor
    """    
    self.__name = name
    self.__semaphore = threading.Semaphore(0)
    self.__lock = threading.Lock()
    self.__functions = []
  
  def __call__(self):
    """Call this task. The task will complete if all dependencies
       have been completed.
    """
    self.complete()
  
  def complete(self):
    """Complete this task. The task will complete only if all dependencies
       have been completed
    """
    if not self.__semaphore.acquire(False):
      with self.__lock:
        for f in self.__functions:
          f()
        self.__functions = None # Signal task done
  
  def dependsOn(self, other):
    """Makes sure this task completes after the 'other' task is completed.
    """
    self.__semaphore.release()    
    other.runWhenComplete(self.complete)
    
  def runWhenComplete(self, function):
    """Registers a function to be run when the task is completed.
    """    
    with self.__lock:
      if self.__functions is None:
        # Already done this task, run the function now
        function()
      else:
        # Wait for task to complete 
        self.__functions.append(function)  
