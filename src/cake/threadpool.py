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
    
    @return: The number of processors/cores in the current system.
    @rtype: int
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
    """Get the next job from the front of the queue.
    
    Blocks until a job is available.
    """
    self._jobSemaphore.acquire() # Wait for next job
    return self._jobs.pop(0)

  def putBack(self, job):
    """Put a job on the end of the queue.
    """
    self._jobs.append(job)
    self._jobSemaphore.release() # Signal a new job
    
  def putFront(self, job):
    """Put a job on the front of the queue.
    """
    self._jobs.insert(0, job)
    self._jobSemaphore.release() # Signal a new job 

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
    self._jobQueue = _JobQueue()
    self._workers = []

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
      self._jobQueue.putFront(self._EXIT_JOB)

    # Wait for the threads to finish
    for thread in self._workers:
      thread.join()

    # Clear any references
    self._jobQueue = _JobQueue()
    self._workers[:] = []
    
  def queueJob(self, callable, front=False):
    """Queue a new job to be executed by the thread pool.
    
    @param callable: The job to queue.
    @type callable: any callable
    
    @param front: If True then put the job at the front of the
    thread pool's job queue, otherwise append it to the end of
    the job queue.
    @type front: boolean
    """
    if front:
      self._jobQueue.putFront(callable)
    else:
      self._jobQueue.putBack(callable)
  
  def _runThread(self):
    """Process jobs continuously until dismissed.
    """
    while True:
      job = self._jobQueue.get()
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
