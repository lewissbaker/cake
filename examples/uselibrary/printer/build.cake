#-------------------------------------------------------------------------------
# Script used to build the printer library.
#-------------------------------------------------------------------------------
from cake.tools import compiler, script
import cake.path

# Add the .h include path.
compiler.addIncludePath("include")

# List of includes.
includes = cake.path.join("include", [
  "printer.h",
  ])

# List of sources.
sources = cake.path.join("source", [
  "printer.cpp",
  ])

# Build the objects.
objects = compiler.objects(
  targetDir="../../build/$VARIANT/uselibrary/printer/obj",
  sources=sources,
  )

# Build the library.
library = compiler.library(
  target="../../build/$VARIANT/uselibrary/printer/lib/printer",
  sources=objects,
  )

# Set the 'library' result of this script to the library we built above.
script.setResult(library=library)
