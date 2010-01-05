import os.path
import cake.engine

class ScriptBuilder(object):
  """Builder that provides utilities for performing Script operations.
  """
  
  def clone(self):
    return self
  
  def include(self, path):
    """Include another script within the context of the currently
    executing script.
    
    A given script will only be included once.
    """
    script = cake.engine.Script.getCurrent()
    return script.include(path)
    
  def execute(self, path):
    """Execute another script as a background task.
    """
    script = cake.engine.Script.getCurrent()
    return script.engine.execute(path)
  
  def cwd(self, path):
    """Return the path prefixed with the current script's directory.
    """
    script = cake.engine.Script.getCurrent()
    scriptDir = os.path.dirname(script.path)
    return os.path.join(scriptDir, path)
