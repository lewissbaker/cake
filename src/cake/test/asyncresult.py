"""AsyncResult Unit Tests.

Tests for AsyncResult and @waitForAsyncResult decorator.
"""

import unittest
import threading
import sys
from cake.async import waitForAsyncResult, flatten, DeferredResult, AsyncResult
from cake.task import Task

class AsyncResultTests(unittest.TestCase):

  def testCallNoAsync(self):

    @waitForAsyncResult
    def makeTuple(*args):
      return tuple(args)

    @waitForAsyncResult
    def makeDict(**kwargs):
      return dict(kwargs)

    self.assertEqual(makeTuple(), ())
    self.assertEqual(makeTuple(1, 2, 3), (1, 2, 3))

    self.assertEqual(makeDict(), {})
    self.assertEqual(makeDict(x=1, y=2), {"x": 1, "y": 2})

  def testCallWithAsyncResultArgs(self):

    @waitForAsyncResult
    def makeArgs(*args, **kwargs):
      return (args, kwargs)

    def returnValue(value):
      return value

    t1 = Task(lambda: returnValue(1))
    t2 = Task(lambda: returnValue(2))
    t3 = Task(lambda: returnValue(3))

    r1 = DeferredResult(t1)
    r2 = DeferredResult(t2)
    r3 = DeferredResult(t3)

    result = makeArgs(r1, r2, x=r3)

    assert isinstance(result, AsyncResult)

    e = threading.Event()
    result.task.addCallback(e.set)

    t1.start()
    t2.start()
    t3.start()

    e.wait(0.5)

    self.assertTrue(result.task.completed)
    self.assertTrue(result.task.succeeded)

    args, kwargs = result.result

    self.assertEqual(args, (1, 2))
    self.assertEqual(kwargs, {"x": 3})

  def testCallWithNestedAsyncResultArgs(self):

    @waitForAsyncResult
    def makeArgs(*args, **kwargs):
      return (args, kwargs)

    def returnValue(value):
      return value

    t1 = Task(lambda: returnValue(1))
    t2 = Task(lambda: returnValue(2))
    t3 = Task(lambda: returnValue(3))
    t4 = Task(lambda: returnValue(4))

    r1 = DeferredResult(t1)
    r2 = DeferredResult(t2)
    r3 = DeferredResult(t3)
    r4 = DeferredResult(t4)

    r5 = makeArgs(r1, r2)

    r6 = makeArgs([r1, r4], x=r3, y=r5)

    assert isinstance(r6, AsyncResult)

    e = threading.Event()
    r6.task.addCallback(e.set)

    t1.start()
    t2.start()
    t3.start()
    t4.start()

    e.wait(0.5)

    self.assertTrue(r5.task.succeeded)
    self.assertTrue(r6.task.succeeded)

    args, kwargs = r5.result
    self.assertEqual(args, (1, 2))
    self.assertEqual(kwargs, {})

    args, kwargs = r6.result

    self.assertEqual(args, ([1, 4],))
    self.assertEqual(kwargs, {"x": 3, "y": ((1, 2), {})})

  def testFlattenNoAsync(self):
    self.assertEqual(flatten([]), [])
    self.assertEqual(flatten([1, 2, 3]), [1, 2, 3])
    self.assertEqual(flatten([1, [2, 3], 4]), [1, 2, 3, 4])
    self.assertEqual(flatten([[1, 2], [3, [4, 5], 6], 7]), [1, 2, 3, 4, 5, 6, 7])

  def testFlattenWithAsync(self):

    def makeAsync(value):
      task = Task(lambda: value)
      task.start()
      return DeferredResult(task)

    value = makeAsync([
      makeAsync([1, 2]),
      [3, makeAsync([4, 5]), makeAsync(6)],
      makeAsync(7)
      ])

    result = flatten(value)

    self.assertTrue(isinstance(result, AsyncResult))

    e = threading.Event()

    result.task.addCallback(e.set)

    e.wait(0.5)

    self.assertTrue(result.task.succeeded)

    self.assertEqual(result.result, [1, 2, 3, 4, 5, 6, 7])

if __name__ == "__main__":
  suite = unittest.TestLoader().loadTestsFromTestCase(AsyncResultTests)
  runner = unittest.TextTestRunner(verbosity=2)
  sys.exit(not runner.run(suite).wasSuccessful())
