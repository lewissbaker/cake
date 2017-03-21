"""Script Tool.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import os.path

from cake.target import Target, FileTarget, getPaths, getTask
from cake.library import Tool
from cake.script import Script

class ScriptTool(Tool):
  """Tool that provides utilities for performing Script operations.
  """
  
  def __init__(self, *args, **kwargs):
    Tool.__init__(self, *args, **kwargs)
    self._included = {}
  
  @property
  def path(self):
    """The path of the currently executing script.
    """
    return Script.getCurrent().path
  
  @property
  def dir(self):
    """The path of the directory of the currently executing script.
    """
    return Script.getCurrent().dir
  
  @property
  def variant(self):
    """The Variant the currently executing script is being built with.
    """
    return Script.getCurrent().variant

  def setResult(self, **kwargs):
    """Export a result from this script that other scripts can import.
    
    Other scripts can use getResult(script, name) to get the result
    exported by the other script calling setResult(name=result).
    """
    Script.getCurrent().setResult(**kwargs)
  
  def getResult(self, script, name, *args, **kwargs):
    """Get a placeholder value that will yield the result of another
    script once that other script has finished executing.
    """
    return self.get(script).getResult(name, *args, **kwargs)
  
  def getTarget(self, name):
    """Get the named ScriptTarget for this script.

    @param name: The name of the target to get.
    @type name: C{str}
    """
    return Script.getCurrent().getTarget(name)

  def getDefaultTarget(self):
    return Script.getCurrent().getDefaultTarget()

  def addDefaultTarget(self, target):
    """Add a target to be built when the default target for this script is built.

    @param target: The target to be built.
    @type target: L{Target} or L{AsyncResult} that yields a L{Target}
    """
    Script.getCurrent().getDefaultTarget().addTarget(target)

  def addDefaultTargets(self, targets):
    """Add a collection of targets to the default script target.

    The default script target is the target that is built when the user
    executes the current build script without specifying a particular target name.

    @param targets: A collection of targets to be built.
    @type targets: A list of L{Target} or L{AsyncResult} yielding a list of L{Target}   
    """
    Script.getCurrent().getDefaultTarget().addTargets(targets)

  def addTarget(self, name, target):
    """Add a target to the named script target.

    The specified target will be built whenever the named script target is
    built.

    @param name: The name of the script-target to add the target to.
    @type name: C{str}

    @param target: A target to build when the named script-target is
    built.
    @type target: L{Target} or L{AsyncResult} yielding a L{Target}
    """
    Script.getCurrent().getTarget(name).addTarget(target)

  def addTargets(self, name, targets):
    """Add a collection of targets to the named script target.

    The specified targets will be built whenever the named script target is
    requested to be built.

    @param name: The name of the script-target to add the targets to.
    @type name: C{str}

    @param target: A target to build when the named script-target is
    built.
    @type target: L{Target} or L{AsyncResult} yielding a L{Target}

    """
    Script.getCurrent().getTarget(name).addTargets(targets)

  def get(self, script, keywords={}, useContext=None, configScript=None, configScriptName=None):
    """Get another script to use in referencing targets.
    
    @param script: Path of the script to load.
    @type script: string
    
    @param keywords: A set of keywords used to find the variant the script
    will be executed with. The variant is looked up in the script's configuration.
    @type keywords: dictionary of string -> string
    
    @param useContext: If False or if None and either configScript or configScriptName
    are not None then lookup the corresponding configuration script starting from the
    script's path, if True then use the current configuration/variant.
    @type useContext: bool or None
    
    @param configScript: The path of the configuration script to use to execute the script.
    Ignored if useContext is True.
    @type configScript: string or None
    
    @param configScriptName: If not None and configScript is None then find the
    configuration script with this name starting the search at the script's path.
    Ignored if useContext is True.
    @type configScriptName: string or None
    """
    if not isinstance(script, basestring):
      raise ValueError("'script' must be a string")
   
    script = self.configuration.basePath(script)
  
    if useContext is None:
      useContext = configScript is None and configScriptName is None
  
    if useContext:
      # Use the current configuration and lookup the variant relative
      # to the current variant.
      baseVariant = Script.getCurrent().variant
      variant = self.configuration.findVariant(keywords, baseVariant=baseVariant)
      return ScriptProxy(self.configuration.execute(path=script, variant=variant))
    else:
      # Re-evaluate the configuration to execute the script with.
      # Uses the keywords specified to find the variant in the variants
      # defined in that configuration.
      path = self.configuration.abspath(script)
      if configScript is None:
        configuration = self.engine.findConfiguration(
          path=path,
          configScriptName=configScriptName,
          )
      else:
        configuration = self.engine.getConfiguration(
          path=self.configuration.abspath(configScript),
          )
      variant = configuration.findVariant(keywords)
      return ScriptProxy(configuration.execute(path=path, variant=variant))

  def cwd(self, *args):
    """Return the path prefixed with the this script's directory.
    
    Examples::
      env.cwd("a") -> "{cwd}/a"
      env.cwd(["a", "b", "c"]) -> ["{cwd}/a", "{cwd}/b", "{cwd}/c"]
      
    @param args: The arguments that need to have the prefix added.
    @type args: string or list(string)
    
    @return: The path prefixed with this script's directory.
    @rtype: string or list(string)
    """
    script = Script.getCurrent()
    return script.cwd(*args)
    
  def include(self, scripts):
    """Include another script within the context of the currently
    executing script.
    
    A given script will only be included once.
    
    @param scripts: A path or sequence of paths of scripts to include.
    @type scripts: string or sequence of string
    """
    basePath = self.configuration.basePath
    
    scripts = basePath(scripts)
    
    include = self._include
    if isinstance(scripts, basestring):
      include(scripts)
    else:
      for path in scripts:
        include(path)

  def _include(self, path):
    """Include another script for execution within this script's context.
    
    A script will only be included once within a given context.
    
    @param path: The path of the file to include.
    @type path: string
    """
    path = os.path.normpath(path)
    
    normalisedPath = os.path.normcase(self.configuration.abspath(path))

    if normalisedPath in self._included:
      return
      
    currentScript = Script.getCurrent()
    includedScript = Script(
      path=path,
      variant=currentScript.variant,
      engine=currentScript.engine,
      configuration=currentScript.configuration,
      task=currentScript.task,
      tools=currentScript.tools,
      parent=currentScript,
      )
    self._included[normalisedPath] = includedScript
    
    try:
      includedScript.execute()
    except IOError, e:
      currentScript.engine.raiseError(
        ("Failed to include cake script %s: %s\n" % (path, str(e))) +
        "".join("  from " + s.path + "\n" for s in currentScript.getAncestors()))
    
  def execute(self, scripts, **keywords):
    """Execute another script as a background task.

    Executes the other script using the current script's configuration
    but potentially a different build variant.
    
    If you need to execute a script using a different configuration
    then use the 'executeNoContext' method instead. 

    @param scripts: A path or sequence of paths of scripts to execute.
    @type scripts: string or sequence of string

    @return: A Script object or sequence of Script objects that can be used
    to determine what scripts will be executed. The script's task will
    complete when the script has finished executing.
    @rtype: L{Script} or C{list} of L{Script}
    """
    basePath = self.configuration.basePath
    
    scripts = basePath(scripts)
    
    script = Script.getCurrent()
    configuration = script.configuration
    variant = configuration.findVariant(keywords, baseVariant=script.variant)
    execute = configuration.execute
    def _execute(path):
      script = execute(path, variant)
      self.addDefaultTarget(script.getDefaultTarget())
      return ScriptProxy(script)

    if isinstance(scripts, basestring):
      return _execute(scripts)
    else:
      return [_execute(path) for path in scripts]

  def run(self, func, args=None, targets=None, sources=[]):
    """Execute the specified python function as a task.

    Only executes the function after the sources have been built and only
    if the target exists, args is the same as last run and the sources
    haven't changed.

    @note: I couldn't think of a better class to put this function in so
    for now it's here although it doesn't really belong.
    """
    engine = self.engine
    configuration = self.configuration

    basePath = configuration.basePath
    
    targets = basePath(targets)
    sources = basePath(sources)

    def _run():
      sourcePaths = getPaths(sources)
      if targets:
        buildArgs = (args, sourcePaths)
        try:
          _, reason = configuration.checkDependencyInfo(
            targets[0],
            buildArgs,
            )
          if reason is None:
            # Up to date
            return
          
          engine.logger.outputDebug(
            "reason",
            "Building '%s' because '%s'\n" % (targets[0], reason),
            )
        except EnvironmentError:
          pass

      try:
        result = func()
      except Exception:
        if targets:
          append = engine.failedTargets.append
          for t in targets:
            append(t)
        raise
      
      if targets:
        newDependencyInfo = configuration.createDependencyInfo(
          targets=targets,
          args=buildArgs,
          dependencies=sourcePaths,
          )
        configuration.storeDependencyInfo(newDependencyInfo)
        
      return result

    if self.enabled:
      task = engine.createTask(_run)
      task.lazyStartAfter(getTask(sources))
    else:
      task = None

    currentScript = Script.getCurrent()

    if targets is not None:
      targets = [FileTarget(path=t, task=task) for t in targets]
      currentScript.getDefaultTarget().addTargets(targets)
      return targets
    else:
      target = Target(task)
      currentScript.getDefaultTarget().addTarget(target)
      return target

class ScriptProxy:
  """Proxy class for a Script instance that limits what
  you can do with a script.

  This object is returned from ScriptTool.get() and ScriptTool.execute().
  """

  def __init__(self, script):
    self._script = script

  def execute(self):
    """Executing a script is shorthand for adding it's default
    targets to your default targets. This means it will only actually
    run if the current script's default target is built.
    """
    Script.getCurrent().getDefaultTarget().addTarget(
      self._script.getDefaultTarget())

  def getTarget(self, name):
    """Get the named target of a script.

    @param name: The name of the target.
    @type name: C{str}

    @return: A target corresponding to the named target defined
    by this script.
    @rtype: L{ScriptTarget}
    """
    return self._script.getTarget(name)

  def getDefaultTarget(self):
    """Get the default target for this script.

    This is the target that will be built if the script is built
    from the command-line without specifying a particular named target.

    @rtype: L{ScriptTarget}
    """
    return self._script.getDefaultTarget()

  def getResult(self, name):
    """Get the result output of a script.

    This will be an AsyncResult value that allows one script to consume
    a programmatic output from another script.

    @rtype: L{ScriptResult}
    """
    return self._script.getResult(name)
