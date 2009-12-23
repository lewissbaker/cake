'''
Created on 22/12/2009

@author: Bugs Bunny
'''

import __builtin__
import imp
import marshal
import os
import struct

MAGIC = imp.get_magic()

# Define an internal helper according to the platform
if os.name == "mac":
  import MacOS
  def set_creator_type(file):
    MacOS.SetCreatorAndType(file, 'Pyth', 'PYC ')
else:
  def set_creator_type(file):
    pass
      
def wr_long(f, x):
  """Internal; write a 32-bit int to a file in little-endian order."""
  f.write(chr( x        & 0xff))
  f.write(chr((x >> 8)  & 0xff))
  f.write(chr((x >> 16) & 0xff))
  f.write(chr((x >> 24) & 0xff))

def compile(file, cfile=None, dfile=None):
  """Byte-compile one Python source file to Python bytecode.

  Arguments:

  file:    source filename
  cfile:   target filename; defaults to source with 'c' or 'o' appended
           ('c' normally, 'o' in optimizing mode, giving .pyc or .pyo)
  dfile:   purported filename; defaults to source (this is the filename
           that will show up in error messages)

  Note that it isn't necessary to byte-compile Python modules for
  execution efficiency -- Python itself byte-compiles a module when
  it is loaded, and if it can, writes out the bytecode to the
  corresponding .pyc (or .pyo) file.

  However, if a Python installation is shared between users, it is a
  good idea to byte-compile all modules upon installation, since
  other users may not be able to write in the source directories,
  and thus they won't be able to write the .pyc/.pyo file, and then
  they would be byte-compiling every module each time it is loaded.
  This can slow down program start-up considerably.

  See compileall.py for a script/module that uses this module to
  byte-compile all installed files (or all files in selected
  directories).

  """
  with open(file, 'rU') as f:
    try:
      timestamp = long(os.fstat(f.fileno()).st_mtime)
    except AttributeError:
      timestamp = long(os.stat(file).st_mtime)
    codestring = f.read()
    
  if not codestring.endswith("\n"):
    codestring = codestring + "\n"
  codeobject = __builtin__.compile(codestring, dfile or file, 'exec')
  
  # Try to save the cache file if possible, don't sweat if we can't
  if cfile is None:
    cfile = file + (__debug__ and 'c' or 'o')
  try:
    with open(cfile, 'wb') as fc:
      fc.write('\0\0\0\0')
      wr_long(fc, timestamp)
      marshal.dump(codeobject, fc)
      fc.flush()
      fc.seek(0, 0)
      fc.write(MAGIC)
    set_creator_type(cfile)
  except Exception:
    pass
  
  return codeobject

def loadCode(file, cfile=None, dfile=None):
  """Load the code object for the specified python file.
  
  Uses the bytecode cache file if it exists and matches the timestamp of
  the source file.
  
  @return: The code object resulting from compiling the python source file.
  """
  if cfile is None:
    cfile = file + (__debug__ and 'c' or 'o')
  try:
    with open(cfile, 'rb') as f:
      if f.read(4) == MAGIC:
        tCache = struct.unpack('<I', f.read(4))[0]
        tSource = long(os.stat(file).st_mtime)
        if tSource == tCache:
          return marshal.load(f)
  except Exception:
    # Failed to load the cache file
    pass
  
  return compile(file, cfile, dfile)

class CodeCache(object):

  def __init__(self):
    self._cache = {}
    
  def load(self, path):
    code = self._cache.get(path, None)
    if code is None:
      code = loadCode(path)
      self._cache[path] = code
    return code
