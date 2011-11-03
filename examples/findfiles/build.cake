#-------------------------------------------------------------------------------
# This example demonstrates copying a single file using the filesys tool.
#-------------------------------------------------------------------------------
from cake.tools import filesys, logging

import cake.path
import fnmatch

basePath = filesys.configuration.basePath
absPath = filesys.configuration.abspath

# Paths returned are relative to the search directory so make them absolute.
def fullPath(path):
  return absPath(basePath(cake.path.join("tofind", path)))

# Function that determines what to include (based on source file/directory path).
def shouldInclude(path):
  if cake.path.isFile(fullPath(path)):
    return fnmatch.fnmatch(cake.path.baseName(path), "findme*.txt")
  else:
    return True # Include/recurse all directories.

# Find and print the contents of the files.
filePaths = filesys.findFiles(
  "tofind",
  recursive=True,
  includeMatch=shouldInclude,
  )

# Paths returned are relative to the config.cake so make them absolute.
for path in filePaths:
  path = fullPath(path)
  if cake.path.isFile(path):
    f = open(path, "rt")
    try:
      logging.outputInfo("The contents of file '%s' are '%s'.\n" % (path, f.read()))
    finally:
      f.close()
