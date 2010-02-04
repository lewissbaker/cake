"""Thread Pooling Class and Utilities.

Provides a simple thread-pool utility for managing execution of multiple jobs
in parallel on separate threads.
"""

import threading
import sys
import platform
import traceback
import atexit

if platform.system() == 'Windows':
  import win32api
  def getProcessorCount():
    """Return the number of processors/cores in the current system.
    
    Useful for determining the maximum parallelism of the current system.
    """
    return win32api.GetSystemInfo()[5]
else:
  def getProcessorCount():
    return 1

class _JobQueue(object):
  """A lightweight job queue class, similar to Queue.Queue.
  """
  def __init__(self):
    """Construct the job queue.
    """    
    self._jobSemaphore = threading.Semaphore(0)
    self._jobs = []

  def get(self):
    """Get the next job from the back of the queue. Blocks until a job is
    available.
    """
    self._jobSemaphore.acquire() # Wait for next job
    return self._jobs.pop()

  def put(self, job, index=0):
    """Put a job on the queue at a given index. Defaults to putting the job
    on the front of the queue.
    """
    self._jobs.insert(index, job)
    self._jobSemaphore.release() # Signal a new job

class ThreadPool(object):
  """Manages a pool of worker threads that it delegates jobs to.
  
  Usage:
  | pool = ThreadPool(numWorkers=4)
  | for i in xrange(50):
  |   pool.queueJob(lambda i=i: someFunction(i))
  """
  EXIT_JOB = "exit job"
  
  def __init__(self, numWorkers):
    """Initialise the thread pool.
    
    @param numWorkers: Initial number of worker threads to start.
    """
    self._jobQueue = _JobQueue()
    self._workers = []

    # Create the worker threads
    for _ in xrange(numWorkers):
      worker = threading.Thread(target=self._runThread)
      worker.start()
      self._workers.append(worker)
    
    # Make sure the threads are joined before program exit
    atexit.register(self.shutdown)
    
  def shutdown(self):
    """On shutdown we complete any currently executing jobs then exit. Jobs
    waiting on the queue may not be executed.
    """
    # Submit the exit job directly to the back of the queue
    for _ in xrange(len(self._workers)):
      self._jobQueue.put(self.EXIT_JOB, -1)

    # Wait for the threads to finish      
    for thread in self._workers:
      thread.join()

    # Clear any references
    self._jobQueue = _JobQueue()
    self._workers[:] = []
    
  def queueJob(self, callable):
    """Queue a new job to be executed by the thread pool.
    
    @param callable: Job to queue
    @type callable: any callable
    """
    self._jobQueue.put(callable)
  
  def _runThread(self):
    """Process jobs continuously until dismissed.
    """
    while True:
      job = self._jobQueue.get()
      if job is self.EXIT_JOB:
        break

      try:
        job()
      except Exception:
        sys.stderr.write("Uncaught Exception:\n")
        sys.stderr.write(traceback.format_exc())
        