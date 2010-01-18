import unittest
import threading

from cake.threadpool import ThreadPool

class ThreadPoolTests(unittest.TestCase):

  def testSingleJob(self):
    result = []
    e = threading.Event()
    def job():
      result.append(None)
      e.set()
       
    threadPool = ThreadPool(numWorkers=10)
    threadPool.queueJob(job)
    e.wait()
    threadPool.shutdown()
    
    self.assertEqual(len(result), 1)
    
  def testMultipleJobs(self):
    jobCount = 50
    result = []
    s = threading.Semaphore(0)
    def job():
      result.append(None)
      s.release()
       
    threadPool = ThreadPool(numWorkers=10)
    for _ in xrange(jobCount):
      threadPool.queueJob(job)
    for _ in xrange(jobCount):
      s.acquire()
    threadPool.shutdown()
    
    self.assertEqual(len(result), 50)

if __name__ == "__main__":
  import sys;sys.argv = ['', 'ThreadPoolTests']
  unittest.main()