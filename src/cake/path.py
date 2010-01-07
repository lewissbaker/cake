import os.path

def join(*args):
  """
  Find the cross product of any amount of input paths or lists of paths.
  
  Example:
  join("a", "b", "c") -> "a/b/c"
  join("a", ["b", "c"], "d") -> ["a/b/d", "a/c/d"]
  join(["a", "b"], ["c", "d"]) -> ["a/c", "a/d", "b/c", "b/d"]
  """
  results = []

  if not args:
    return ""
  elif len(args) == 1:
    return args[0]

  anyLists = False
  
  last = args[-1]
  if isinstance(last, basestring):
    results = [last]
  else:
    results = last
    anyLists = True

  osJoin = os.path.join

  for i in xrange(len(args) - 2, -1, -1):
    arg = args[i]
    if isinstance(arg, basestring):
      results = [osJoin(arg, r) for r in results]
    else:
      anyLists = True
      newResults = []
      for a in arg:
        newResults.extend(osJoin(a, r) for r in results)
      results = newResults
  
  if anyLists:
    return results
  else:
    return results[0]

def expandVars(path, env):
  """
  Recursively expand shell variables of the form $var and ${var}.

  This function is a copy of os.path.expandvars() with added support for
  recursion.
  
  Unknown variables are replaced with {MISSING_SYMBOL_<varname>}.
  """
  if '$' not in path:
    return path
  import string
  varchars = string.ascii_letters + string.digits + '_-'
  res = ''
  index = 0
  pathlen = len(path)
  while index < pathlen:
    c = path[index]
    if c == '\'':   # no expansion within single quotes
      path = path[index + 1:]
      pathlen = len(path)
      try:
        index = path.index('\'')
        res = res + '\'' + path[:index + 1]
      except ValueError:
        res = res + path
        index = pathlen - 1
    elif c == '$':  # variable or '$$'
      if path[index + 1:index + 2] == '$':
        res = res + c
        index = index + 1
      elif path[index + 1:index + 2] == '{':
        path = path[index + 2:]
        pathlen = len(path)
        try:
          index = path.index('}')
          var = path[:index]
          if var in env:
            res = res + expandVars(env[var], env)
          else:
            res = res + '{MISSING_SYMBOL_' + var + '}'
        except ValueError:
          res = res + path
          index = pathlen - 1
      else:
        var = ''
        index = index + 1
        c = path[index:index + 1]
        while c != '' and c in varchars:
          var = var + c
          index = index + 1
          c = path[index:index + 1]
        if var in env:
          res = res + expandVars(env[var], env)
        else:
          res = res + '{MISSING_SYMBOL_' + var + '}'
        if c != '':
          res = res + c
    else:
      res = res + c
    index = index + 1
  return res

