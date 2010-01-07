import cake.engine

class Environment(cake.engine.Tool):
  
  def __init__(self):
    self.__vars = {}
    
  def clone(self):
    new = self.__class__()
    new.__vars = self.__vars.copy()
    return new
    
  def __getitem__(self, key):
    """Return an environment variable given its key.
    """
    return self.__vars[key]
  
  def __setitem__(self, key, value):
    """Set a new value for an environment variable.
    """
    self.__vars[key] = value
    
  def __delitem__(self, key):
    del self.__vars[key]

  def get(self, *args):
    return self.__vars.get(*args)

  def set(self, **kwargs):
    self.__vars.update(kwargs)
    return self
    
  def setDefault(self, **kwargs):
    for key, value in kwargs.iteritems():
      self.__vars.setdefault(key, value)
    return self

  def update(self, values):
    self.__vars.update(values)
    return self
    
  def expand(self, value):
    """Expand variables in the specified string.
    """
    return cake.path.expandVars(value, self.__vars)
