"""Script Tool.
"""

from cake.engine import Script
from cake.library import Tool

class ScriptTool(Tool):
  """Builder that provides utilities for performing Script operations.
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
    
  def execute(self, scripts):
    """Execute another script as a background task.

    @param scripts: A path or sequence of paths of scripts to execute.
    @type scripts: string or sequence of string

    @return: A task or sequence of tasks that can be used to determine
      when all tasks created by the script have finished executing.
    @rtype: L{Task} or C{list} of L{Task}
    """
    execute = Script.getCurrent().engine.execute
    if isinstance(scripts, basestring):
      return execute(scripts)
    else:
      return [execute(path) for path in scripts]
