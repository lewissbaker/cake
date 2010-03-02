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

import cake.logging
import cake.engine
import cake.task
import cake.path
import cake.filesys

def searchUpForFile(path, file):
  """Search a specified directory and its parent directories for a file.
  
  @param path: The path of the directory to start searching from.
  This should be an absolute path, otherwise results may be unexpected.
  @type path: string
  
  @param file: The name of the file to search for.
  @type file: string
  
  @return: The path of the file found or None if the file was not
  found.
  @rtype: string
  """
  
  while True:
    candidate = cake.path.join(path, file)
    if cake.filesys.isFile(candidate):
      return candidate
  
    parent = cake.path.dirName(path)
    if parent == path:
      return None
    
    path = parent

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
  
  if args is None:
    args = sys.argv[1:]
  
  startTime = datetime.datetime.utcnow()
  
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
    "-p", "--profile",
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
      scripts.append(arg)

  if not scripts:
    scripts.append(cwd)
  
  if options.profileOutput:
    import cProfile
    p = cProfile.Profile()
    p.enable()
    threadPool = cake.threadpool.DummyThreadPool()
    oldThreadPool = cake.task._threadPool
    cake.task._threadPool = threadPool
    
  if options.boot is None:
    options.boot = searchUpForFile(cwd, 'boot.cake')
    if options.boot is None:
      sys.stderr.write("cake: could not find 'boot.cake' in %s\n" % cwd)
      return -1
  elif not os.path.isabs(options.boot):
    options.boot = os.path.join(cwd, options.boot)

  # Make the boot file path the cwd as we'll be making the args
  # relative to it later  
  # Ideally this would go in the boot.cake but then it would also
  # need the ability to modify the scripts path to be relative to this
  bootDir = os.path.dirname(options.boot)
  bootDir = cake.path.fileSystemPath(bootDir) 
  os.chdir(bootDir)

  logger = cake.logging.Logger(debugComponents=options.debugComponents)
  engine = cake.engine.Engine(logger)
  engine.forceBuild = options.forceBuild
  try:
    bootCode = engine.getByteCode(options.boot)
    exec bootCode in {"engine" : engine, "__file__" : options.boot}
  except Exception:
    msg = traceback.format_exc()
    engine.logger.outputError(msg)
    return 1

  if keywords:
    try:
      variants = engine.findAllVariants(keywords)
    except LookupError, e:
      msg = "Error: unable to determine build variant: %s" % str(e)
      engine.logger.outputError(msg)
      return 1
  else:
    variants = engine.defaultVariants

  tasks = []
  for script in scripts:
    if not os.path.isabs(script):
      script = os.path.join(cwd, script)
    if cake.filesys.isDir(script):
      script = cake.path.join(script, 'build.cake')

    # Find the common parts of the boot dir and arg and strip them off
    script = cake.path.fileSystemPath(script)
    index = len(cake.path.commonPath(script, bootDir))
    # If stripping a directory, make sure to strip off the separator too 
    if index and (script[index] == os.path.sep or script[index] == os.path.altsep):
      index += 1
    script = script[index:]

    for variant in variants:
      try:
        task = engine.execute(path=script, variant=variant)
        tasks.append(task)
      except Exception:
        msg = traceback.format_exc()
        engine.logger.outputError(msg)

  finished = threading.Event()
  
  def onFinish():
    if mainTask.succeeded:
      if engine.logger.warningCount:
        msg = "Build succeeded with %i warnings.\n" % engine.logger.warningCount
      else:
        msg = "Build succeeded.\n"
    else:
      if engine.logger.warningCount:
        msg = "Build failed with %i errors and %i warnings.\n" % (
          engine.logger.errorCount,
          engine.logger.warningCount,
          )
      else:
        msg = "Build failed with %i errors.\n" % engine.logger.errorCount
    engine.logger.outputInfo(msg)
    finished.set()
  
  mainTask = cake.task.Task()
  mainTask.addCallback(onFinish)
  mainTask.startAfter(tasks)

  if options.profileOutput:
    mainTask.addCallback(threadPool.quit)
    threadPool.run()
    cake.task._threadPool = oldThreadPool
  else:
    # We must wait in a loop in case a KeyboardInterrupt comes.
    while not finished.isSet():
      time.sleep(0.1)
  
  endTime = datetime.datetime.utcnow()

  if options.profileOutput:
    p.disable()
    p.dump_stats(options.profileOutput)
  
  engine.logger.outputInfo("Build took %s.\n" % (endTime - startTime))
  
  return engine.logger.errorCount
