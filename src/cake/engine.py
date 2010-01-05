import threading
import cake.bytecode
import cake.builders
import cake.task

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
  
  def clone(self):
    cls = self.__class__
    new = cls()
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
      script, task = self._executed[key]
    else:
      script = Script(path=path, variant=variant, engine=self)
      def execute():
        cake.builders.__dict__.clear()
        for name, tool in variant.tools.items():
          setattr(cake.builders, name, tool.clone())
        script.execute()
      task = cake.task.Task(execute)
      self._executed[key] = (script, task)
      task.start()

    callingRootScript = Script.getCurrentRoot()
    if callingRootScript is not None:
      callingKey = callingRootScript.path, callingRootScript.variant
      _, callingTask = self._executed[callingKey]
      callingTask.completeAfter(task)
      
    return task
    
  def getByteCode(self, path):
    byteCode = self._byteCodeCache.get(path, None)
    if byteCode is None:
      byteCode = cake.bytecode.loadCode(path)
      self._byteCodeCache[path] = byteCode
    return byteCode
    
class Script(object):
  
  _current = threading.local()
  
  def __init__(self, path, variant, engine, parent=None):
    self.path = path
    self.variant = variant
    self.engine = engine
    if parent is None:
      self._included = {self.path : self}
    else:
      self._included = parent._included

  @staticmethod
  def getCurrent():
    return getattr(Script._current, "value", None)
  
  @staticmethod
  def getCurrentRoot():
    current = Script.getCurrent()
    if current is not None:
      return current.root
    else:
      return None

  @property
  def root(self):
    """The root script of the execution tree.
    """
    result = self
    while result.parent is not None:
      result = result.parent
    return result

  def include(self, path):
    if path in self._included:
      return
      
    includedScript = Script(path, self.variant, self.engine, parent=self)
    self._included[path] = includedScript
    includedScript.execute()
    
  def execute(self):
    byteCode = self.engine.getByteCode(self.path)
    old = Script.getCurrent()
    Script._current.value = self
    try:
      exec byteCode
    finally:
      Script._current.value = old
