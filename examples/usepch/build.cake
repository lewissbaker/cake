#-------------------------------------------------------------------------------
# This example demonstrates building a program from a single source file using
# the compiler tool. The source file uses a precompiled header file.
#-------------------------------------------------------------------------------
from cake.tools import compiler

# List of sources.
sources = [
  "main.cpp",
  ]

# The precompiled header exactly as it's included by source files.
pchHeader = "pch.h"

# Build the precompiled header.
pch = compiler.pch(
  target="../build/$VARIANT/usepch/obj/pch",
  source="pch.cpp",
  header=pchHeader,
  )

# Build the objects. Use the precompiled header built above.
objects = compiler.objects(
  targetDir="../build/$VARIANT/usepch/obj",
  sources=sources,
  pch=pch,
  )

# Build the program. The precompiled header must be added to the list of sources
# for compilers such as MSVC.
compiler.program(
  target="../build/$VARIANT/usepch/bin/main",
  sources=objects + [pch],
  )
