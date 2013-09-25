#-------------------------------------------------------------------------------
# This example demonstrates building a program that links to a library. Both the
# program and library are built using the compiler tool. If the program is built
# before the library it will implicitly build the library via the libraries
# 'use.cake' dependency.
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
  targetDir=script.cwd("obj"),
  sources=sources,
  )

# Build the program.
compiler.program(
  target=script.cwd("bin/main"),
  sources=objects,
  )
