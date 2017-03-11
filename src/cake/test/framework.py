"""Classes used for testing the cake tool.

See tests in $ROOT/test/.
"""

import sys
import re
import os
import os.path
import tempfile
import subprocess
import shutil
import datetime
import time
import thread
import threading
from functools import wraps

class TestCase:

  def __init__(self, testFunc):
    self.testFunc = testFunc
    self.name = testFunc.__name__
    self.ignored = False

  def run(self, reporter, testDir, tmpDir):
    if self.ignored:
      reporter.testIgnored(self)
    else:
      reporter.testStarted(self)
      try:
        context = TestContext(self, reporter, testDir, tmpDir)
        self.testFunc(context)
        context.cleanUp()
      except TestFailedException:
        pass
      except Exception, e:
        reporter.result.errors.append(
          "Test threw unhandled exception: %s" % str(e))
      finally:
        reporter.testFinished()
    
class TestResult:

  def __init__(self, testCase):
    self.testCase = testCase
    self.testName = testCase.name
    self.startTimeUtc = None
    self.endTimeUtc = None
    self.errors = []
    self.warnings = []
    self.ignored = False
    self.reason = None

class TestReporter:

  def __init__(self):
    self.result = None
    self.results = []

  def testStarted(self, testCase):
    if self.result is not None:
      raise RuntimeError("Test '%s' is already running" % self.result.testName)

    self.result = TestResult(testCase)
    self.result.startTimeUtc = datetime.datetime.utcnow()

  def testFinished(self):
    if self.result is None:
      raise RuntimeError("No test is currently in progress")

    self.result.endTimeUtc = datetime.datetime.utcnow()

    timeTaken = self.result.endTimeUtc - self.result.startTimeUtc
    timeString = "%0.3fs" % timeTaken.total_seconds()

    if self.result.errors:
      print "FAILED     %s: took %s" % (self.result.testName, timeString)
      for err in self.result.errors:
        print "  ERROR:", err
    else:
      print "PASSED     %s: took %s" % (self.result.testName, timeString)

    self.results.append(self.result)
    self.result = None

  def error(self, message):
    if self.result:
      self.result.errors.append(message)
    raise TestFailedException(message)

  def warning(self, message):
    if self.result:
      self.result.warnings.append(message)

  def testIgnored(self, testName, reason):
    result = self.result
    if result is None:
      result = TestResult(testName)
    else:
      if result.testName != testName:
        raise RuntimeError(
          "Cannot ignore test '%s' when test '%s' is running" % (
            testName,
            result.testName))
      self.result = None

    result.ignored = True
    result.reason = reason
    self.results.append(result)

    print "IGNORED  %s: %s" % (testName, reason)

  def passedTests(self):
    return [r for r in self.results if not r.ignored and not r.errors]

  def failedTests(self):
    return [r for r in self.results if not r.ignored and r.errors]

  def ignoredTests(self):
    return [r for r in self.results if r.ignored]

