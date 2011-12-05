#-------------------------------------------------------------------------------
# This example demonstrates building and using a module (.dll on windows) with
# the compiler tool.
#-------------------------------------------------------------------------------
from cake.tools import compiler, script

# Use the integer library.
script.include("../integer/use.cake")

# List of sources.
sources = [
  "main.cpp",
  ]

# Build the objects.
objects = compiler.objects(
  targetDir="../../build/$VARIANT/usemodule/main/obj",
  sources=sources,
  )

# Build the program.
compiler.program(
  target="../../build/$VARIANT/usemodule/main/bin/main",
  sources=objects,
  )

# Copy any modules used next to the built program.
compiler.copyModulesTo(
  targetDir="../../build/$VARIANT/usemodule/main/bin",
  )
