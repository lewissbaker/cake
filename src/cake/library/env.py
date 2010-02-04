"""Environment Tool.
"""

import cake.path

from cake.library import Tool

class Environment(Tool):
  """A dictionary of key/value pairs used for path substitution.
  """
  
  def __init__(self):
    """Default constructor.
    """
    self.__vars = {}
    
  def __getitem__(self, key):
    """Return an environment variables value given its key.
    """
    return self.__vars[key]
  
  def __setitem__(self, key, value):
    """Set a new value for an environment variable.
    """
    self.__vars[key] = value
    
  def __delitem__(self, key):
    """Delete an environment variable given its key. 
    """
    del self.__vars[key]

  def get(self, *args):
    """Return an environment variable or default value if not found.
    """
    return self.__vars.get(*args)

  def set(self, **kwargs):    
    """Set a series of keys/values.
    """
    self.__environment.update(kwargs)
    
  def setDefault(self, **kwargs):
    """Set a value only if it doesn't already exist.
    """
    for key, value in kwargs.iteritems():
      self.__vars.setdefault(key, value)

  def delete(self, *arguments):    
    """Delete a value.
    """
    for a in arguments:
      del self.__vars[a]
      
  def update(self, values):
    """Update the environment with key/value pairs from 'values'.
    """
    self.__vars.update(values)
    
  def expand(self, value):
    """Expand variables in the specified string.
    """
    return cake.path.expandVars(value, self.__vars)
