
class Declare(object):
  def __init__(self, default):
    self.default = default

class ToolMetaclass(type):
  """This metaclass ensures that new instance variables can only be added to
  an instance during its __init__.
  """
  
  def __init__(cls, name, bases, dct):
    super(ToolMetaclass, cls).__init__(name, bases, dct)
    
    cls._initCount = 0
    
    oldInit = cls.__init__
    def __init__(self, *args, **kwargs):
      self._initCount = self._initCount + 1
      oldInit(self, *args, **kwargs)
      self._initCount = self._initCount - 1
    cls.__init__ = __init__
      
    oldSetattr = cls.__setattr__
    def __setattr__(self, name, value):
      if not self._initCount and not hasattr(self, name):
        raise AttributeError(name)
      oldSetattr(self, name, value)
    cls.__setattr__ = __setattr__

class Tool(object):
  """Base class for user-defined Cake tools.
  """
  
  __metaclass__ = ToolMetaclass
  
  def clone(self):
    """Return an independent clone of this tool.
    
    The default clone behaviour performs a shallow copy of the
    member variables of the tool. You should override this method
    if you need a more sophisticated clone.
    """
    new = self.__class__()
    new.__dict__ = deepCopyBuiltins(self.__dict__)
    return new

class FileTarget(object):
  
  def __init__(self, path, task):
    self.path = path
    self.task = task

def getPathAndTask(file):
  if isinstance(file, FileTarget):
    return file.path, file.task
  else:
    return file, None

def getPathsAndTasks(files):
  paths = []
  tasks = []
  for f in files:
    if isinstance(f, FileTarget):
      paths.append(f.path)
      tasks.append(f.task)
    else:
      paths.append(f)
  return paths, tasks

def deepCopyBuiltins(obj):
  if isinstance(obj, dict):
    return dict((deepCopyBuiltins(k), deepCopyBuiltins(v)) for k, v in obj.iteritems())
  elif isinstance(obj, (list, tuple, set)):
    return type(obj)(deepCopyBuiltins(i) for i in obj)
  else:
    return obj
