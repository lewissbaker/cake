#-------------------------------------------------------------------------------
# This example demonstrates copying a single file using the filesys tool.
#-------------------------------------------------------------------------------
from cake.tools import filesys, logging

import cake.path
import fnmatch

# Function that determines what to include (based on source file/directory path).
def shouldInclude(path):
  return fnmatch.fnmatch(path, "findme*.txt")

# Find and print the contents of the files.
filePaths = filesys.findFiles(
  "tofind",
  recursive=True,
  includeMatch=shouldInclude,
  )

# Paths returned are relative to the config.cake so make them absolute.
basePath = filesys.configuration.basePath
absPath = filesys.configuration.abspath

for p in filePaths:
  path = absPath(basePath(cake.path.join("tofind", p)))
  if cake.path.isFile(path): # Only print files, not directories.
    f = open(path, "rt")
    try:
      logging.outputInfo("The contents of file '%s' are '%s'.\n" % (p, f.read()))
    finally:
      f.close()
