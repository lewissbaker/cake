"""Logging Utilities.
"""

import sys
import threading

class Logger(object):
  """A class used to log tool output.
  
  Message output for each function is guaranteed to not intermingle
  with other messages output due to the use of a thread lock.
  """
  
  def __init__(self, debugComponents=[]):
    """Default construction.
    
    @param debugComponents: The components to output debug messages for.
    @type debugComponents: list of string
    """
    self.debugComponents = debugComponents
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
      
  def outputDebug(self, keyword, message):
    """Output a debug message.
    
    The message will output only if the keyword matches a component
    we are currently debugging.
    
    @param keyword: The debug keyword associated with this message.
    @type keyword: string
    @param message: The message to output.
    @type message: string
    """
    if keyword in self.debugComponents:
      with self._lock:
        sys.stdout.write(message)
        sys.stdout.flush()
