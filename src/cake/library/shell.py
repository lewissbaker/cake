"""Shell Tool.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import os
import subprocess
import cake.filesys
import cake.path
from cake.async_util import waitForAsyncResult, flatten
from cake.target import Target, FileTarget, getPaths, getTasks
from cake.library import Tool
from cake.script import Script

_undefined = object()

class ShellTool(Tool):

  def __init__(self, configuration, env=None):
    Tool.__init__(self, configuration)
    if env is None:
      self._env = dict(os.environ)
    else:
      self._env = dict(env)

  def run(self, args, targets=[], sources=[], cwd=None, shell=False, removeTargets=False):
    """Run a shell command to build specified targets.

    @param args: The command-line to run.
    Either a list of strings, one item per argument, or a single string.
    @type args: string or list of string

    @param targets: If specified then a list of the target file paths that
    will be generated by this shell command.

    @param sources: If specified then a list of the sources for building
    the target. If any of these sources change then the command will be
    re-executed.

    @param cwd: The directory to spawn the shell command in.
    If not specified then uses the configuration.baseDir.

    @param shell: Whether to run this command using the default shell,
    eg. '/bin/sh' or 'cmd.exe'.

    @param removeTargets: If specified then the target files will be removed
    before running the command if they already exist.
    """
    tool = self.clone()
    
    basePath = self.configuration.basePath
   
    return tool._run(args, basePath(targets), basePath(sources), basePath(cwd), shell, removeTargets)
  
  def _run(self, args, targets, sources, cwd, shell, removeTargets):

    engine = self.engine
    
    def spawnProcess(targets, sources, cwd):

      sourcePaths = getPaths(sources)
      configuration = self.configuration
      abspath = configuration.abspath

      if isinstance(args, str):
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
          absT = abspath(t)
          
          try:
            cake.filesys.makeDirs(cake.path.dirName(absT))
          except Exception as e:
            msg = "cake: Error creating target directory %s: %s\n" % (
              cake.path.dirName(t), str(e))
            engine.raiseError(msg, targets=targets)
            
          if removeTargets:
            try:
              cake.filesys.remove(absT)
            except Exception as e:
              msg = "cake: Error removing old target %s: %s\n" % (
                t, str(e))
              engine.raiseError(msg, targets=targets)

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
          env=self._env,
          stdin=subprocess.PIPE,
          shell=shell,
          cwd=cwd,
          )
      except EnvironmentError as e:
        msg = "cake: failed to launch %s: %s\n" % (argsList[0], str(e))
        engine.raiseError(msg, targets=targets)

      p.stdin.close()
      exitCode = p.wait()
      
      if exitCode != 0:
        msg = "%s exited with code %i\n" % (argsList[0], exitCode)
        engine.raiseError(msg, targets=targets)

      if targets:
        newDependencyInfo = configuration.createDependencyInfo(
          targets=targets,
          args=buildArgs,
          dependencies=sourcePaths,
          )
        configuration.storeDependencyInfo(newDependencyInfo)

    @waitForAsyncResult
    def _run(targets, sources, cwd):
      if self.enabled:
        task = engine.createTask(lambda t=targets, s=sources, c=cwd: spawnProcess(t, s, c))
        task.lazyStartAfter(getTasks(sources))
      else:
        task = None
  
      if targets:
        targets = [FileTarget(path=t, task=task) for t in targets]
        Script.getCurrent().getDefaultTarget().addTargets(targets)
        return targets
      else:
        target = Target(task)
        Script.getCurrent().getDefaultTarget().addTarget(target)
        return target
    
    return _run(flatten(targets), flatten(sources), cwd)

  def __iter__(self):
    return iter(self._env)

  def keys(self):
    return self._env.keys()

  def items(self):
    return self._env.items()

  def update(self, value):
    return self._env.update(value)

  def get(self, key, default=_undefined):
    if default is _undefined:
      return self._env.get(key)
    else:
      return self._env.get(key, default)

  def __getitem__(self, key):
    return self._env[key]

  def __setitem__(self, key, value):
    self._env[key] = value

  def __delitem__(self, key):
    del self._env[key]

  def appendPath(self, path):
    basePath = self.configuration.basePath
    
    path = basePath(path)

    pathEnv = self.get('PATH', None)
    if pathEnv is None:
      pathEnv = path
    else:
      pathEnv = os.pathsep.join((pathEnv, path))
    self['PATH'] = pathEnv

  def prependPath(self, path):
    basePath = self.configuration.basePath
    
    path = basePath(path)
        
    pathEnv = self.get('PATH', None)
    if pathEnv is None:
      pathEnv = path
    else:
      pathEnv = os.pathsep.join((path, pathEnv))
    self['PATH'] = pathEnv
