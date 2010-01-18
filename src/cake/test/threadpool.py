import unittest
from cake.threadpool import ThreadPool

class ThreadPoolTests(unittest.TestCase):

  def testSingleJob(self):
    result = []
    def job():
      result.append(None)
       
    threadPool = ThreadPool(numWorkers=10)
    threadPool.queueJob(job)
    threadPool.waitForJobsToComplete()
    threadPool.shutdown()
    
    self.assertEqual(len(result), 1)
    
  def testMultipleJobs(self):
    result = []
    def job():
      result.append(None)
       
    threadPool = ThreadPool(numWorkers=10)
    for _ in xrange(50):
      threadPool.queueJob(job)
    threadPool.waitForJobsToComplete()
    threadPool.shutdown()
    
    self.assertEqual(len(result), 50)

if __name__ == "__main__":
  import sys;sys.argv = ['', 'ThreadPoolTests']
  unittest.main()