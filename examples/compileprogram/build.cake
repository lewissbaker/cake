#-------------------------------------------------------------------------------
# Script used to build the main program.
#-------------------------------------------------------------------------------
from cake.tools import compiler, script

# List of sources.
sources = script.cwd([
  "main.cpp",
  ])

# Build the objects.
objects = compiler.objects(
  targetDir=script.cwd("../build/compileprogram/obj"),
  sources=sources,
  )

# Build the program.
compiler.program(
  target=script.cwd("../build/compileprogram/bin/main"),
  sources=objects,
  )
