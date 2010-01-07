import threading
import os.path

import cake.bytecode
import cake.builders
import cake.task
import cake.path

class Variant(object):
  
  def __init__(self, name):
    self.name = name
    self.tools = {}
    self.env = {}
  
  def clone(self):
    v = Variant()
    v.env = self.env.copy()
    v.tools = dict((name, tool.clone()) for name, tool in self.tools)
    return v

class Tool(object):
  """Base class for user-defined Cake tools.
  """
  
  def clone(self):
    """Return an independent clone of this tool.
    
    The default clone behaviour performs a shallow copy of the
    member variables of the tool. You should override this method
    if you need a more sophisticated clone.
    """
    new = self.__class__()
    new.__dict__ = self.__dict__.copy()
    return new

class Engine(object):
  """Main object that holds all of the singleton resources for a build.
  """
  
  def __init__(self):
    self._variants = set()
    self._defaultVariant = None
    self._byteCodeCache = {}
    self._executed = {}
  
  def addVariant(self, variant, default=False):
    """Register a new variant with this engine.
    """
    self._variants.add(variant)
    if default:
      self._defaultVariant = variant
    
  def execute(self, path, variant=None):
    """Execute the script with the specified variant.
    
    Return a task object that completes when the script and any
    tasks it starts finish executing.
    """
    if variant is None:
      variant = self._defaultVariant
    
    # TODO: Locks in here
    
    key = (path, variant)
    
    if key in self._executed:
      script = self._executed[key]
    else:
      def execute():
        cake.builders.__dict__.clear()
        for name, tool in variant.tools.items():
          setattr(cake.builders, name, tool.clone())
        script.execute()
      task = cake.task.Task(execute)
      script = Script(
        path=path,
        variant=variant,
        task=task,
        engine=self,
        )
      self._executed[key] = script
      task.start()

    return task
    
  def getScriptTask(self, script):
    key = ()
    
  def getByteCode(self, path):
    byteCode = self._byteCodeCache.get(path, None)
    if byteCode is None:
      byteCode = cake.bytecode.loadCode(path)
      self._byteCodeCache[path] = byteCode
    return byteCode
    
class Script(object):
  
  _current = threading.local()
  
  def __init__(self, path, variant, engine, task, parent=None):
    self.path = path
    self.dir = os.path.dirname(path)
    self.variant = variant
    self.engine = engine
    self.task = task
    if parent is None:
      self.root = self
      self._included = {self.path : self}
    else:
      self.root = parent.root
      self._included = parent._included

  @staticmethod
  def getCurrent():
    """Get the current thread's currently executing script.
    """
    return getattr(Script._current, "value", None)
  
  @staticmethod
  def getCurrentRoot():
    """Get the current thread's root script.
    
    This is the top-level script currently being executed.
    A script may not be the top-level script if it is executed due
    to inclusion from another script.
    """
    current = Script.getCurrent()
    if current is not None:
      return current.root
    else:
      return None

  def cwd(self, *args):
    """Return the path prefixed with the current script's directory.
    """
    return cake.path.join(self.dir, *args)

  def include(self, path):
    """Include another script for execution within this script's context.
    
    A script will only be included once within a given context.
    """
    if path in self._included:
      return
      
    includedScript = Script(
      path=path,
      variant=self.variant,
      engine=self.engine,
      task=self.task,
      parent=self,
      )
    self._included[path] = includedScript
    includedScript.execute()
    
  def execute(self):
    """Execute this script.
    """
    byteCode = self.engine.getByteCode(self.path)
    old = Script.getCurrent()
    Script._current.value = self
    try:
      exec byteCode
    finally:
      Script._current.value = old
