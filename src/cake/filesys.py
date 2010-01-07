import shutil
import os
import os.path

def copyFile(source, target):
  """Copy a file from source path to target path.
  
  Overwrites the target path if it exists and is writeable.
  Create's the target directory if it doesn't exist.
  """
  makeDirs(os.path.dirname(target)) 
  shutil.copyfile(source, target)
  
def makeDirs(path):
  """
  Recursively create directories.
  
  Unlike os.makedirs(), it does not throw an exception if the
  directory already exists. 
  """
  # Don't try to create directory at the root level, eg: 'C:\\'
  if os.path.ismount(path):
    return
  
  try:
    os.makedirs(path)
  except Exception, e:
    # Ignore failures due to directory already existing.
    if not os.path.isdir(path):
      raise
