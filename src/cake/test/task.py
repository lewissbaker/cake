"""Task Unit Tests.
"""

import unittest
import threading
import sys

import cake.task

class TaskTests(unittest.TestCase):

  def testTaskFunctionExecutedExactlyOnce(self):
    result = []
    def f():
      result.append(None)
      
    e = threading.Event()
    t = cake.task.Task(f)
    t.addCallback(e.set)
    
    self.assertFalse(t.started)
    self.assertFalse(t.completed)
    self.assertFalse(t.succeeded)
    self.assertFalse(t.failed)
    
    t.start()
    
    self.assertTrue(t.started)
    
    e.wait(0.5)

    self.assertTrue(t.completed)
    self.assertTrue(t.started)
    self.assertTrue(t.succeeded)
    self.assertFalse(t.failed)
    self.assertEqual(len(result), 1)

  def testFailingTask(self):
    def f():
      raise RuntimeError()

    e = threading.Event()
    t = cake.task.Task(f)
    t.addCallback(e.set)

    t.start()
    
    e.wait(0.5)
    
    self.assertTrue(t.completed)
    self.assertTrue(t.started)
    self.assertFalse(t.succeeded)
    self.assertTrue(t.failed)
      
  def testStartAfter(self):
    result = []
    def a():
      result.append("a")
    def b():
      result.append("b")
      
    eb = threading.Event()
    ta = cake.task.Task(a)
    tb = cake.task.Task(b)
    tb.addCallback(eb.set)
        
    tb.startAfter(ta)
    
    self.assertTrue(tb.started)
    self.assertFalse(ta.started)
    
    ta.start()
    
    self.assertTrue(ta.started)
    
    eb.wait(0.5)
    
    self.assertTrue(tb.completed)
    self.assertTrue(ta.succeeded)
    self.assertTrue(tb.started)
    self.assertTrue(tb.succeeded)
    self.assertEqual(result, ["a", "b"])
      
  def testStartAfterCompletedTask(self):
    result = []
    def a():
      result.append("a")
    def b():
      result.append("b")
      
    ea = threading.Event()
    eb = threading.Event()
    ta = cake.task.Task(a)
    tb = cake.task.Task(b)
    ta.addCallback(ea.set)
    tb.addCallback(eb.set)
        
    ta.start()
    
    self.assertTrue(ta.started)
    
    ea.wait(0.5)
    
    self.assertTrue(ta.completed)
    
    tb.startAfter(ta)
    
    self.assertTrue(tb.started)

    eb.wait(0.5)
    
    self.assertTrue(tb.completed)
    self.assertTrue(ta.succeeded)
    self.assertTrue(tb.started)
    self.assertTrue(tb.succeeded)
    self.assertEqual(result, ["a", "b"])
    
  def testStartAfterFailedTask(self):
    result = []
    def a():
      result.append("a")
      raise RuntimeError()
    def b():
      result.append("b")
    
    eb = threading.Event()
    ta = cake.task.Task(a)
    tb = cake.task.Task(b)
    tb.addCallback(eb.set)
    tb.startAfter(ta)
    
    self.assertTrue(tb.started)
    self.assertFalse(ta.started)
    
    ta.start()
    
    self.assertTrue(ta.started)
    
    eb.wait(0.5)
    
    self.assertTrue(tb.completed)
    self.assertTrue(tb.failed)
    self.assertTrue(tb.started)
    self.assertTrue(tb.failed)
    self.assertEqual(result, ["a"])
      
  def testCompleteAfter(self):
    
    result = []
    
    def a():
      result.append("a")
      def b():
        result.append("b")
      t = cake.task.Task(b)
      t.start()
      cake.task.Task.getCurrent().completeAfter(t)
      
    def c():
      result.append("c")

    ec = threading.Event()
    ta = cake.task.Task(a)
    tc = cake.task.Task(c)
    tc.addCallback(ec.set)
    tc.startAfter(ta)
    ta.start()
    
    ec.wait(0.5)
    
    self.assertTrue(tc.completed)
    self.assertEqual(result, ["a", "b", "c"])
    
  def testStartAfterMultiple(self):
    
    result = []
    def a():
      result.append("a")
    def b():
      result.append("b")
    def c():
      result.append("c")
      
    ec = threading.Event()
    ta = cake.task.Task(a)
    tb = cake.task.Task(b)
    tc = cake.task.Task(c)
    tc.addCallback(ec.set)
    tc.startAfter([ta, tb])
    
    self.assertTrue(tc.started)
    self.assertFalse(ta.started)
    self.assertFalse(tb.started)
    
    ta.start()
    
    self.assertFalse(tc.completed)
    
    tb.start()
    
    ec.wait(0.5)

    self.assertTrue(tc.completed)
    self.assertTrue(ta.succeeded)
    self.assertTrue(tb.succeeded)
    self.assertTrue(tc.succeeded)
    self.assertTrue(result in [["a", "b", "c"], ["b", "a", "c"]])
    
  def testStartAfterMultipleSomeFail(self):
    
    result = []
    def a():
      raise Exception()
    def b():
      result.append("b")
    def c():
      result.append("c")
      
    eb = threading.Event()
    ec = threading.Event()      
    ta = cake.task.Task(a)
    tb = cake.task.Task(b)
    tc = cake.task.Task(c)
    tb.addCallback(eb.set)
    tc.addCallback(ec.set)        
    tc.startAfter([ta, tb])
    
    self.assertTrue(tc.started)
    self.assertFalse(ta.started)
    self.assertFalse(tb.started)
    
    tb.start()
    
    eb.wait(0.5)

    self.assertTrue(tb.completed)
    self.assertTrue(tb.succeeded)
    
    self.assertFalse(tc.completed)
    
    ta.start()

    ec.wait(0.5)    

    self.assertTrue(tc.completed)
    self.assertTrue(ta.failed)
    self.assertTrue(tb.succeeded)
    self.assertTrue(tc.failed)
    self.assertEqual(result, ["b"])
    
  def testMultipleSubTasks(self):
    result = []
    
    def a():
      result.append("a")
      t = cake.task.Task.getCurrent()
      
      def b1():
        self.assertTrue(cake.task.Task.getCurrent() is t1)
        result.append("b1")
        
      def b2():
        self.assertTrue(cake.task.Task.getCurrent() is t2)
        result.append("b2")
        
      t1 = cake.task.Task(b1)
      t1.start()
      
      t2 = cake.task.Task(b2)
      t2.start()

      self.assertTrue(t1 is not t)
      self.assertTrue(t2 is not t)
      self.assertTrue(t1 is not t2)
      
      t.completeAfter([t1, t2])
      
    def c():
      result.append("c")

    ec = threading.Event()
    ta = cake.task.Task(a)
    tc = cake.task.Task(c)
    tc.addCallback(ec.set)
    tc.startAfter(ta)
    ta.start()
    
    ec.wait(0.5)

    self.assertTrue(tc.completed)
    self.assertTrue(tc.succeeded)
    self.assertTrue(result in [
      ["a", "b1", "b2", "c"],
      ["a", "b2", "b1", "c"],
      ])

  def testFailedSubTasksFailsParent(self):
    
    result = []
    
    def a():
      result.append("a")
      
      def b():
        result.append("b")
        raise RuntimeError()
      
      t = cake.task.Task(b)
      t.parent.completeAfter(t)
      t.start()
      
    def c():
      result.append("c")

    ec = threading.Event()
    ta = cake.task.Task(a)
    tc = cake.task.Task(c)
    tc.addCallback(ec.set)
    tc.startAfter(ta)
    ta.start()
    
    ec.wait(0.5)

    self.assertTrue(tc.completed)
    self.assertTrue(ta.failed)
    self.assertTrue(tc.failed)
    self.assertEqual(result, ["a", "b"])

  def testCompleteAfterMultipleSomeFail(self):
    
    result = []
    
    def a():
      result.append("a")
      
    def b1():
      raise Exception()
      
    def b2():
      result.append("b2")
      
    def c():
      result.append("c")
      
    tb1 = cake.task.Task(b1)
    tb2 = cake.task.Task(b2)

    ta = cake.task.Task(a)
    ta.completeAfter([tb1, tb2])

    ec = threading.Event()
    tc = cake.task.Task(c)
    tc.addCallback(ec.set)
    tc.startAfter(ta)

    ta.start()
    
    self.assertFalse(tc.completed)
    self.assertFalse(ta.completed)

    tb2.start()
    
    self.assertFalse(tc.completed)
    self.assertFalse(ta.completed)
    
    tb1.start()
    
    ec.wait(0.5)

    self.assertTrue(tc.completed)
    self.assertTrue(ta.failed)
    self.assertTrue(tb1.failed)
    self.assertTrue(tb2.succeeded)
    self.assertTrue(tc.failed)
    self.assertTrue(result in [["a", "b2"], ["b2", "a"]])

  def testCancelBeforeStart(self):
    
    def a():
      pass
    
    ta = cake.task.Task(a)
    
    ta.cancel()
    
    self.assertTrue(ta.started)
    self.assertTrue(ta.completed)
    self.assertFalse(ta.succeeded)
    self.assertTrue(ta.failed)
  
  def testCancelAfterCompleteThrows(self):
    
    def a():
      pass
    
    ea = threading.Event()
    ta = cake.task.Task(a)
    ta.addCallback(ea.set)
    
    ta.start()
  
    ea.wait(0.5)

    self.assertTrue(ta.completed)
    self.assertRaises(cake.task.TaskError, ta.cancel)

  def testCancelWhileExecutingFailsTask(self):
    
    def a():
      cake.task.Task.getCurrent().cancel()
      
    ea = threading.Event()
    ta = cake.task.Task(a)
    ta.addCallback(ea.set)
    
    ta.start()
  
    ea.wait(0.5)

    self.assertTrue(ta.completed)
    self.assertTrue(ta.started)
    self.assertTrue(ta.completed)
    self.assertFalse(ta.succeeded)
    self.assertTrue(ta.failed)

  def testTaskResult(self):
    
    def a():
      return "a"

    e = threading.Event()
    t = cake.task.Task(a)
    t.addCallback(e.set)
    
    t.start()
  
    e.wait(0.5)

    self.assertTrue(t.completed)
    self.assertEqual(t.result, "a")

  def testNestedTaskResult(self):
    
    def a():
      tb = cake.task.Task(b)
      tb.start()
      return tb
    
    def b():
      return "b"

    e = threading.Event()
    ta = cake.task.Task(a)
    ta.addCallback(e.set)
    ta.start()
    
    e.wait(0.5)
    
    self.assertTrue(ta.succeeded)
    self.assertEqual(ta.result, "b")

if __name__ == "__main__":
  suite = unittest.TestLoader().loadTestsFromTestCase(TaskTests)
  runner = unittest.TextTestRunner(verbosity=2)
  sys.exit(not runner.run(suite).wasSuccessful())
