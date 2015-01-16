"""Utilities for loading Byte-Compiled Scripts.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import __builtin__
import imp
import marshal
import os
import sys
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
      
def loadCode(file, cfile=None, dfile=None, cached=True):
  """Load the code object for the specified python file.
  
  Uses the bytecode cache file if it exists and matches the timestamp of
  the source file. These files have the same format as the .pyc/.pyo files
  used by Python module import logic.
  
  @param file: Path of the source file to load.
  
  @param cfile: If specified, the path of the bytecode cache file.
  Defaults to path of the original file with either 'c' or 'o' appended.
  
  @param dfile: If specified, the path of the file to show in error
  messages. Defaults to C{file}.
   
  @param cached: True if the byte code should be cached to a separate
  file for quicker loading next time.
  @type cached: bool
   
  @return: The code object resulting from compiling the python source file.
  This can be executed by the 'exec' statement/function.
  """
  if cfile is None:
    cfile = file + (__debug__ and 'c' or 'o')

  timestamp = None

  try:
    if sys.dont_write_bytecode:
      cached = False
  except AttributeError:
    # Fallback for Python 2.5 or earlier
    if "PYTHONDONTWRITEBYTECODE" in os.environ:
      cached = False

  if cached:
    # Try to load the cache file if possible, don't sweat if we can't
    try:
      f = open(cfile, 'rb')
      try:
        if f.read(_MAGIC_LEN) == _MAGIC:
          cacheTimestamp = struct.unpack('<I', f.read(4))[0]
          timestamp = long(os.stat(file).st_mtime)
          if timestamp == cacheTimestamp:
            return marshal.load(f)
      finally:
        f.close()
    except Exception:
      # Failed to load the cache file
      pass
  
  # Load the source file
  f = open(file, 'rU')
  try:
    if timestamp is None:
      try:
        timestamp = long(os.fstat(f.fileno()).st_mtime)
      except AttributeError:
        timestamp = long(os.stat(file).st_mtime)
    codestring = f.read()
  finally:
    f.close()
    
  # Source needs a trailing newline to compile correctly
  if not codestring.endswith('\n'):
    codestring = codestring + '\n'
    
  # Compile the source
  codeobject = __builtin__.compile(codestring, dfile or file, 'exec')
  
  if cached:
    # Try to save the cache file if possible, don't sweat if we can't
    try:
      f = open(cfile, 'wb')
      try:
        f.write(_NOTMAGIC)
        f.write(struct.pack('<I', timestamp))
        marshal.dump(codeobject, f)
        f.flush()
        f.seek(0, 0)
        f.write(_MAGIC)
      finally:
        f.close()
      _setCreatorType(cfile)
    except Exception:
      pass
  
  return codeobject
