#-------------------------------------------------------------------------------
# Script used to build the printer library.
#-------------------------------------------------------------------------------
from cake.tools import compiler, script

# Add the .h include path.
compiler.addIncludePath(script.cwd("include"))

# List of includes.
includes = script.cwd("include", [
  "printer.h",
  ])

# List of sources.
sources = script.cwd("source", [
  "printer.cpp",
  ])

# Build the objects.
objects = compiler.objects(
  targetDir=script.cwd("../../build/uselibrary/printer/obj"),
  sources=sources,
  )

# Build the library.
library = compiler.library(
  target=script.cwd("../../build/uselibrary/printer/lib/printer"),
  sources=objects,
  )

# Set the 'library' result of this script to the library we built above.
script.setResult(library=library)
