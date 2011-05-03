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
  _EXIT_JOB = "exit job"
    
  def __init__(self, numWorkers):
    """Initialise the thread pool.
    
    @param numWorkers: Initial number of worker threads to start.
    @type numWorkers: int
    """
    self._jobQueue = collections.deque()
    self._workers = []
    self._wakeCondition = threading.Condition(threading.Lock())

    # Create the worker threads
    for _ in xrange(numWorkers):
      worker = threading.Thread(target=self._runThread)
      worker.daemon = True
      worker.start()
      self._workers.append(worker)
    
    # Make sure the threads are joined before program exit
    atexit.register(self._shutdown)
    
  def _shutdown(self):
    """Shutdown the ThreadPool.
    
    On shutdown we complete any currently executing jobs then exit. Jobs
    waiting on the queue may not be executed.
    """
    # Submit the exit job directly to the back of the queue
    for _ in xrange(len(self._workers)):
      self.queueJob(self._EXIT_JOB, True)
    
    # Wait for the threads to finish
    for thread in self._workers:
      thread.join()
    
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
    while True:
      self._wakeCondition.acquire()
      try:
        try:
          job = self._jobQueue.popleft()
        except IndexError:
          self._wakeCondition.wait()
          continue
      finally:
        self._wakeCondition.release()
      
      if job is self._EXIT_JOB:
        break
            
      try:
        job()
      except Exception:
        sys.stderr.write("Uncaught Exception:\n")
        sys.stderr.write(traceback.format_exc())

class DummyThreadPool(object):
  """A class like ThreadPool that performs all operations in
  the one thread.
  """
  
  def __init__(self):
    self._queue = []
    self._quit = False
  
  def queueJob(self, callable, front=False):
    """Add a job to the queue.
    
    @param callable: A job to queue up. Must be callable with
    no arguments.
    @param front: If true then the job is put on the front of
    the queue, otherwise it is put on the end of the queue.
    """
    if front:
      self._queue.insert(0, callable)
    else:
      self._queue.append(callable)

  def run(self):
    """Start processing jobs in the queue one at a time
    in the calling thread until either no jobs are left
    or someone calls quit().
    """
    while self._queue and not self._quit:
      job = self._queue.pop(0)
      try:
        job()
      except Exception:
        sys.stderr.write("Uncaught Exception:\n")
        sys.stderr.write(traceback.format_exc())
        
    self._quit = False
    
  def quit(self):
    """Causes the call to run() to quit processing jobs and return.
    """
    self._quit = True
