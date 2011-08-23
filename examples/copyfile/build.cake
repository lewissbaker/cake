#-------------------------------------------------------------------------------
# This example demonstrates copying a single file using the filesys tool.
#-------------------------------------------------------------------------------
from cake.tools import filesys, script

# Copy the file. It will only be copied again if the files time stamp is out
# of date.
filesys.copyFile(
  source=script.cwd("copyme.txt"),
  target=script.cwd("../build/copyfile/copiedyou.txt"),
  )

# Copy a list of files to a target directory.
filesys.copyFiles(
  sources=script.cwd(["copyme.txt", "copymetoo.txt"]),
  targetDir=script.cwd("../build/copyfile/copiedfiles"),
  )
