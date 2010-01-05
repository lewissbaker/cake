import unittest

_modules = [
  "cake.test.task",
  ]

def suite():
  loader = unittest.TestLoader()
  s = unittest.TestSuite()
  for name in _modules:
    print name
    s.addTests(loader.loadTestsFromName(name))
  return s

def run():
  s = suite()
  runner = unittest.TextTestRunner(verbosity=2)
  return runner.run(s)

if __name__ == "__main__":
  import sys
  sys.exit(run())