class TestContext:

  def __init__(self, testCase, reporter, testDir, tmpDir):
    self.testCase = testCase
    self.reporter = reporter
    self.testDir = testDir
    self.root = os.path.abspath(
      tempfile.mkdtemp(prefix=testCase.name, dir=tmpDir))
    
  def copyTree(self, src, dst):
    """Copy the directory tree under source directory into destination 
    directory.

    Relative paths are assumed relative to self.root.

    @param src: Path of the source directory to copy.
    
    @param dst: Path to copy source tree to. Will be created if it doesn't
    already exist.
    """
    src = self.abspath(src)
    dst = self.abspath(dst)
    if not os.path.isdir(dst):
      os.makedirs(dst)

    for srcBase, dirs, files in os.walk(src):
      relPath = os.path.relpath(srcBase, src)
      dstBase = os.path.join(dst, relPath)
      for name in dirs:
        dstPath = os.path.join(dstBase, name)
        if not os.path.isdir(dstPath):
          os.mkdir(dstPath)
      for name in files:
        srcPath = os.path.join(srcBase, name)
        dstPath = os.path.join(dstBase, name)
        shutil.copy(srcPath, dstPath)
    
  def cleanUp(self):
    """Remove the test context directory and everything under it recursively.
    """
    if os.path.isdir(self.root):
      shutil.rmtree(self.root)

  def abspath(self, p):
    """Convert the path to an absolute path if not already absolute.
    """
    if os.path.isabs(p):
      return p
    return os.path.join(self.root, p)

  def removeFile(self, path):
    """Delete the specified file.
    """
    self.checkFileExists(path)
    os.remove(self.abspath(path))

  def checkFileExists(self, path):
    """Check that the file at specified path exists.
    Log an error if it doesn't exist.
    """
    exists = os.path.isfile(self.abspath(path))
    if not exists:
      self.reporter.error("File '%s' does not exist." % path)
    return exists

  def touchFile(self, path):
    """Touch the file at the specified path to update its timestamp.

    Creates an empty file if doesn't already exist.
    """
    path = self.abspath(path)

    dirPath = os.path.dirname(path)
    if not os.path.isdir(dirPath):
      os.makedirs(dirPath)

    open(self.abspath(path), 'wb+').close()

  def writeTextFile(self, path, contents):
    """Write the specified contents as a UTF-8 encoded text file.
    """
    path = self.abspath(path)

    dirPath = os.path.dirname(path)
    if not os.path.isdir(dirPath):
      os.makedirs(dirPath)

    f = open(path, 'wt')
    try:
      f.write(contents.encode("utf8"))
    finally:
      f.close()

  def readFileContents(self, path):
    absPath = self.abspath(path)
    try:
      f = open(absPath, 'rb')
      try:
        return f.read()
      finally:
        f.close()
    except Exception, e:
      if os.path.isfile(absPath):
        self.reporter.error("Error reading file '%s': %s" % (path, str(e)))
      else:
        self.reporter.error("File '%s' does not exist." % path)
      return None

  def checkFilesAreSame(self, a, b):
    """Check that both files exist and have the same contents.
    """
    
    if self.checkFileExists(a) and self.checkFileExists(b):
      aContents = self.readFileContents(a)
      bContents = self.readFileContents(b)

      if aContents is not None and bContents is not None:
        if aContents != bContents:
          self.reporter.error("Files '%s' (%i bytes) and '%s' (%i bytes) "
                              "should be same but differ." % (
                                a, len(aContents),
                                b, len(bContents)))
          
  def runCake(self, *args, **kwargs):
    cwd = kwargs.get('cwd', '.')
    cwd = self.abspath(cwd)
    
    timeLimit = kwargs.get('timeLimit', 60)

    cakeSrcDir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    cakeScript = os.path.abspath(os.path.join(cakeSrcDir, 'run.py'))

    env = {}
    env.update(os.environ)
    env['PYTHONPATH'] = cakeSrcDir

    startTime = datetime.datetime.utcnow()

    outfile = tempfile.TemporaryFile()
    try:
      try:
        p = subprocess.Popen(
          args=[sys.executable, '-u', cakeScript, args],
          env=env,
          cwd=cwd,
          stdout=outfile,
          stderr=outfile,
        )

        e = threading.Event()

        def waitForExit():
          try:
            p.wait()
          finally:
            e.set()

        threading.Thread(target=waitForExit).start()

        timeout = False
        if not e.wait(timeLimit):
          timeout = True

          if hasattr(p, "kill"):
            try:
              p.kill()
            except Exception, e:
              self.reporter.warning(
                "Failed to kill long-running cake command (pid %i): %s" % (
                  p.pid,
                  str(e)))

          self.reporter.error(
            "Cake command took too long (>%f seconds): cake %s" % (
              timeLimit,
              " ".join(args)))

        outfile.seek(0)
        output = outfile.read()

        return CakeOutput(self.reporter, args, p.returncode, output)
        
      except EnvironmentError, e:
        self.reporter.error("Error running cake: %s" % str(e))

    finally:
      outfile.close()

class TestFailedException(Exception):
  """Exception thrown when a test fails.

  This exception type is caught specially by the testing framework.
  """
  pass

