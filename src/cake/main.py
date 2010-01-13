import os
import os.path
import sys
import optparse
import threading

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
  """
  
  while True:
    candidate = cake.path.join(path, file)
    if cake.filesys.isFile(candidate):
      return candidate
  
    parent = cake.path.directory(path)
    if parent == path:
      return None
    
    path = parent

def run(args, cwd=None):
  """Run a cake build with the specified command-line args.
  
  @param args: A list of command-line args for cake.
  @type args: list of string
  
  @return: The exit code of cake. Non-zero if exited with errors, zero
  if exited with success.
  @rtype: int
  """
  
  usage = "usage: %prog [options] <cake-script>*"
  
  parser = optparse.OptionParser(usage=usage)
  parser.add_option(
    "-b", "--boot", metavar="FILE",
    dest="boot",
    help="Path to the boot.cake configuration file to use.",
    default=None
    )
  
  options, args = parser.parse_args(args)
  
  if cwd is not None:
    cwd = os.path.abspath(cwd)
  else:
    cwd = os.getcwd()

  if not args:
    args = [cwd]
  
  if options.boot is None:
    options.boot = searchUpForFile(cwd, 'boot.cake')
    if options.boot is None:
      sys.stderr.write("cake: could not find 'boot.cake' in %s\n" % cwd)
      return -1
  elif not os.path.isabs(options.boot):
    options.boot = os.path.join(cwd, options.boot)
  
  engine = cake.engine.Engine()
  bootCode = engine.getByteCode(options.boot)
  exec bootCode in {"engine" : engine, "__file__" : options.boot}

  tasks = []
  for arg in args:
    if not os.path.isabs(arg):
      arg = os.path.join(cwd, arg)
    if cake.filesys.isDirectory(arg):
      arg = cake.path.join(arg, 'build.cake')

    task = engine.execute(arg)
    tasks.append(task)

  finished = threading.Event()
  
  def onFinish():
    if taskGroup.succeeded:
      if engine.logger.warningCount:
        msg = "Build succeeded with %i warnings." % engine.logger.warningCount
      else:
        msg = "Build succeeded."
    else:
      if engine.logger.warningCount:
        msg = "Build failed with %i errors and %i warnings." % (
          engine.logger.errorCount,
          engine.logger.warningCount,
          )
      else:
        msg = "Build failed with %i errors." % engine.logger.errorCount
    engine.logger.outputInfo(msg)
    finished.set()
  
  taskGroup = cake.task.TaskGroup(tasks)
  taskGroup.addCallback(onFinish)
  finished.wait()
  
  return engine.logger.errorCount
