"""Script Tool.
"""

from cake.engine import Script, DependencyInfo, FileInfo
from cake.library import Tool, FileTarget, getPathsAndTasks

class ScriptTool(Tool):
  """Tool that provides utilities for performing Script operations.
  """
  
  def include(self, scripts):
    """Include another script within the context of the currently
    executing script.
    
    A given script will only be included once.
    
    @param scripts: A path or sequence of paths of scripts to include.
    @type path: string or sequence of string
    """
    include = Script.getCurrent().include
    if isinstance(scripts, basestring):
      include(scripts)
    else:
      for path in scripts:
        include(path)
    
  def execute(self, scripts, **keywords):
    """Execute another script as a background task.

    @param scripts: A path or sequence of paths of scripts to execute.
    @type scripts: string or sequence of string

    @return: A task or sequence of tasks that can be used to determine
      when all tasks created by the script have finished executing.
    @rtype: L{Task} or C{list} of L{Task}
    """
    engine = Script.getCurrent().engine
    variant = engine.findVariant(**keywords)
    execute = engine.execute
    if isinstance(scripts, basestring):
      return execute(scripts, variant)
    else:
      return [execute(path) for path in scripts]

  def run(self, func, args=None, targets=None, sources=[]):
    """Execute the specified python function as a task.

    Only executes the function after the sources have been built and only
    if the target exists, args is the same as last run and the sources
    havent changed.

    @note: I couldn't think of a better class to put this function in so
    for now it's here although it doesn't really belong.
    """
    script = Script.getCurrent()
    engine = script.engine

    sourcePaths, sourceTasks = getPathsAndTasks(sources)

    def _run():

      if targets:
        buildArgs = (args, sourcePaths)
        try:
          oldDependencyInfo = engine.getDependencyInfo(targets[0])
          if oldDependencyInfo.isUpToDate(engine, buildArgs):
            return
        except EnvironmentError:
          pass

      func()

      if targets:
        newDependencyInfo = DependencyInfo(
          targets=[FileInfo(path=t) for t in targets],
          args=buildArgs,
          dependencies=[
            FileInfo(
              path=s,
              timestamp=engine.getTimestamp(s),
              )
            for s in sourcePaths
            ],
          )
        engine.storeDependencyInfo(newDependencyInfo)

    task = engine.createTask(_run)
    task.startAfter(sourceTasks)

    if targets is not None:
      return [FileTarget(path=t, task=task) for t in targets]
    else:
      return task