class CakeOutput:

  _configRe = re.compile("^Building with .*Variant\\(.*\\)$")
  _succeededRe = re.compile("^Build succeeded\\.$")
  _buildTookRe = re.compile("^Build took \\d+:\\d+:\\d+\\.\\d+\\.$")

  def __init__(self, reporter, args, exitCode, output):
    self.args = args
    self.reporter = reporter
    self.exitCode = exitCode
    self.output = output
    self.lines = [l.rstrip().replace("\\", "/") for l in output.split('\n') if l.rstrip()]

  @property
  def command(self):
    args = ["cake"]
    args.extend(self.args)
    return " ".join(args)

  def checkSucceeded(self):
    if self.exitCode != 0:
      self.reporter.error(
        "Cake command (%s) failed with exit code %i.\nOutput:\n%s" % (
          self.command,
          self.exitCode,
          self.output))

  def checkFailed(self):
    if self.exitCode == 0:
      self.reporter.error(
        "Cake command (%s) succeeded but was expected to fail.\nOutput:\n%s" % (
          self.command,
          self.output))

  def checkBuildWasNoop(self):
    self.checkSucceeded()
    for line in self.lines:
      if self._configRe.match(line):
        continue
      elif self._succeededRe.match(line):
        continue
      elif self._buildTookRe.match(line):
        continue
      else:
        self.reporter.error(
          "Cake command (" + self.command + 
          ") was expected to be a no-op but had line '" + line +
          "'.\nOutput:\n" + self.output)

  def checkNoLine(self, line):
    if line in self.lines:
      self.reporter.error(
        "Line '%s' should not have been in output of '%s'.\nOutput:\n%s" % (
          line,
          self.command,
          self.output))

  def checkHasLineMatching(self, pattern):
    pattern = re.compile(pattern)
    if not any(pattern.match(l) for l in self.lines):
      self.reporter.error(
        "Expected line matching '%s' in output of '%s'.\nOutput:\n%s" % (
          pattern.pattern,
          self.command,
          self.output))
      
  def checkHasLine(self, line):
    if line not in self.lines:
      self.reporter.error(
        "Expected line '%s' to appear in output of '%s'.\nOutput:\n%s" % (
          line,
          self.command,
          self.output))

  def checkHasLines(self, lines):
    for line in lines:
      self.checkHasLine(line)

  def checkHasLinesInOrder(self, lines):

    startIdx = 0

    for i, line in enumerate(lines):
      try:
        startIdx = self.lines.index(line, startIdx)
      except ValueError:
        try:
          self.lines.index(line, 0, startIdx)

          self.reporter.error(
            "Expected line '%s' after '%s', but was before" % (
              line, lines[i-1]))

        except ValueError:
          if i > 0:
            self.reporter.error(
              "Expected line '%s' somewhere after '%s', but not present.\nOutput:\n%s" % (
                line, lines[i-1], self.output))
          else:
            self.reporter.error(
              "Expected line '%s' somewhere in output, but not present.\nOutput:\n%s" % (
                line, self.output))
    
def caketest(*args, **kwargs):
  """Decorator to be used to identify a test-case function.
  """

  if args:
    # @caketest
    # def test(t):
    #   pass
    assert not kwargs
    assert len(args) == 1
    
    return TestCase(args[0])

  else:
    # @caketest(fixture="path")
    # def test(t):
    #   pass

    fixture = kwargs.get("fixture", None)
    
    def decorator(testFunc):
      if fixture:
        @wraps(testFunc)
        def run(t):
          fixtureDir = os.path.join(t.testDir, fixture)
          fixtureDir = os.path.abspath(fixtureDir)
          fixtureDir = os.path.normpath(fixtureDir)
          t.copyTree(fixtureDir, t.root)
          testFunc(t)

        return TestCase(run)
      else:
        return TestCase(testFunc)

    return decorator

def findTests(testDir):
  """Return a sequence of TestCase objects.

  One for each test found in the directory.
  """
  for name in os.listdir(testDir):
    if not name.endswith(".py"):
      continue

    scriptPath = os.path.join(testDir, name)
    scriptGlobals = {'__file__': scriptPath}
    execfile(scriptPath, scriptGlobals)
    
    for v in scriptGlobals.values():
      if isinstance(v, TestCase):
        yield v

def runTests(tests, reporter, testDir, tmpDir):
  for test in tests:
    test.run(reporter, testDir, tmpDir)
