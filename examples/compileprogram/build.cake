#-------------------------------------------------------------------------------
# This example demonstrates building a program from a single source file using
# the compiler tool.
#-------------------------------------------------------------------------------
from cake.tools import compiler

# List of sources.
sources = [
  "main.cpp",
  ]

# Build the objects.
objects = compiler.objects(
  targetDir="../build/$TARGET/compileprogram/obj",
  sources=sources,
  )

# Build the program.
compiler.program(
  target="../build/$TARGET/compileprogram/bin/main",
  sources=objects,
  )
