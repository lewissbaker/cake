#-------------------------------------------------------------------------------
# This example demonstrates copying a directory using the filesys tool.
#-------------------------------------------------------------------------------
from cake.tools import filesys

# Function that determines what to include (based on source file/directory path).
def shouldInclude(path):
  return path.find("exclude") == -1

# Copy a source directory to a target directory.
filesys.copyDirectory(
  sourceDir="copyme",
  targetDir="../build/$VARIANT/copydirectory/copiedyou",
  recursive=True,
  onlyNewer=True,
  removeStale=True,
  includeMatch=shouldInclude,
  )
