"""Main Entrypoint and Running Utilities.
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
  
  usage = "usage: %prog [options] <cake-script>*"
  
  parser = optparse.OptionParser(usage=usage)
  parser.add_option(
    "-b", "--boot", metavar="FILE",
    dest="boot",
    help="Path to the boot.cake configuration file to use.",
    default=None
    )
  parser.add_option(
    "-p", "--profile", metavar="FILE",
    dest="profileOutput",
    help="Path to output profiling information to.",
    default=None,
    )
  parser.add_option(
    "-d", "--debug",
    type="int",
    dest="debugLevel",
    help="Set debug message level in the range [0=Default, 2].",
    default=0,
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

  logger = cake.logging.Logger(debugLevel=options.debugLevel)
  engine = cake.engine.Engine(logger)
  try:
    bootCode = engine.getByteCode(options.boot)
    exec bootCode in {"engine" : engine, "__file__" : options.boot}
  except Exception:
    msg = traceback.format_exc()
    engine.logger.outputError(msg)
    return 1

  try:
    variant = engine.findVariant(**keywords)
  except LookupError, e:
    msg = "Error: unable to determine build variant: %s" % str(e)
    engine.logger.outputError(msg)
    return 1

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

if __name__ == '__main__':
  try:
    sys.exit(run())
  except KeyboardInterrupt:
    sys.exit(-1)