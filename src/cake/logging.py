import sys
import threading

class Logger(object):
  
  def __init__(self):
    self.errorCount = 0
    self.warningCount = 0
    self._lock = threading.Lock()
    
  def outputError(self, message):
    with self._lock:
      self.errorCount += 1
      sys.stderr.write(message)
      sys.stderr.flush()
      
  def outputWarning(self, message):
    with self._lock:
      self.warningCount += 1
      sys.stderr.write(message)
      sys.stderr.flush()
      
  def outputInfo(self, message):
    with self._lock:
      sys.stdout.write(message)
      sys.stdout.flush()
      
  def outputDebug(self, message):
    with self._lock:
      sys.stdout.write(message)
      sys.stdout.flush()
