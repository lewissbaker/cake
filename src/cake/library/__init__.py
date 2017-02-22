"""Base Class and Utilities for Cake Tools.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

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

def memoise(func):
  """Decorator that can be placed on Tool methods to memoise the result.
  
  The result cache is invalidated whenever an attribute is set on the
  instance.
  
  @param func: The function to memoise.
  @type func: function
  """
  
  undefined = object()
  def run(*args, **kwargs):
    kwargsTuple = tuple((k,v) for k, v in kwargs.iteritems())
    
    self = args[0]
    key = (func, args[1:], kwargsTuple)

    cache = self._Tool__memoise
    result = cache.get(key, undefined)
    if result is undefined:
      result = func(*args, **kwargs)
      cache[key] = result
    return result
  
  try:
    run.func_name = func.func_name
    run.func_doc = func.func_doc
  except AttributeError:
    pass
  
  return run

class Tool(object):
  """Base class for user-defined Cake tools.
  """
  
  __metaclass__ = ToolMetaclass
  
  enabled = True
  """Enabled/disable this tool.
  
  If the tool is disabled it should not produce any output files but
  it should still return the paths to those potential output files so
  other tools can use them.
  
  @type: bool
  """
  
  def __init__(self, configuration):
    self.__memoise = {}
    self.configuration = configuration
    self.engine = configuration.engine
  
  def __setattr__(self, name, value):
    if name != '_Tool__memoise' and hasattr(self, '_Tool__memoise'):
      self._clearCache()
    super(Tool, self).__setattr__(name, value)
  
  def _clearCache(self):
    """Clear the memoise cache due to some change.
    """
    self.__memoise.clear()
  
  def clone(self):
    """Return an independent clone of this tool.
    
    The default clone behaviour performs a deep copy of any builtin
    types, and a clone of any Tool-derived objects. Everything else
    will be shallow copied. You should override this method if you
    need a more sophisticated clone.
    """
    new = object.__new__(self.__class__)
    new.__dict__ = cloneTools(self.__dict__)
    return new

def cloneTools(obj):
  """Return a deep copy of any Tool-derived objects or builtin types.

  @param obj: The given object to copy.
  @return: A copy of the given object for Tool-dervied or builtin types,
  and references to the same object for user-defined types.
  """
  if isinstance(obj, Tool):
    return obj.clone()
  elif isinstance(obj, dict):
    return dict((cloneTools(k), cloneTools(v)) for k, v in obj.iteritems())
  elif isinstance(obj, (list, tuple, set)):
    return type(obj)(cloneTools(i) for i in obj)
  else:
    return obj
