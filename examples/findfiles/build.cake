#-------------------------------------------------------------------------------
# This example demonstrates copying a single file using the filesys tool.
#-------------------------------------------------------------------------------
from cake.tools import filesys, logging

# Find and print the contents of the files.
filePaths = filesys.findFiles(
  ".",
  recursive=True,
  pattern="findme*.txt",
  patternRe=None,
  )

# Paths returned are relative to the config.cake so make them absolute.
absPath = filesys.configuration.abspath

for p in filePaths:
  f = open(absPath(p), "rt")
  try:
    logging.outputInfo("The contents of file '%s' are '%s'.\n" % (p, f.read()))
  finally:
    f.close()
