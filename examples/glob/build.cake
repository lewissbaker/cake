#-------------------------------------------------------------------------------
# This example demonstrates copying a single file using the filesys tool.
#-------------------------------------------------------------------------------
from cake.tools import filesys, logging

# Find and print the contents of the files.
filePaths = filesys.glob("findme*.txt")

# Paths returned are relative to the config.cake so make them absolute.
basePath = filesys.configuration.basePath
absPath = filesys.configuration.abspath

for p in filePaths:
  f = open(absPath(basePath(p)), "rt")
  try:
    logging.outputInfo("The contents of file '%s' are '%s'.\n" % (p, f.read()))
  finally:
    f.close()
