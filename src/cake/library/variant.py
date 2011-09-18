"""Variant Tool.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

from cake.library import Tool
from cake.script import Script

class VariantTool(Tool):
  
  def __getattribute__(self, name):
    """Return a variant keywords current value given its name.
    
    @param name: The name of the keyword to query.
    @type name: string
    @return: The current value of the named keyword.
    @rtype: string
    """
    try:
      return Tool.__getattribute__(self, name)
    except AttributeError:
      try:
        return Script.getCurrent().variant.keywords[name]
      except KeyError:
        raise AttributeError("Unknown attribute '%s'" % name)
