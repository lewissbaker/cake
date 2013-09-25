import sys
import os.path

rootDir = os.path.dirname(__file__)
srcDir = os.path.join(rootDir, "src")
testDir = os.path.join(rootDir, "test")
tmpDir = os.path.join(rootDir, "build", "test")

if not os.path.isdir(tmpDir):
  os.makedirs(tmpDir)

sys.path = [srcDir] + sys.path

from cake.test.framework import findTests, runTests, TestReporter

reporter = TestReporter()

runTests(
  tests=sorted(findTests(testDir), key=lambda t: t.name),
  reporter=reporter,
  testDir=testDir,
  tmpDir=tmpDir,
  )

passed = reporter.passedTests()
failed = reporter.failedTests()
ignored = reporter.ignoredTests()

print "-------"
print "Summary:",
print len(passed), "passed,", len(failed), "failed,", len(ignored), "ignored"

sys.exit(len(reporter.failedTests()))
