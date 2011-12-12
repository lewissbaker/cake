"""ThreadPool Unit Tests.
"""

import unittest
import threading
import sys

import cake.threadpool

class ThreadPoolTests(unittest.TestCase):

  def testSingleJob(self):
    result = []
    e = threading.Event()
    def job():
      result.append(None)
      e.set()
       
    threadPool = cake.threadpool.ThreadPool(numWorkers=10)
    threadPool.queueJob(job)
    e.wait()
    
    self.assertEqual(len(result), 1)
    
  def testMultipleJobs(self):
    jobCount = 50
    result = []
    s = threading.Semaphore(0)
    def job():
      result.append(None)
      s.release()
       
    threadPool = cake.threadpool.ThreadPool(numWorkers=10)
    for _ in xrange(jobCount):
      threadPool.queueJob(job)
    for _ in xrange(jobCount):
      s.acquire()
    
    self.assertEqual(len(result), 50)

if __name__ == "__main__":
  suite = unittest.TestLoader().loadTestsFromTestCase(ThreadPoolTests)
  runner = unittest.TextTestRunner(verbosity=2)
  sys.exit(not runner.run(suite).wasSuccessful())
