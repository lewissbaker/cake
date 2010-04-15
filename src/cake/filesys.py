"""File System Utilities.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import shutil
import os
import os.path
import time

def toUtc(timestamp):
  """Convert a timestamp from local time-zone to UTC.
  """
  return time.mktime(time.gmtime(timestamp))
  
def exists(path):
  """Check if a file or directory exists at the path.
  
  @param path: The path to check for.
  @type path: string
  
  @return: True if a file or directory exists, otherwise False.
  @rtype: bool
  """
  return os.path.exists(path)

def isFile(path):
  """Check if a file exists at the path.
  
  @param path: The path of the file to check for.
  @type path: string
  
  @return: True if the file exists, otherwise False.
  @rtype: bool
  """
  return os.path.isfile(path)

def isDir(path):
  """Check if a directory exists at the path.

  @param path: The path of the directory to check for.
  @type path: string
  
  @return: True if the directory exists, otherwise False.
  @rtype: bool
  """
  return os.path.isdir(path)

def remove(path):
  """Remove a file.
  
  Unlike os.remove() this function fails silently if the
  file does not exist.

  @param path: The path of the file to remove.
  @type path: string
  """
  try:
    os.remove(path)
  except EnvironmentError:
    # Ignore failure if file doesn't exist. Fail if it's a directory.
    if os.path.exists(path):
      raise

def removeTree(path):
  """Recursively delete all files in the directory at specified path.

  @param path: Path to the directory containing the tree to remove
  """
  for root, dirs, files in os.walk(path, topdown=False):
    for name in files:
      p = os.path.join(root, name)
      remove(p)
    for name in dirs:
      p = os.path.join(root, name)
      os.rmdir(p)
  os.rmdir(path)
  
def copyFile(source, target):
  """Copy a file from source path to target path.
  
  Overwrites the target path if it exists and is writeable.
  Create's the target directory if it doesn't exist.
  
  @param source: The path of the source file.
  @type source: string
  @param target: The path of the target file.
  @type target: string
  """
  makeDirs(os.path.dirname(target)) 
  shutil.copyfile(source, target)

def rename(source, target):
  """Rename a file or directory.

  @param source: The path of the source file/directory.
  @type source: string
  @param target: The path of the target file/directory.
  @type target: string
  """
  os.rename(source, target)
  
def makeDirs(path):
  """Recursively create directories.
  
  Unlike os.makedirs(), it does not throw an exception if the
  directory already exists.
  
  @param path: The path of the directory to create.
  @type path: string 
  """
  # Don't try to create directory at the root level, eg: 'C:\\'
  if os.path.ismount(path):
    return
  
  head, tail = os.path.split(path)
  if not tail:
    head, tail = os.path.split(head)
  if head and tail and not os.path.exists(head):
    makeDirs(head)
    if tail == os.curdir: # xxx/newdir/. exists if xxx/newdir exists
      return

  try:
    os.mkdir(path)
  except EnvironmentError:
    # Ignore failure due to directory already existing.
    if not os.path.isdir(path):
      raise
