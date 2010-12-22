"""Shell Tool.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import os
import subprocess
import cake.filesys
import cake.path
from cake.library import Tool, FileTarget, deepCopyBuiltins, getPaths, getTasks

_undefined = object()

class ShellTool(Tool):

  def __init__(self, configuration, env=None):
    Tool.__init__(self, configuration)
    if env is None:
      self.__env = dict(os.environ)
    else:
      self.__env = dict(env)

  def run(self, args, targets=None, sources=[], cwd=None):

    engine = self.engine
    env = deepCopyBuiltins(self.__env)

    def spawnProcess(cwd=cwd):

      sourcePaths = getPaths(sources)
      configuration = self.configuration
      abspath = configuration.abspath

      if isinstance(args, basestring):
        argsString = args
        argsList = [args]
        executable = None
      else:
        argsString = " ".join(args)
        argsList = args
        executable = abspath(args[0])
        
      if targets:
        # Check dependencies to see if they've changed
        buildArgs = argsList + sourcePaths + targets
        try:
          _, reasonToBuild = configuration.checkDependencyInfo(
            targets[0],
            buildArgs,
            )
          if reasonToBuild is None:
              # Target is up to date, no work to do
              return
        except EnvironmentError:
          pass
        
        engine.logger.outputDebug(
          "reason",
          "Rebuilding '%s' because %s.\n" % (targets[0], reasonToBuild),
          )
      
      # Create target directories first
      if targets:
        for t in targets:
          cake.filesys.makeDirs(cake.path.dirName(abspath(t)))

      if cwd is None:
        cwd = configuration.baseDir
      else:
        cwd = abspath(cwd)

      # Output the command-line we're about to run.
      engine.logger.outputInfo("Running %s\n" % argsList[0])

      engine.logger.outputDebug(
        "run",
        "run: %s\n" % argsString,
        )

      try:
        p = subprocess.Popen(
          args=args,
          executable=executable,
          env=env,
          stdin=subprocess.PIPE,
          cwd=cwd,
          )
      except EnvironmentError, e:
        msg = "cake: failed to launch %s: %s\n" % (argsList[0], str(e))
        engine.raiseError(msg)

      p.stdin.close()
      exitCode = p.wait()
      
      if exitCode != 0:
        msg = "%s exited with code %i\n" % (argsList[0], exitCode)
        engine.raiseError(msg)

      if targets:
        newDependencyInfo = configuration.createDependencyInfo(
          targets=targets,
          args=buildArgs,
          dependencies=sourcePaths,
          )
        configuration.storeDependencyInfo(newDependencyInfo)

    if self.enabled:
      tasks = getTasks(sources)

      task = engine.createTask(spawnProcess)
      task.startAfter(tasks)
    else:
      task = None

    if targets is None:
      return task
    else:
      return [FileTarget(path=t, task=task) for t in targets]

  def __iter__(self):
    return iter(self.__env)

  def keys(self):
    return self.__env.keys()

  def items(self):
    return self.__env.items()

  def update(self, value):
    return self.__env.update(value)

  def get(self, key, default=_undefined):
    if default is _undefined:
      return self.__env.get(key)
    else:
      return self.__env.get(key, default)

  def __getitem__(self, key):
    return self.__env[key]

  def __setitem__(self, key, value):
    self.__env[key] = value

  def __delitem__(self, key):
    del self.__env[key]

  def appendPath(self, path):
    pathEnv = self.get('PATH', None)
    if pathEnv is None:
      pathEnv = path
    else:
      pathEnv = os.pathsep.join((pathEnv, path))
    self['PATH'] = pathEnv

  def prependPath(self, path):
    pathEnv = self.get('PATH', None)
    if pathEnv is None:
      pathEnv = path
    else:
      pathEnv = os.pathsep.join((path, pathEnv))
    self['PATH'] = pathEnv
