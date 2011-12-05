#-------------------------------------------------------------------------------
# This example demonstrates copying a single file using the filesys tool.
#-------------------------------------------------------------------------------
from cake.tools import filesys

# Copy the file. It will only be copied again if the files time stamp is out
# of date.
filesys.copyFile(
  source="copyme.txt",
  target="../build/$VARIANT/copyfile/copiedyou.txt",
  )

# Copy a list of files to a target directory.
filesys.copyFiles(
  sources=["copyme.txt", "copymetoo.txt"],
  targetDir="../build/$VARIANT/copyfile/copiedfiles",
  )
