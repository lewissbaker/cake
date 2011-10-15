"""Thread Pooling Class and Utilities.

Provides a simple thread-pool utility for managing execution of multiple jobs
in parallel on separate threads.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import threading
import os
import sys
import platform
import traceback
import atexit
import collections

import cake.system

if cake.system.isWindows():
  try:
    import win32api
    def getProcessorCount():
      """Return the number of processors/cores in the current system.
      
      Useful for determining the maximum parallelism of the current system.
      
      @return: The number of processors/cores in the current system.
      @rtype: int
      """
      return win32api.GetSystemInfo()[5]
  except ImportError:
    def getProcessorCount():
      try:
        return int(os.environ["NUMBER_OF_PROCESSORS"])
      except KeyError:
        return 1
else:
  def getProcessorCount():
    try:
      import multiprocessing
      return multiprocessing.cpu_count()
    except ImportError:
      return 1

class ThreadPool(object):
  """Manages a pool of worker threads that it delegates jobs to.
  
  Usage::
    pool = ThreadPool(numWorkers=4)
    for i in xrange(50):
      pool.queueJob(lambda i=i: someFunction(i))
  """
  def __init__(self, numWorkers):
    """Initialise the thread pool.
    
    @param numWorkers: Initial number of worker threads to start.
    @type numWorkers: int
    """
    self._jobQueue = collections.deque()
    self._workers = []
    self._wakeCondition = threading.Condition(threading.Lock())
    self._finished = False

    # Create the worker threads.
    for _ in xrange(numWorkers):
      worker = threading.Thread(target=self._runThread)
      worker.daemon = True
      worker.start()
      self._workers.append(worker)
    
    # Make sure the threads are joined before program exit.
    atexit.register(self._shutdown)
    
  def _shutdown(self):
    """Shutdown the ThreadPool.
    
    On shutdown we complete any currently executing jobs then exit. Jobs
    waiting on the queue may not be executed.
    """
    # Signal that we've finished.
    self._finished = True
    
    # Clear the queue and wake any waiting threads.
    self._wakeCondition.acquire()
    try:
      self._jobQueue.clear()
      self._wakeCondition.notifyAll()
    finally:      
      self._wakeCondition.release()      
      
    # Wait for the threads to finish.
    for thread in self._workers:
      thread.join()
  
  @property
  def numWorkers(self):
    """Returns the number of worker threads available to process jobs.
    
    @return: The number of worker threads available to process jobs.
    @rtype: int
    """
    return len(self._workers)
  
  def queueJob(self, callable, front=False):
    """Queue a new job to be executed by the thread pool.
    
    @param callable: The job to queue.
    @type callable: any callable
    
    @param front: If True then put the job at the front of the
    thread pool's job queue, otherwise append it to the end of
    the job queue.
    @type front: boolean
    """
    self._wakeCondition.acquire()
    try:
      if not self._finished: # Don't add jobs if we've shutdown.
        wasEmpty = len(self._jobQueue) == 0
        if front:
          self._jobQueue.appendleft(callable)
        else:
          self._jobQueue.append(callable)
        if wasEmpty:
          self._wakeCondition.notifyAll()
    finally:      
      self._wakeCondition.release()
      
  def _runThread(self):
    """Process jobs continuously until dismissed.
    """
    while not self._finished:
      self._wakeCondition.acquire()
      try:
        try:
          job = self._jobQueue.popleft()
        except IndexError:
          self._wakeCondition.wait() # No more jobs. Sleep until another is pushed.
          continue
      finally:
        self._wakeCondition.release()
            
      try:
        job()
      except Exception:
        sys.stderr.write("Uncaught Exception:\n")
        sys.stderr.write(traceback.format_exc())
