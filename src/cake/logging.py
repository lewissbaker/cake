import sys
import threading

class Logger(object):
  """A class used to log tool output.
  
  Message output for each function is guaranteed to not intermingle
  with other messages output due to the use of a thread lock.
  """
  
  def __init__(self):
    """Default construction.
    """
    self.errorCount = 0
    self.warningCount = 0
    self._lock = threading.Lock()
    
  def outputError(self, message):
    """Output an error message.
    
    @param message: The message to output.
    @type message: string
    """
    with self._lock:
      self.errorCount += 1
      sys.stderr.write(message)
      sys.stderr.flush()
      
  def outputWarning(self, message):
    """Output a warning message.
    
    @param message: The message to output.
    @type message: string
    """
    with self._lock:
      self.warningCount += 1
      sys.stderr.write(message)
      sys.stderr.flush()
      
  def outputInfo(self, message):
    """Output an informative message.
    
    @param message: The message to output.
    @type message: string
    """
    with self._lock:
      sys.stdout.write(message)
      sys.stdout.flush()
      
  def outputDebug(self, message):
    """Output a debug message.
    
    @param message: The message to output.
    @type message: string
    """
    with self._lock:
      sys.stdout.write(message)
      sys.stdout.flush()
