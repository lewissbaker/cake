import threading
import sys

# Note: Use semantic versioning (http://semver.org) when changing version.
__version_info__ = (0, 1, 0)
__version__ = '.'.join(str(v) for v in __version_info__)

# We want the 'cake.builders' module to have thread-local contents so that
# Cake scripts can get access to their builders using standard python import
# statements. 
builders = threading.local()
sys.modules['cake.builders'] = builders

def overrideOpen():
  """
  Override the built-in open() and os.open() to set the no-ihherit
  flag on files to prevent processes from inheriting file handles.
  """
  import __builtin__
  import os
  
  old_open = __builtin__.open
  def new_open(filename, mode="r", bufsize=0):
    # Always add no-inherit flag
#    if "N" not in mode:
#      mode += "N" 
    
    if mode.startswith("r"):
      flags = os.O_RDONLY
    elif mode.startswith("w"):
      flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    elif mode.startswith("a"):
      flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    else:
      raise ValueError("mode must start with 'r', 'w' or 'a'")
    
    for ch in mode[1:]:
      if ch == "+":
        flags |= os.O_RDWR
        flags &= ~(os.O_RDONLY | os.O_WRONLY)
      elif ch == "t":
        flags |= os.O_TEXT
      elif ch == "b":
        flags |= os.O_BINARY
      elif ch in " ,":
        pass
      elif ch == "U":
        pass # Universal newline support
      elif ch == "N":
        flags |= os.O_NOINHERIT
      elif ch == "D":
        flags |= os.O_TEMPORARY
      elif ch == "T":
        flags |= os.O_SHORT_LIVED
      elif ch == "S":
        flags |= os.O_SEQUENTIAL
      elif ch == "R":
        flags |= os.O_RANDOM
      else:
        raise ValueError("unknown flag '%s' in mode" % ch)

    if flags & os.O_BINARY and flags & os.O_TEXT:
      raise ValueError("Cannot specify both 't' and 'b' in mode")
    if flags & os.O_SEQUENTIAL and flags & os.O_RANDOM:
      raise ValueError("Cannot specify both 'S' and 'R' in mode")

    try:
      fd = os.open(filename, flags)
      return os.fdopen(fd, mode, bufsize)
    except OSError, e:
      raise IOError(str(e))
  __builtin__.open = new_open

  old_os_open = os.open
  def new_os_open(filename, flag, mode=0777):
#    if not flag & os.O_NOINHERIT:
#      sys.stderr.write("opening %s - added O_NOINHERIT\n" % filename)
#    else:
#      sys.stderr.write("opening %s\n" % filename)

    flag |= os.O_NOINHERIT
    return old_os_open(filename, flag, mode)
  os.open = new_os_open
  
overrideOpen()
