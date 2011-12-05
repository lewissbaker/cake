#-------------------------------------------------------------------------------
# Script used to extract a zip file.
#-------------------------------------------------------------------------------
from cake.tools import zipping

# Function that determines what to include (based on source file/directory path).
def shouldInclude(s):
  return s.find("exclude") == -1

# Extract the zip file. Only extract files/directories that are newer than those
# in the target directory. Remove any files/directories in the target directory
# that no longer exist in the source path. 
zipping.extract(
  targetDir="../build/$VARIANT/unzip",
  source="unzip.zip",
  onlyNewer=True,
  removeStale=True,
  includeMatch=shouldInclude,
  )
