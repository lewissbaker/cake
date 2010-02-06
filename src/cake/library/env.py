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
    
    @param key:  The key of the environment variable to get.
    @return: The value of the environment variable.
    """
    return self.__vars[key]
  
  def __setitem__(self, key, value):
    """Set a new value for an environment variable.
    
    @param key: The key of the environment variable to set.
    @param value: The value to set the environment variable to.
    """
    self.__vars[key] = value
    
  def __delitem__(self, key):
    """Delete an environment variable given its key.
    
    @param key: The key of the environment variable to delete. 
    """
    del self.__vars[key]

  def get(self, key, default=None):
    """Return an environment variable or default value if not found.
    
    @param key: The key of the environment variable to get.
    @param default: The value to return if the key is not found.
    """
    return self.__vars.get(key, default)

  def set(self, **kwargs):    
    """Set a series of keys/values.
    
    Similar to update() except key/value pairs are taken directly
    from the keyword arguments.
    
    Note that this means keys must conform to Python keyword argument
    naming conventions (eg. no spaces).
    
    Example::
      env.set(
        CODE_PATH="C:/code",
        ART_PATH="C:/art",
        )
    """
    self.__environment.update(kwargs)
    
  def delete(self, *arguments):    
    """Delete values given their keys.
    
    Note that this means keys must conform to Python argument naming
    conventions (eg. no spaces).

    Example::
      env.delete(
        CODE_PATH,
        ART_PATH
        )
    """
    for a in arguments:
      del self.__vars[a]
      
  def update(self, values):
    """Update the environment with key/value pairs from 'values'.
    
    Example::
      env.update({
        "CODE_PATH":"c:/code",
        "ART_PATH":"c:/art",
        })
    @param values: An iterable sequence of key/value pairs to update
    from.
    """
    self.__vars.update(values)
    
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
    return cake.path.expandVars(value, self.__vars)

  def choose(self, select, **keywords):
    """Select one of the options based on the current value of the env variable.

    Example:
    | env.choose("platform",
    |            win32="socket_win32.cpp",
    |            linux="socket_posix.cpp",
    |            osx="socket_mac.cpp",
    |            )
    | # "socket_posix.cpp" if env["platform"] == "linux"

    @param select: The name of the environment variable.
    @type select: string

    @return: The value of the keyword arg that matches the value of the
    environment variable. If the variable doesn't exist or none of the
    values match then returns None.
    """
    return keywords.get(self.get(select, None), None)
  