"""Provides a simple thread-pool utility for managing execution of multiple jobs
in parallel on separate threads.
"""

import threading
import win32api
import time
import sys
import traceback

def getProcessorCount():
  """Return the number of processors/cores in the current system.
  
  Useful for determining the maximum parallelism of the current system.
  """
  return win32api.GetSystemInfo()[5]

class JobQueue(object):
  """A lightweight job queue class, similar to Queue.Queue.
  """
  def __init__(self):
    """Construct the job queue.
    """    
    self._jobSemaphore = threading.Semaphore(0)
    self._jobs = []
    self._submitted = 0
    self._completed = 0
    self._completedLock = threading.Lock()
      
  def get(self):
    """Get the next job from the back of the queue. Blocks until a job is
    available.
    """    
    self._jobSemaphore.acquire()
    job = self._jobs.pop()
    return lambda job=job: self._executeJob(job)
    
  def put(self, job, index=0):
    """Put a job on the queue at a given index. Defaults to putting the job
    on the front of the queue.
    """    
    self._jobs.insert(index, job)
    self._submitted += 1 # Must increase count before signalling a new job 
    self._jobSemaphore.release() # Signal a new job
 
  @property
  def outstandingJobCount(self):
    """Returns the number of jobs outstanding.
    """    
    return self._submitted - self._completed

  def _executeJob(self, job):
    """Execute a job and signal when it's complete.
    """
    try:
      job()
    finally:
      with self._completedLock:
        self._completed += 1
          
class ThreadPool(object):
  """Manages a pool of worker threads that it delegates jobs to.
  
  Usage:
  | pool = ThreadPool(numWorkers=4)
  | for i in xrange(50):
  |   pool.queueJob(lambda i=i: someFunction(i))
  | pool.waitForJobsToComplete()
  """
  class ExitThreadException(Exception):
    """An exception used to signal thread exit.
    """
    pass
  
  def __init__(self, numWorkers, maxQueueSize=0):
    """Initialise the thread pool.
    
    @param numWorkers: Initial number of worker threads to start.
    @param maxQueueSize: Maximum size of the job queue before adding new jobs
    blocks the caller.
    """
    self._maxQueueSize = maxQueueSize
    self._jobQueue = JobQueue()
    self._workers = []

    # Create the worker threads
    for _ in xrange(numWorkers):
      worker = threading.Thread(target=self._runThread)
      worker.setDaemon(True)
      worker.start()
      self._workers.append(worker)
    
  def __del__(self):
    """On shutdown we complete any currently executing jobs then exit. Jobs
    waiting on the queue may not be executed.
    """
    self.shutdown()
    
  def shutdown(self):
    """On shutdown we complete any currently executing jobs then exit. Jobs
    waiting on the queue may not be executed.
    """
    # Submit the exit job to the back of the queue
    for _ in xrange(len(self._workers)):
      self._jobQueue.put(self._exitJob, -1)

    # Wait for the threads to finish      
    for thread in self._workers:
      thread.join()
    
  def queueJob(self, callable):
    """Queue a new job to be executed by the thread pool. Blocks if
    there are already self.maxSize jobs in the queue. 
    """
    if self._maxQueueSize > 0:
      self.waitForJobsToComplete(self._maxQueueSize - 1)
      
    self._jobQueue.put(callable)
  
  def waitForJobsToComplete(self, outstandingJobCount=0):
    """Wait for all but outstandingJobCount jobs to be completed.
    
    @param outstandingJobCount: The number of outstanding jobs
    allowed to be left in the queue before returning.
    """
    while self._jobQueue.outstandingJobCount > outstandingJobCount:
      time.sleep(0.1)
  
  def _runThread(self):
    """Process jobs continuously until dismissed.
    """
    while True:
      # Get the next job
      job = self._jobQueue.get()

      # Execute the job
      try:
        job()
      except self.ExitThreadException:
        return # Exit the thread
      except Exception:
        sys.stderr.write("Uncaught exception\n")
        sys.stderr.write(traceback.format_exc())
      except:
        sys.stderr.write("------------ Hit exception\n")
        raise
      
  def _exitJob(self):
    """Thread exit job.
    """
    raise self.ExitThreadException()