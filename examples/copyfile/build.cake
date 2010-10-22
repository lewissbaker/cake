#-------------------------------------------------------------------------------
# Script used to copy a file.
#-------------------------------------------------------------------------------
from cake.tools import filesys, script

# Copy the file. It will only be copied again if the files time stamp is out
# of date.
filesys.copyFile(
  source=script.cwd("copyme.txt"),
  target=script.cwd("../build/copyfile/copiedyou.txt"),
  )
