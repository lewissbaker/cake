#-------------------------------------------------------------------------------
# Script used to build the main program.
#-------------------------------------------------------------------------------
from cake.tools import compiler, script

# Use the printer library. The libraries include path will be added to the
# compilers command line for object file builds, and the library filename and
# library include path will be added to the command line for program builds.
script.include(script.cwd("../printer/use.cake"))

# List of sources.
sources = script.cwd([
  "main.cpp",
  ])

# Build the objects.
objects = compiler.objects(
  targetDir=script.cwd("../../build/uselibrary/main/obj"),
  sources=sources,
  )

# Build the program.
compiler.program(
  target=script.cwd("../../build/uselibrary/main/bin/main"),
  sources=objects,
  )
