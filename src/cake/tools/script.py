from cake.engine import Script
from cake.tools import Tool

class ScriptTool(Tool):
  """Builder that provides utilities for performing Script operations.
  """
  
  def include(self, path):
    """Include another script within the context of the currently
    executing script.
    
    A given script will only be included once.
    """
    script = Script.getCurrent()
    return script.include(path)
    
  def execute(self, path):
    """Execute another script as a background task.
    """
    script = Script.getCurrent()
    return script.engine.execute(path)
