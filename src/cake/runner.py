"""Running Utilities.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import os
import os.path
import sys
import threading
import datetime
import time
import traceback
import platform

import cake.engine
import cake.logging
import cake.path
import cake.script
import cake.task
import cake.threadpool
import cake.version

from cake.async_util import flatten

from optparse import Option, OptionParser

class DebugKeywords:
  def __init__(self):
    self.keywords = []

  def append(self, arg_value):
    self.keywords.extend(value.split(sep=","))

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
  
  if args is None:
    args = sys.argv[1:]

  if cwd is not None:
    cwd = os.path.abspath(cwd)
  else:
    cwd = os.getcwd()
  
  usage = "usage: %prog [options] <cake-script>*"
  argsCakeFlag = "--args"
  
  parser = OptionParser(usage=usage, add_help_option=False)
  parser.add_option(
    "-h", "--help",
    action="help",
    help="Show this help message and exit.",
    )
  parser.add_option(
    "-v", "--version",
    dest="outputVersion",
    action="store_true",
    help="Print the current version of Cake and exit.",
    default=False,
    )
  parser.add_option(
    argsCakeFlag,
    metavar="FILE",
    dest="args",
    help="Path to the args.cake file to use.",
    default=None,
    )
  parser.add_option(
    "--config",
    metavar="FILE",
    dest="config",
    help="Path to the config.cake configuration file to use.",
    default=None,
    )
  parser.add_option(
    "--debug", metavar="KEYWORDS",
    action="append",
    dest="debugComponents",
    help="Set features to debug, eg: 'reason,run,script,scan,time'.",
    default=DebugKeywords(),
    )
  parser.add_option(
    "-s", "--silent", "--quiet",
    action="store_true",
    dest="quiet",
    help="Suppress printing of all Cake messages, warnings and errors.",
    default=False,
    )
  parser.add_option(
    "-f", "--force",
    action="store_true",
    dest="forceBuild",
    help="Force rebuild of every target.",
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
    "-k", "--keep-going",
    dest="maximumErrorCount",
    action="store_const",
    const=None,
    help="Keep building even in the presence of errors.",
    )
  parser.add_option(
    "-e", "--max-errors",
    dest="maximumErrorCount",
    metavar="COUNT",
    type="int",
    help="Halt the build after a certain number of errors.",
    default=100,
    )
  parser.add_option(
    "-l", "--list-targets",
    dest="listTargetsMode",
    action="store_true",
    help="List named targets in specified build scripts.",
    default=False,
  )
  
  # Find and remove script filenames from the arguments.
  scriptTargets = []
  newArgs = []
  for arg in args:
    if arg.startswith('-'):
      newArgs.append(arg)
      continue
    
    # Strip off any '@' part
    atPos = arg.find('@')
    if atPos == 0:
      path = cwd
    elif atPos > 0:
      path = arg[:atPos]
    else:
      path = arg

    if not os.path.isabs(path):
      path = os.path.join(cwd, path)
    # If it's a file or directory assume it's a script path.
    if os.path.exists(path):
      if atPos >= 0:
        targetNames = arg[atPos + 1:].split(',')
      else:
        targetNames = None

      scriptTargets.append((path, targetNames))
    else:
      newArgs.append(arg)
  args = newArgs

  # Default to building a script file in the working directory.    
  if not scriptTargets:
    scriptTargets.append((cwd, None))

  logger = cake.logging.Logger()
  engine = cake.engine.Engine(logger, parser, args)

  # Try to find an args.cake command line option.
  for arg in engine.args:
    if arg.startswith(argsCakeFlag):
      argsFileName = arg[len(argsCakeFlag):]
      if argsFileName:
        break
  else:
    # Try to find an args.cake by searching up from each script's directory.
    for scriptPath, targetNames in scriptTargets:
      # Script could be a file or directory name.
      if os.path.isdir(scriptPath):
        scriptDirName = scriptPath
      else:
        scriptDirName = os.path.dirname(scriptPath)
        
      argsFileName = engine.searchUpForFile(scriptDirName, "args.cake")
      if argsFileName:
        break
    else:
      argsFileName = None # No args.cake found.

  # Run the args.cake
  if argsFileName:
    script = cake.script.Script(
      path=argsFileName,
      configuration=None,
      variant=None,
      task=None,
      engine=engine,
      )
    # Don't cache args.cake as this is where the cache dir may be set.
    script.execute(cached=False)

  # Parse any remaining args (after args.cake may have modified them).
  options, args = parser.parse_args(engine.args)

  # Print out Cake version information if requested.
  if options.outputVersion:
    cakeVersion = cake.version.__version__
    cakePath = cake.path.dirName(cake.__file__)
    sys.stdout.write("Cake %s [%s]\n" % (cakeVersion, cakePath))
    sys.stdout.write("Python %s\n" % sys.version)
    return 1

  # Find keyword arguments from what's left of the args. 
  keywords = {}
  unknownArgs = []
  for arg in args:
    if '=' in arg:
      keyword, value = arg.split('=', 1)
      existingValues = keywords.setdefault(keyword, [])
      if value:
        existingValues.extend(value.split(','))
    else:
      unknownArgs.append(arg)

  if unknownArgs:
    parser.error("unknown args: %s" % " ".join(unknownArgs))
  
  # Set components to debug.
  for c in options.debugComponents.keywords:
    logger.enableDebug(c)
  logger.quiet = options.quiet
  
  engine.options = options
  engine.forceBuild = options.forceBuild
  engine.maximumErrorCount = options.maximumErrorCount
    
  threadPool = cake.threadpool.ThreadPool(options.jobs)
  cake.task.setThreadPool(threadPool)
 
  tasks = []
  
  configScript = options.config
  if configScript is not None and not os.path.isabs(configScript):
    configScript = os.path.abspath(configScript)
  
  bootFailed = False

  def listTargets(scripts):
    defaultTargets = []
    namedTargets = {}
    for script in scripts:
      defaultTargets.extend(flatten(script.getDefaultTarget().targets))
      for name, target in script._targets.items():
        namedTargets.setdefault(name, []).extend(flatten(target.targets))

    def targetList(targets):
      targets = sorted(set(str(t) for t in targets))
      if targets:
        return "".join("   -> " + t + "\n" for t in targets)
      else:
        return "   <no targets defined>\n"

    path = scripts[0].path

    message = "Targets for " + path + "\n"
    message += "  <default>\n"
    message += targetList(defaultTargets)
    for name in sorted(namedTargets.keys()):
      message += "  @" + name + "\n"
      message += targetList(namedTargets[name])

    logger.outputInfo(message)

  for scriptPath, targetNames in scriptTargets:
    scriptPath = cake.path.fileSystemPath(scriptPath)
    try:
      if configScript is None:
        configuration = engine.findConfiguration(scriptPath)
      else:
        configuration = engine.getConfiguration(configScript)

      variants = configuration.findAllVariants(keywords)

      scripts = [configuration.execute(scriptPath, variant)
                 for variant in variants] 
      if options.listTargetsMode:
        scriptTasks = [s.task for s in scripts]
        task = engine.createTask(lambda s=scripts: listTargets(scripts))
        task.startAfter(scriptTasks)
        tasks.append(task)
      else:
        if targetNames:
          for script in scripts:
            tasks.extend(script.getTarget(targetName).task
                         for targetName in targetNames)
        else:
          for script in scripts:
            tasks.append(script.getDefaultTarget().task)
    except cake.engine.BuildError:
      # Error already output
      bootFailed = True
    except Exception:
      bootFailed = True
      msg = traceback.format_exc()
      engine.logger.outputError(msg)
      engine.errors.append(msg)
    
  def onFinish():
    if not bootFailed and mainTask.succeeded:
      engine.onBuildSucceeded()
      if engine.warningCount:
        msg = "Build succeeded with %i warnings.\n" % engine.warningCount
      else:
        msg = "Build succeeded.\n"
    else:
      engine.onBuildFailed()
      if engine.warningCount:
        msg = "Build failed with %i errors and %i warnings.\n" % (
          engine.errorCount,
          engine.warningCount,
          )
      else:
        msg = "Build failed with %i errors.\n" % engine.errorCount
        
      if engine.failedTargets:
        msg += "The following targets failed to build:\n"
        if len(engine.failedTargets) >= 20:
          extraCount = len(engine.failedTargets) - 16
          targetsToPrint = engine.failedTargets[:16]
          targetsToPrint.append('... %i more targets ...' % extraCount)
        else:
          targetsToPrint = engine.failedTargets

        msg += "".join("- " + t + "\n" for t in targetsToPrint)

    engine.logger.outputInfo(msg)
  
  mainTask = cake.task.Task()
  mainTask.addCallback(onFinish)
  mainTask.startAfter(tasks)

  finished = threading.Event()
  mainTask.addCallback(finished.set)
  # We must wait in a loop in case a KeyboardInterrupt comes.
  while not finished.isSet():
    time.sleep(0.1)
  
  endTime = datetime.datetime.utcnow()
  engine.logger.outputInfo(
    "Build took %s.\n" % _formatTimeDelta(endTime - startTime)
    )
  
  return engine.errorCount

def _formatTimeDelta(t):
  """Return a string representation of the time to millisecond precision."""
  
  hours = t.seconds // 3600
  minutes = (t.seconds / 60) % 60
  seconds = t.seconds % 60
  milliseconds = t.microseconds // 1000

  if t.days:
    return "%i days, %i:%02i:%02i.%03i" % (
      t.days, hours, minutes, seconds, milliseconds)
  else:
    return "%i:%02i:%02i.%03i" % (hours, minutes, seconds, milliseconds)
