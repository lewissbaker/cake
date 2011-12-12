"""Environment Tool.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import cake.path

from cake.library import Tool

def _coerceToList(value):
  if isinstance(value, list):
    return value
  return [value]

class EnvironmentTool(Tool):
  """
  Tool that provides a dictionary of key/value pairs
  used for path substitution.
  """
  
  def __init__(self, configuration):
    """Default constructor.
    """
    Tool.__init__(self, configuration)
    self.vars = {}
    
  def __getitem__(self, key):
    """Return an environment variables value given its key.
    
    @param key:  The key of the environment variable to get.
    @return: The value of the environment variable.
    """
    return self.vars[key]
  
  def __setitem__(self, key, value):
    """Set a new value for an environment variable.
    
    @param key: The key of the environment variable to set.
    @param value: The value to set the environment variable to.
    """
    self.vars[key] = value
    
  def __delitem__(self, key):
    """Delete an environment variable given its key.
    
    @param key: The key of the environment variable to delete. 
    """
    del self.vars[key]

  def __contains__(self, key):
    """Test if an environment variable is defined.

    @param key: The key of the environment variable to test.
    """
    return key in self.vars

  def get(self, key, default=None):
    """Return an environment variable or default value if not found.
    
    @param key: The key of the environment variable to get.
    @param default: The value to return if the key is not found.
    """
    return self.vars.get(key, default)

  def setDefault(self, key, default=None):
    """Set a value only if it doesn't already exist.
    """
    return self.vars.setdefault(key, default)
      
  def update(self, *values, **kwargs):
    """Update the environment with key/value pairs from 'values' or 'kwargs'.
    
    If a matching key already exists its value will be replaced by the value
    passed in. 

    Note that if the key/value pairs come from 'kwargs' they must conform to
    Python keyword argument naming conventions (eg. no spaces).
    
    Example::
      env.update({
        "CODE_PATH":"c:/code",
        "ART_PATH":"c:/art",
        })
      env.update(
        CODE_PATH="C:/code",
        ART_PATH="C:/art",
        )
    @param values: An iterable sequence of key/value pairs to update from.
    """
    self.vars.update(*values, **kwargs)
    
  def expand(self, value):
    """Expand variables in the specified string.
    
    Variables that are expanded are of the form ${VAR}
    or $VAR.

    Example::
      env["CODE_PATH"] = "c:/code"
      env.expand("${CODE_PATH}/a") -> "C:/code/a"
      
    @param value: The string to expand.
    @type value: string
    @return: The expanded string.
    @rtype: string
    """
    return cake.path.expandVars(value, self.vars)

  def append(self, **kwargs):
    """Append keyword arguments to the environment. If the key does not exist
    the value passed in is used. If the key does exist the value is appended using
    the '+' operator.

    Example::
      env.append(
        CFLAGS=["/O1"],
        MESSAGE="Added /O1 flag. ",
        )
    """
    for k, v in kwargs.iteritems():
      try:
        old = self.vars[k]
        if type(old) != type(v):
          old = _coerceToList(old)
          v = _coerceToList(v)
        self.vars[k] = old + v
      except KeyError:
        self.vars[k] = v

  def prepend(self, **kwargs):
    """Prepend keyword arguments to the environment. If the key does not exist
    the value passed in is used. If the key does exist the value is prepended using
    the '+' operator.

    Example::
      env.prepend(
        CFLAGS=["/O1"],
        MESSAGE="Added /O1 flag. ",
        )
    """
    for k, v in kwargs.iteritems():
      try:
        old = self.vars[k]
        if type(old) != type(v):
          old = _coerceToList(old)
          v = _coerceToList(v)
        self.vars[k] = v + old
      except KeyError:
        self.vars[k] = v

  def replace(self, **kwargs):
    """Replace key/values in the environment with keyword arguments. 

    This function is identical to the set() function.
    
    Example::
      env.set(
        CODE_PATH="C:/code",
        ART_PATH="C:/art",
        )
    """
    self.vars.update(kwargs)
