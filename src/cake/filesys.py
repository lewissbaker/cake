import shutil
import os
import os.path

def exists(path):
  """Check if a file or directory exists at the path.
  """
  return os.path.exists(path)

def isFile(path):
  """Check if a file exists at the path.
  """
  return os.path.isfile(path)

def isDirectory(path):
  """Check if a directory exists at the path.
  """
  return os.path.isdir(path)

def copyFile(source, target):
  """Copy a file from source path to target path.
  
  Overwrites the target path if it exists and is writeable.
  Create's the target directory if it doesn't exist.
  """
  makeDirs(os.path.dirname(target)) 
  shutil.copyfile(source, target)
  
def makeDirs(path):
  """Recursively create directories.
  
  Unlike os.makedirs(), it does not throw an exception if the
  directory already exists. 
  """
  # Don't try to create directory at the root level, eg: 'C:\\'
  if os.path.ismount(path):
    return
  
  try:
    os.makedirs(path)
  except Exception:
    # Ignore failure due to directory already existing.
    if not os.path.isdir(path):
      raise
