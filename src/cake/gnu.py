"""Utilities for dealing with GNU tools.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

def parseDependencyFile(path, targetSuffix):
  """Parse a .d file and return the list of dependencies.
  
  @param path: The path to the dependency file.
  @type path: string
  @param targetSuffix: Suffix used by targets.
  @type targetSuffix: string
  @return: A list of dependencies.
  @rtype: list of string
  """
  dependencies = []
  uniqueDeps = set()

  def addPath(path):
    if path and path not in uniqueDeps:
      uniqueDeps.add(path)
      path = path.replace('\\ ', ' ') # fix escaped spaces
      dependencies.append(path)

  f = open(path, 'rt')
  try:
    text = f.read()
    text = text.replace('\\\n', ' ') # join escaped lines
    text = text.replace('\n', ' ') # join other lines
    text = text.lstrip() # strip leading whitespace

    # Find the 'target:' rule
    i = text.find(targetSuffix + ':')
    if i != -1:
      text = text[i+len(targetSuffix)+1:] # strip target + ':'

      while True:
        text = text.lstrip() # strip leading whitespace

        i = text.find(' ')
        while i != -1 and text[i-1] == '\\': # Skip escaped spaces
          i = text.find(' ', i+1)
        
        if i == -1:
          addPath(text)
          break
        else:
          addPath(text[:i])
          text = text[i:]
  finally:
    f.close()
  
  return dependencies
