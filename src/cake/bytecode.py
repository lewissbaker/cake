"""Utilities for loading Byte-Compiled Scripts.
"""

__all__ = ["loadCode"]

import __builtin__
import imp
import marshal
import os
import struct
import platform

# Magic header written at start of file
_MAGIC = imp.get_magic()
_MAGIC_LEN = len(_MAGIC)
_NOTMAGIC = '\0' * _MAGIC_LEN

assert _MAGIC != _NOTMAGIC

# Define an internal helper according to the platform
if platform.system() in ['Darwin']:
  import MacOS
  def _setCreatorType(file):
    MacOS.SetCreatorAndType(file, 'Pyth', 'PYC ')
else:
  def _setCreatorType(file):
    pass
      
def loadCode(file, cfile=None, dfile=None):
  """Load the code object for the specified python file.
  
  Uses the bytecode cache file if it exists and matches the timestamp of
  the source file. These files have the same format as the .pyc/.pyo files
  used by Python module import logic.
  
  @param file: Path of the source file to load.
  
  @param cfile: If specified, the path of the bytecode cache file.
  Defaults to path of the original file with either 'c' or 'o' appended.
  
  @param dfile: If specified, the path of the file to show in error
  messages. Defaults to C{file}.
   
  @return: The code object resulting from compiling the python source file.
  This can be executed by the 'exec' statement/function.
  """
  if cfile is None:
    cfile = file + (__debug__ and 'c' or 'o')

  timestamp = None
   
  # Try to load the cache file if possible, don't sweat if we can't
  try:
    with open(cfile, 'rb') as f:
      if f.read(_MAGIC_LEN) == _MAGIC:
        cacheTimestamp = struct.unpack('<I', f.read(4))[0]
        timestamp = long(os.stat(file).st_mtime)
        if timestamp == cacheTimestamp:
          return marshal.load(f)
  except Exception:
    # Failed to load the cache file
    pass
  
  # Load the source file
  with open(file, 'rU') as f:
    if timestamp is None:
      try:
        timestamp = long(os.fstat(f.fileno()).st_mtime)
      except AttributeError:
        timestamp = long(os.stat(file).st_mtime)
    codestring = f.read()
    
  # Source needs a trailing newline to compile correctly
  if not codestring.endswith('\n'):
    codestring = codestring + '\n'
    
  # Compile the source
  codeobject = __builtin__.compile(codestring, dfile or file, 'exec')
  
  # Try to save the cache file if possible, don't sweat if we can't
  try:
    with open(cfile, 'wb') as f:
      f.write(_NOTMAGIC)
      f.write(struct.pack('<I', timestamp))
      marshal.dump(codeobject, f)
      f.flush()
      f.seek(0, 0)
      f.write(_MAGIC)
    _setCreatorType(cfile)
  except Exception:
    pass
  
  return codeobject
