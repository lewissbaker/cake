"""Script Tool.
"""

from cake.engine import Script
from cake.library import Tool

class ScriptTool(Tool):
  """Builder that provides utilities for performing Script operations.
  """
  
  def include(self, path=None, scripts=None):
    """Include another script within the context of the currently
    executing script.
    
    A given script will only be included once.
    
    @param path: The path of the script to include.
    @type path: string
    """
    script = Script.getCurrent()
    if path:
      return script.include(path)
    elif scripts:
      return [script.include(p) for p in scripts]
    
  def execute(self, path):
    """Execute another script as a background task.

    @return: A task that can be used to determine when all tasks created
    by the script have finished executing.
    @rtype: L{Task}  
    """
    script = Script.getCurrent()
    return script.engine.execute(path)
