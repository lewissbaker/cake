#-------------------------------------------------------------------------------
# This example demonstrates building and using a module (.dll on windows) with
# the compiler tool.
#-------------------------------------------------------------------------------
from cake.tools import compiler, script

# Use the integer library.
script.include(script.cwd("../integer/use.cake"))

# List of sources.
sources = script.cwd([
  "main.cpp",
  ])

# Build the objects.
objects = compiler.objects(
  targetDir=script.cwd("../../build/usemodule/main/obj"),
  sources=sources,
  )

# Build the program.
compiler.program(
  target=script.cwd("../../build/usemodule/main/bin/main"),
  sources=objects,
  )

# Copy any modules used next to the built program.
compiler.copyModulesTo(
  targetDir=script.cwd("../../build/usemodule/main/bin"),
  )
