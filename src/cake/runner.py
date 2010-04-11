"""Running Utilities.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import os
import os.path
import sys
import optparse
import threading
import datetime
import time
import traceback
import platform

import cake.logging
import cake.engine
import cake.task
import cake.path
import cake.filesys
import cake.threadpool

def callOnce(f):
  """Decorator that handles calling a function only once.
  
  The second and subsequent times it is called the cached
  result is returned.
  """
  state = {}
  def func(*args, **kwargs):
    if state:
      try:
        return state["result"]
      except KeyError:
        raise state["exception"]
    else:
      try:
        result = state["result"] = f(*args, **kwargs)
        return result
      except Exception, e:
        state["exception"] = e
        raise
  return func 

@callOnce
def _overrideOpen():
  """
  Override the built-in open() and os.open() to set the no-inherit
  flag on files to prevent processes from inheriting file handles.
  """
  if hasattr(os, "O_NOINHERIT"):
    import __builtin__
  
    old_open = __builtin__.open
    def new_open(filename, mode="r", *args, **kwargs):
      if "N" not in mode:
        mode += "N"
      return old_open(filename, mode, *args, **kwargs)
    __builtin__.open = new_open
  
    old_os_open = os.open
    def new_os_open(filename, flag, mode=0777):
      flag |= os.O_NOINHERIT
      return old_os_open(filename, flag, mode)
    os.open = new_os_open

@callOnce
def _overridePopen():
  """
  Override the subprocess Popen class due to a bug in Python 2.4
  that can cause an exception if a process finishes too quickly.
  """
  version = platform.python_version_tuple()
  if version[0] == "2" and version[1] == "4":
    import subprocess
    
    old_Popen = subprocess.Popen
    class new_Popen(old_Popen):
      def poll(self):
        try:
          return old_Popen.poll(self)
        except ValueError:
          return self.returncode
      
      def wait(self):
        try:
          return old_Popen.wait(self)
        except ValueError:
          return self.returncode
    subprocess.Popen = new_Popen

@callOnce    
def _speedUp():
  """
  Speed up execution by importing Psyco and binding the slowest functions
  with it.
  """ 
  try:
    import psyco
    psyco.bind(cake.engine.Configuration.checkDependencyInfo)
    psyco.bind(cake.engine.Configuration.createDependencyInfo)
    #psyco.full()
    #psyco.profile()
    #psyco.log()
  except ImportError:
    # Only report import failures on systems we know Psyco supports.
    version = platform.python_version_tuple()
    supportsVersion = version[0] == "2" and version[1] in ["5", "6"]
    if platform.system() == "Windows" and supportsVersion:
      sys.stderr.write(
        "warning: Psyco is not installed. Installing it may halve your incremental build time.\n"
        )

def run(args=None, cwd=None):
  """Run a cake build with the specified command-line args.
  
  @param args: A list of command-line args for cake. If this is None 
  sys.argv is used instead.
  @type args: list of string, or None
  @param cwd: The working directory to use. If this is None os.getcwd()
  is used instead.
  @type cwd: string or None
  
  @return: The exit code of cake. Non-zero if exited with errors, zero
  if exited with success.
  @rtype: int
  """
  startTime = datetime.datetime.utcnow()
  
  _overrideOpen()
  _overridePopen()
  _speedUp()
  
  if args is None:
    args = sys.argv[1:]
  
  class MyOption(optparse.Option):
    """Subclass the Option class to provide an 'extend' action.
    """  
    ACTIONS = optparse.Option.ACTIONS + ("extend",)
    STORE_ACTIONS = optparse.Option.STORE_ACTIONS + ("extend",)
    TYPED_ACTIONS = optparse.Option.TYPED_ACTIONS + ("extend",)
    ALWAYS_TYPED_ACTIONS = optparse.Option.ALWAYS_TYPED_ACTIONS + ("extend",)
  
    def take_action(self, action, dest, opt, value, values, parser):
      if action == "extend":
        lvalue = value.split(",")
        values.ensure_value(dest, []).extend(lvalue)
      else:
        optparse.Option.take_action(
          self, action, dest, opt, value, values, parser
          )
  
  usage = "usage: %prog [options] <cake-script>*"
  
  parser = optparse.OptionParser(usage=usage,option_class=MyOption)
  parser.add_option(
    "-b", "--boot",
    metavar="FILE",
    dest="boot",
    help="Path to the boot.cake configuration file to use.",
    default=None
    )
  parser.add_option(
    "-f", "--force",
    action="store_true",
    dest="forceBuild",
    help="Force rebuild of every target.",
    default=False,
    )
  parser.add_option(
    "-p", "--projects",
    action="store_true",
    dest="createProjects",
    help="Create projects instead of building a variant.",
    default=False,
    )
  parser.add_option(
    "-j", "--jobs",
    metavar="JOBCOUNT",
    type="int",
    dest="jobs",
    help="Number of simultaneous jobs to execute.",
    default=cake.threadpool.getProcessorCount(),
    )
  parser.add_option(
    "--profile",
    metavar="FILE",
    dest="profileOutput",
    help="Path to output profiling information to.",
    default=None,
    )
  parser.add_option(
    "-d", "--debug", metavar="KEYWORDS",
    action="extend",
    dest="debugComponents",
    help="Set features to debug, eg: 'reason,run,script,scan'.",
    default=[],
    )
  
  options, args = parser.parse_args(args)
  
  if cwd is not None:
    cwd = os.path.abspath(cwd)
  else:
    cwd = os.getcwd()
  cwd = cake.path.fileSystemPath(cwd)

  keywords = {}
  scripts = []
  
  for arg in args:
    if '=' in arg:
      keyword, value = arg.split('=', 1)
      value = value.split(',')
      if len(value) == 1:
        value = value[0]
      keywords[keyword] = value
    else:
      if not os.path.isabs(arg):
        arg = os.path.join(cwd, arg)
      scripts.append(arg)
    
  if not scripts:
    scripts.append(cwd)
  
  if options.profileOutput:
    import cProfile
    p = cProfile.Profile()
    p.enable()
    threadPool = cake.threadpool.DummyThreadPool()
  else:
    threadPool = cake.threadpool.ThreadPool(options.jobs)
  cake.task.setThreadPool(threadPool)

  logger = cake.logging.Logger(debugComponents=options.debugComponents)
  engine = cake.engine.Engine(logger)
  engine.forceBuild = options.forceBuild
  engine.createProjects = options.createProjects
  
  tasks = []
  
  bootScript = options.boot
  if bootScript is not None and not os.path.isabs(bootScript):
    bootScript = os.path.abspath(bootScript)
  
  for script in scripts:
    try:
      task = engine.execute(
        path=script,
        bootScript=bootScript,
        keywords=keywords,
        )
      tasks.append(task)
    except Exception:
      msg = traceback.format_exc()
      engine.logger.outputError(msg)
    
  def onFinish():
    if mainTask.succeeded:
      engine.onBuildSucceeded()
      if engine.logger.warningCount:
        msg = "Build succeeded with %i warnings.\n" % engine.logger.warningCount
      else:
        msg = "Build succeeded.\n"
    else:
      engine.onBuildFailed()
      if engine.logger.warningCount:
        msg = "Build failed with %i errors and %i warnings.\n" % (
          engine.logger.errorCount,
          engine.logger.warningCount,
          )
      else:
        msg = "Build failed with %i errors.\n" % engine.logger.errorCount
    engine.logger.outputInfo(msg)
  
  mainTask = cake.task.Task()
  mainTask.completeAfter(tasks)
  mainTask.addCallback(onFinish)
  mainTask.start()

  if options.profileOutput:
    mainTask.addCallback(threadPool.quit)
    threadPool.run()
  else:
    finished = threading.Event()
    mainTask.addCallback(finished.set)
    # We must wait in a loop in case a KeyboardInterrupt comes.
    while not finished.isSet():
      time.sleep(0.1)
  
  endTime = datetime.datetime.utcnow()

  if options.profileOutput:
    p.disable()
    p.dump_stats(options.profileOutput)
  
  engine.logger.outputInfo("Build took %s.\n" % (endTime - startTime))
  
  return engine.logger.errorCount
