import unittest
import time

import cake.task

class TaskTests(unittest.TestCase):

  def testTaskFunctionExecutedExactlyOnce(self):
    result = []
    def f():
      result.append(None)
      
    t = cake.task.Task(f)
    
    self.assertFalse(t.started)
    self.assertFalse(t.completed)
    self.assertFalse(t.succeeded)
    self.assertFalse(t.failed)
    
    t.start()
    
    self.assertTrue(t.started)
    
    for _ in xrange(5):
      if t.completed:
        self.assertTrue(t.started)
        self.assertTrue(t.succeeded)
        self.assertFalse(t.failed)
        self.assertEqual(len(result), 1)
        break
      time.sleep(0.1)
    else:
      self.fail("task didn't complete")

  def testFailingTask(self):
    def f():
      raise RuntimeError()

    t = cake.task.Task(f)
    t.start()
    
    for _ in xrange(5):
      if t.completed:
        self.assertTrue(t.started)
        self.assertFalse(t.succeeded)
        self.assertTrue(t.failed)
        break
      time.sleep(0.1)
    else:
      self.fail("task didn't complete")
      
  def testStartAfter(self):
    result = []
    def a():
      result.append("a")
    def b():
      result.append("b")
      
    ta = cake.task.Task(a)
    tb = cake.task.Task(b)
    tb.startAfter(ta)
    
    self.assertTrue(tb.started)
    self.assertFalse(ta.started)
    
    ta.start()
    
    self.assertTrue(ta.started)
    
    for _ in xrange(5):
      if tb.completed:
        self.assertTrue(ta.succeeded)
        self.assertTrue(tb.started)
        self.assertTrue(tb.succeeded)
        self.assertEqual(result, ["a", "b"])
        break
      time.sleep(0.1)
    else:
      self.fail("task didn't complete")
      
  def testStartAfterCompletedTask(self):
    result = []
    def a():
      result.append("a")
    def b():
      result.append("b")
      
    ta = cake.task.Task(a)
    tb = cake.task.Task(b)
    
    ta.start()
    
    self.assertTrue(ta.started)
    
    for _ in xrange(5):
      if ta.completed:
        break
      time.sleep(0.1)
    else:
      self.fail("task a didn't finish")

    self.assertTrue(ta.completed)
    
    tb.startAfter(ta)
    
    self.assertTrue(tb.started)
    
    for _ in xrange(5):
      if tb.completed:
        self.assertTrue(ta.succeeded)
        self.assertTrue(tb.started)
        self.assertTrue(tb.succeeded)
        self.assertEqual(result, ["a", "b"])
        break
      time.sleep(0.1)
    else:
      self.fail("task didn't complete")
    
  def testStartAfterFailedTask(self):
    result = []
    def a():
      result.append("a")
      raise RuntimeError()
    def b():
      result.append("b")
    
    ta = cake.task.Task(a)
    tb = cake.task.Task(b)
    tb.startAfter(ta)
    
    self.assertTrue(tb.started)
    self.assertFalse(ta.started)
    
    ta.start()
    
    self.assertTrue(ta.started)
    
    for _ in xrange(5):
      if tb.completed:
        self.assertTrue(tb.failed)
        self.assertTrue(tb.started)
        self.assertTrue(tb.failed)
        self.assertEqual(result, ["a"])
        break
      time.sleep(0.1)
    else:
      self.fail("task didn't complete")
      
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

    ta = cake.task.Task(a)
    tc = cake.task.Task(c)
    tc.startAfter(ta)
    ta.start()
    
    for _ in xrange(5):
      if tc.completed:
        self.assertEqual(result, ["a", "b", "c"])
        break
      time.sleep(0.1)
    else:
      self.fail("task c didn't complete")
    
  def testStartAfterMultiple(self):
    
    result = []
    def a():
      result.append("a")
    def b():
      result.append("b")
    def c():
      result.append("c")
      
    ta = cake.task.Task(a)
    tb = cake.task.Task(b)
    tc = cake.task.Task(c)
    tc.startAfter([ta, tb])
    
    self.assertTrue(tc.started)
    self.assertFalse(ta.started)
    self.assertFalse(tb.started)
    
    ta.start()
    
    self.assertFalse(tc.completed)
    
    tb.start()
    
    for _ in xrange(5):
      if tc.completed:
        self.assertTrue(ta.succeeded)
        self.assertTrue(tb.succeeded)
        self.assertTrue(tc.succeeded)
        self.assertTrue(result in [["a", "b", "c"], ["b", "a", "c"]])
        break
      time.sleep(0.1)
    else:
      self.fail("task didn't complete")
    
  def testStartAfterMultipleSomeFail(self):
    
    result = []
    def a():
      raise Exception()
    def b():
      result.append("b")
    def c():
      result.append("c")
      
    ta = cake.task.Task(a)
    tb = cake.task.Task(b)
    tc = cake.task.Task(c)
    tc.startAfter([ta, tb])
    
    self.assertTrue(tc.started)
    self.assertFalse(ta.started)
    self.assertFalse(tb.started)
    
    tb.start()
    
    for _ in xrange(5):
      if tb.completed:
        self.assertTrue(tb.succeeded)
        break
      time.sleep(0.1)
    else:
      self.fail("task didn't complete")
    
    self.assertFalse(tc.completed)
    
    ta.start()
    
    for _ in xrange(5):
      if tc.completed:
        self.assertTrue(ta.failed)
        self.assertTrue(tb.succeeded)
        self.assertTrue(tc.failed)
        self.assertEqual(result, ["b"])
        break
      time.sleep(0.1)
    else:
      self.fail("task didn't complete")
    
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

    ta = cake.task.Task(a)
    tc = cake.task.Task(c)
    tc.startAfter(ta)
    ta.start()
    
    for _ in xrange(5):
      if tc.completed:
        self.assertTrue(tc.succeeded)
        self.assertTrue(result in [
          ["a", "b1", "b2", "c"],
          ["a", "b2", "b1", "c"],
          ])
        break
      time.sleep(0.1)
    else:
      self.fail("task c didn't complete")

  def testFailedSubTasksFailsParent(self):
    
    result = []
    
    def a():
      result.append("a")
      
      def b():
        result.append("b")
        raise RuntimeError()
      
      t = cake.task.Task(b)
      t.start()
      
    def c():
      result.append("c")

    ta = cake.task.Task(a)
    tc = cake.task.Task(c)
    tc.startAfter(ta)
    ta.start()
    
    for _ in xrange(5):
      if tc.completed:
        self.assertTrue(ta.failed)
        self.assertTrue(tc.failed)
        self.assertEqual(result, ["a", "b"])
        break
      time.sleep(0.1)
    else:
      self.fail("task c didn't complete")

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

    tc = cake.task.Task(c)
    tc.startAfter(ta)

    ta.start()
    
    self.assertFalse(tc.completed)
    self.assertFalse(ta.completed)

    tb2.start()
    
    self.assertFalse(tc.completed)
    self.assertFalse(ta.completed)
    
    tb1.start()
    
    for _ in xrange(5):
      if tc.completed:
        self.assertTrue(ta.failed)
        self.assertTrue(tb1.failed)
        self.assertTrue(tb2.succeeded)
        self.assertTrue(tc.failed)
        self.assertTrue(result in [["a", "b2"], ["b2", "a"]])
        break
      time.sleep(0.1)
    else:
      self.fail("task c didn't complete")

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
    
    ta = cake.task.Task(a)
    
    ta.start()
  
    for _ in xrange(5):
      if ta.completed:
        break
      time.sleep(0.1)
    else:
      self.fail("task a didn't finish")

    self.assertRaises(cake.task.TaskError, ta.cancel)
            
  def testCancelWhileExecutingFailsTask(self):
    
    def a():
      cake.task.Task.getCurrent().cancel()
      
    ta = cake.task.Task(a)
    
    ta.start()
  
    for _ in xrange(5):
      if ta.completed:
        break
      time.sleep(0.1)
    else:
      self.fail("task a didn't finish")
    
    self.assertTrue(ta.started)
    self.assertTrue(ta.completed)
    self.assertFalse(ta.succeeded)
    self.assertTrue(ta.failed)
  