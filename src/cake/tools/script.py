import cake.engine

class ScriptTool(cake.engine.Tool):
  """Builder that provides utilities for performing Script operations.
  """
  
  def clone(self):
    # Optimisation because this class has no state
    # Remove this if it starts storing any member variables.
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
